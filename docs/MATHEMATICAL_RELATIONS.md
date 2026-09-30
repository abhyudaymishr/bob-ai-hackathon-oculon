# Mathematical relations implemented in the Delhi hotspot codebase

This document summarizes equations found in the included implementation. Symbols are defined locally, and each item names the workflow to which it applies. It distinguishes the discrete multigram ranker from the differentiable logistic comparison model; they do not share an objective or Hessian.

## 1. Date, place, and spatial units

### 1.1 Event-time bucket

For event date (d_i), the monthly index is (m_i=\operatorname{YYYY-MM}(d_i)), and the calendar month number (s_i\in\{1,\ldots,12\}) supplies seasonality. Rows with invalid, implausible, after-cutoff dates, or unresolved/ambiguous locations are excluded from the corresponding spatial model rather than assigned invented coordinates.

### 1.2 Nearest metro assignment

For a resolved approximate location (p_i=(\phi_i,\lambda_i)) and metro stations (q_j=(\phi_j,\lambda_j)), the code assigns
\[
j^*(i)=\arg\min_j d_H(p_i,q_j),
\]
using the Haversine great-circle distance
\[
a=\sin^2\!\left(\frac{\Delta\phi}{2}\right)+\cos\phi_i\cos\phi_j\sin^2\!\left(\frac{\Delta\lambda}{2}\right),\qquad
 d_H=2R\arcsin(\min(1,\sqrt a)),
\]
where angles are in radians and (R=6{,}371{,}008.8) metres. In vehicle analysis the input point is a PIN/locality postal-area centroid, so the nearest-station assignment is also approximate.

### 1.3 Local projected coordinates

For transport optimization, geographic coordinates are projected locally using an equirectangular approximation about reference latitude (\phi_0) and longitude (\lambda_0):
\[
x=R(\lambda-\lambda_0)\cos\phi_0,\qquad y=R(\phi-\phi_0).
\]
The Euclidean distance (\sqrt{(x_i-x_j)^2+(y_i-y_j)^2}) is used for local transport cost. This is a local approximation, not a national projection.

## 2. Discrete spatial multigram model

Implemented in `train_missing_persons_multigram.py` and reused by the body and vehicle trainers.

### 2.1 Daily location sequence

For each date, station/unit counts are aggregated. The location-token sequence concatenates at most the three highest-count units for each date, with deterministic count/name tie ordering. This prevents arbitrary CSV row order from becoming a transition order. Let the resulting sequence be (z_1,\ldots,z_T ).

### 2.2 Seasonal/recent base distribution

For target calendar month (s) and spatial unit (u), let (C_s(u)) count historical events in month-of-year (s). Let (C_{12k}(u)) count the most recent up-to-12,000 historical events. The raw blended weight is
\[
r(u)=0.60C_s(u)+0.40C_{12k}(u).
\]
With (N) candidate units, the smoothed base distribution is
\[
B(u)=\frac{r(u)+0.5}{\sum_v r(v)+0.5N}.
\]
The 0.5 additive constant is a symmetric smoothing prior.

### 2.3 Conditional (n)-gram estimates

For order (n\in\{1,2,3\}), let (c_n(u\mid h_n)) be the number of times unit (u) follows the (n)-token history (h_n) in the sequence, and let (C_n(h_n)=\sum_v c_n(v\mid h_n)). The implementation uses Lidstone smoothing strength \(\alpha=8 ):
\[
G_n(u\mid h_n)=\frac{c_n(u\mid h_n)+\alpha B(u)}{C_n(h_n)+\alpha}.
\]
If the sequence lacks a context of order (n), that order falls back to (B(u)).

The implemented rank score is the normalized blend
\[
S(u)=\frac{0.25B(u)+0.20G_1(u\mid h_1)+0.25G_2(u\mid h_2)+0.30G_3(u\mid h_3)}{\sum_v[0.25B(v)+0.20G_1(v\mid h_1)+0.25G_2(v\mid h_2)+0.30G_3(v\mid h_3)]}.
\]
Because each component is a probability distribution and the weights sum to one, the denominator is theoretically one; the code normalizes again for numerical safety. These are relative next-unit scores, not calibrated counts or validated event probabilities.

### 2.4 Top-(k) hotspot sets

The model defines (k=\max(1,\lceil q|A_m|\rceil)), where (A_m) is the set of active units in month (m), and (q=0.10) by default. Actual hotspots are the (k) units with greatest held-out counts; predicted hotspots are the (k) highest model scores among the candidate units. Deterministic unit-name ordering breaks ties.

## 3. Binary logistic hotspot model and Hessian

Implemented by `build_spatial_method_comparison.py` and `build_random_hotspot_model.py`. For a unit-month feature vector (x_i), label (y_i\in\{0,1\}), and coefficient vector (w),
\[
p_i=\sigma(x_i^Tw)=\frac{1}{1+e^{-x_i^Tw}}.
\]
Features include a spatial-unit indicator, cyclic month terms (\sin(2\pi(s-1)/12) ) and (\cos(2\pi(s-1)/12) ), capped linear time trend, \(\log(1+c_{m-1}) ), and \(\log(1+(c_{m-1}+c_{m-2}+c_{m-3})/3) ), plus intercept. Here counts/lag features must be built from training data only.

The mean binary cross-entropy with L2 regularization is
\[
J(w)=\frac1n\sum_{i=1}^n\left[\log(1+e^{x_i^Tw})-y_i x_i^Tw\right]+\frac{\lambda}{2}w^TPw,
\]
where \(\lambda=0.08 ), (P) is identity except the intercept is unpenalized. Let (p_i=\sigma(x_i^Tw)), (D=\operatorname{diag}(p_i(1-p_i))). Then
\[
\nabla J(w)=\frac1nX^T(p-y)+\lambda Pw,
\qquad
H(w)=\nabla^2J(w)=\frac1nX^TDX+\lambda P.
\]
Newton's update is (w_{t+1}=w_t-\eta H(w_t)^{-1}\nabla J(w_t)). The code starts (\eta=1) and halves it until the objective does not increase, stopping at small parameter change, failed line search, or the iteration cap. Hessian CSVs store (H) at the fitted coefficients; eigenvalues, trace, and condition number are summaries of curvature/numerical conditioning, not predictive accuracy scores. The multigram model in Section 2 is count-based and differentiability/Hessian is not defined for that procedure.

## 4. Classification evaluation

For binary hotspot labels, (TP,TN,FP,FN) have their usual meanings:
\[
\mathrm{Accuracy}=\frac{TP+TN}{TP+TN+FP+FN},\quad
\mathrm{Precision}=\frac{TP}{TP+FP},\quad
\mathrm{Recall}=\frac{TP}{TP+FN},\quad
F_1=\frac{2\,\mathrm{Precision}\,\mathrm{Recall}}{\mathrm{Precision}+\mathrm{Recall}}.
\]
A zero denominator maps to zero in the implementation. Accuracy can look high when most unit-months are non-hotspots; F1 and geographic distance should be read alongside it.

### 4.1 Rolling-origin probability scores

For a held-out month, let \(p_u\) be the multigram probability for catalogue unit \(u\), and \(q_u=c_u/\sum_v c_v\) the empirical event share at that unit. The new walk-forward evaluator computes categorical log loss and the sum-form Brier score:
\[
L_{\log}=-\sum_u q_u\log(\max(p_u,10^{-15})),\qquad
BS=\sum_u(p_u-q_u)^2.
\]
These proper scores assess the full location distribution, not binary hotspot membership. The normalized monthly counts \(q\) are the observed categorical outcome distribution.

Average precision is computed for binary hotspot labels \(y_u\) ranked by score \(p_u\). For score groups sorted from high to low (ties grouped), if \(\Delta R_g\) is the increase in recall after group \(g\) and \(P_g\) is precision after including that group, then
\[
AP=\sum_g P_g\Delta R_g.
\]
It evaluates ranking over the catalogue and is not a probability-calibration score.

## 5. Geographic error measures

### 5.1 Symmetric hotspot miss distance

For actual hotspot points (A) and predicted points (P), the station-proxy models calculate
\[
D_{sym}=\frac12\left[\frac1{|A|}\sum_{a\in A}\min_{p\in P}d_H(a,p)+\frac1{|P|}\sum_{p\in P}\min_{a\in A}d_H(p,a)\right].
\]
This is a symmetric mean nearest-neighbor distance; despite occasionally being described as a hotspot miss distance, it is not an optimal-transport/Wasserstein metric.

### 5.2 Discrete 1-Wasserstein distance

The PIN-versus-metro method comparison normalizes nonnegative hotspot scores/counts to unit mass within each test month. For source masses `a_i`, target masses `b_j`, and local projected locations `(x_i, y_j)`, it solves
\[
W_1(a,b)=\min_{\pi_{ij}\ge0}\sum_{i,j}\pi_{ij}\lVert x_i-y_j\rVert_2,
\quad \sum_j\pi_{ij}=a_i,\quad\sum_i\pi_{ij}=b_j.
\]
The Python code solves this finite min-cost flow and reports metres converted to kilometres. The legacy PIN-versus-metro comparison transports selected-hotspot masses; the new walk-forward evaluator transports the full predicted event-location distribution against empirical held-out event mass. Lower values mean the compared measures are geographically closer under the selected unit representation; they do not prove that the approximate PIN/metro point is an exact incident location.

## 6. Split and forecast conventions

For event-level random holdouts, a seeded shuffle selects approximately 80% of eligible events for training and 20% for test. Some scripts use `round(0.8n)`, while others use a configurable fraction; exact row counts can differ by rounding. The shared theft spatial comparison applies the same event split to PIN and nearest-metro representations. In the multigram monthly evaluator, score history is explicitly filtered to dates before the target month, so same-month training events are not used in that score. However, random assignment does not simulate one deployment cutoff, and in the logistic comparison the coefficients are fit over the whole training partition; later training months can therefore inform predictions for earlier test months. The new rolling-origin evaluator reserves the latest 20% of complete observed months and uses strictly earlier events for each forecast. The separate `prepare_hotspot_train_test.py` script only prepares a chronological count table; it does not by itself train or evaluate a model.

The next-month forecast ranks spatial units by score after fitting/using all eligible historical events available before the forecast month. The score is not an estimated number of incidents. For missing-mobile data, the known data have only a virtual reporting unit and no physical theft location, so the implementation reports time counts and does not produce a spatial hotspot prediction.

## 7. Interpretation boundaries

- A PIN centroid approximates a postal area; a nearest metro point is assigned from that centroid.
- A police station point represents a reporting-area proxy, not an exact event/recovery site.
- Ambiguous or unmatched text stays unlocated instead of being geocoded speculatively.
- Distances quantify agreement between mapped proxies and labels under the chosen model, not ground-truth address accuracy.
- The package does not convert model scores into causal claims or calibrated incident probabilities.
