#!/usr/bin/env python3
"""Log-Gaussian Cox Process (LGCP) catchment-integration layer.

Model (discretised LGCP on the station catchments):
    f ~ GP(0, k_Matern32(haversine_km))            latent log-intensity field
    y_u | f ~ Poisson( a_u * exp(b + f(s_u)) )      a_u = catchment area (km^2)
The Laplace posterior over f gives, per station u, a posterior-predictive
intensity E[exp(f_u)] = exp(f_u_hat + 0.5 * Var(f_u)). Normalising over stations
gives a spatially smooth probability measure

    p(u) = a_u * lambda_u / sum_v a_v * lambda_v

i.e. the catchment integral of the intensity over each Voronoi cell, divided by
its total mass. Stations with few/zero events inherit mass from neighbours
through the kernel instead of from a global constant.

Only numpy is required.
"""
from __future__ import annotations

import math
import numpy as np

R_KM = 6371.0088
LAT0 = 28.62


def project_km(lons, lats, lat0: float = LAT0) -> np.ndarray:
    lons, lats = np.asarray(lons, float), np.asarray(lats, float)
    x = R_KM * np.radians(lons - 76.75) * math.cos(math.radians(lat0))
    y = R_KM * np.radians(lats - 28.0)
    return np.column_stack([x, y])


def catchment_areas(xy: np.ndarray, cell_km: float = 0.4, max_radius_km: float = 7.0) -> np.ndarray:
    """Voronoi catchment area (km^2) per station via a fine grid Monte-Carlo integral.

    Cells farther than max_radius_km from every station are treated as outside
    Delhi, which stops edge stations getting unbounded catchments. If you want
    an exact mask, drop grid cells that fall outside your boundary GeoJSON.
    """
    pad = max_radius_km
    xs = np.arange(xy[:, 0].min() - pad, xy[:, 0].max() + pad, cell_km)
    ys = np.arange(xy[:, 1].min() - pad, xy[:, 1].max() + pad, cell_km)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    area = np.zeros(len(xy))
    for i in range(0, len(pts), 4000):
        chunk = pts[i:i + 4000]
        d = np.sqrt(((chunk[:, None, :] - xy[None, :, :]) ** 2).sum(-1))
        nearest, dmin = d.argmin(1), d.min(1)
        keep = dmin <= max_radius_km
        np.add.at(area, nearest[keep], cell_km ** 2)
    return np.maximum(area, cell_km ** 2)


def matern32(xy: np.ndarray, ell: float, sigma2: float) -> np.ndarray:
    d = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1))
    s = math.sqrt(3.0) * d / ell
    return sigma2 * (1.0 + s) * np.exp(-s)


def _laplace(y, log_a, K, b, iters: int = 60):
    """Newton (Rasmussen & Williams Alg. 3.1) with step halving. Returns mode, factor, logZ."""
    n = len(y)
    f = np.zeros(n)

    def psi(f_, a_vec):
        eta = log_a + b + f_
        return float(np.sum(y * eta - np.exp(eta)) - 0.5 * f_ @ a_vec)

    a_vec = np.zeros(n)
    cur = psi(f, a_vec)
    for _ in range(iters):
        mu = np.exp(log_a + b + f)
        sW = np.sqrt(mu)
        B = np.eye(n) + sW[:, None] * K * sW[None, :]
        L = np.linalg.cholesky(B)
        rhs = mu * f + (y - mu)
        t = np.linalg.solve(L.T, np.linalg.solve(L, sW * (K @ rhs)))
        a_new = rhs - sW * t
        f_new = K @ a_new
        step = 1.0
        while step > 1e-4:
            f_try = f + step * (f_new - f)
            a_try = a_vec + step * (a_new - a_vec)
            val = psi(f_try, a_try)
            if val >= cur - 1e-12:
                break
            step *= 0.5
        converged = abs(val - cur) < 1e-8
        f, a_vec, cur = f_try, a_try, val
        if converged:
            break
    mu = np.exp(log_a + b + f)
    sW = np.sqrt(mu)
    B = np.eye(n) + sW[:, None] * K * sW[None, :]
    L = np.linalg.cholesky(B)
    log_ml = float(np.sum(y * (log_a + b + f) - mu) - 0.5 * f @ a_vec - np.log(np.diag(L)).sum())
    return f, L, sW, log_ml


def fit_lgcp_base(counts, xy, areas, temper: float = 1.0,
                  ells=(2.0, 4.0, 6.0, 10.0, 16.0), sigma2s=(0.05, 0.2, 0.5, 1.0, 2.0)):
    """Fit the LGCP and return (probabilities per station, chosen hyperparameters).

    counts: (possibly fractional) weighted counts per station, same order as xy/areas.
    temper: overdispersion divisor. Real counts are far more dispersed than
            Poisson, so y/temper stops the likelihood from swamping the GP prior.
            Tune it on validation log-loss (see tune_temper).
    Hyperparameters (ell, sigma2) are chosen by the Laplace marginal likelihood.
    """
    y = np.asarray(counts, float) / max(temper, 1e-9)
    log_a = np.log(areas / areas.mean())
    b = math.log(max(y.sum(), 1e-9) / np.exp(log_a).sum())
    best = None
    for ell in ells:
        for s2 in sigma2s:
            K = matern32(xy, ell, s2) + 1e-8 * np.eye(len(y))
            try:
                f, L, sW, ml = _laplace(y, log_a, K, b)
            except np.linalg.LinAlgError:
                continue
            if best is None or ml > best[0]:
                best = (ml, ell, s2, K, f, L, sW)
    if best is None:
        uniform = np.full(len(y), 1.0 / len(y))
        return uniform, {"ell_km": None, "sigma2": None, "temper": temper}
    _, ell, s2, K, f, L, sW = best
    V = np.linalg.solve(L, sW[:, None] * K)
    var = np.maximum(np.diag(K) - (V ** 2).sum(0), 0.0)
    mass = areas * np.exp(f + 0.5 * var)          # catchment-integrated predictive intensity
    p = mass / mass.sum()
    return p, {"ell_km": ell, "sigma2": s2, "temper": temper}


def tune_temper(fit_fn, holdout_counts, candidates=(1, 3, 10, 30, 100, 300)):
    """Pick temper minimising held-out multinomial log-loss. fit_fn(temper)->p."""
    ho = np.asarray(holdout_counts, float)
    if ho.sum() == 0:
        return candidates[0]
    best = min(candidates, key=lambda t: -(ho * np.log(np.maximum(fit_fn(t)[0], 1e-12))).sum() / ho.sum())
    return best


if __name__ == "__main__":
    # Synthetic self-check: smooth true field + overdispersion + sparse stations.
    rng = np.random.default_rng(0)
    n = 210
    xy = rng.uniform([0, 0], [35, 45], size=(n, 2))
    areas = catchment_areas(xy)
    truth = matern32(xy, 7.0, 0.8) + 1e-8 * np.eye(n)
    f_true = np.linalg.cholesky(truth) @ rng.standard_normal(n)
    lam = areas * np.exp(f_true)
    p_true = lam / lam.sum()

    def draw(N, disp=0.4):
        g = rng.gamma(1 / disp, disp, size=n)          # overdispersion
        pr = p_true * g
        pr /= pr.sum()
        return rng.multinomial(N, pr)

    train, test = draw(3000), draw(3000)
    lid = (train + 8 * (1 / n) * 0 + 0.5) / (train.sum() + 0.5 * n)
    ll = lambda p: -(test * np.log(p)).sum() / test.sum()
    print(f"uniform PP  {math.exp(ll(np.full(n, 1 / n))):.1f}")
    print(f"raw freq PP {math.exp(ll(lid)):.1f}")
    fit = lambda t: fit_lgcp_base(train, xy, areas, temper=t)
    t = tune_temper(fit, draw(3000))
    p, hp = fit(t)
    print(f"LGCP PP     {math.exp(ll(p)):.1f}  {hp}")
