### Detailed Mathematical & Structural Impact Analysis: Continuous Lebesgue Density, Population Exposure Offsets, and Exact Boundary Clipping

Adopting this formulation fundamentally elevates the statistical architecture from an **ad-hoc discrete sequence ranker on arbitrary spatial bins** to a **principled spatial point process with rigorous measure-theoretic foundations**.

Below is a comprehensive breakdown of the mathematical, empirical, and architectural consequences across the codebase.

---

### 1. Resolving the Discretization Bias & The Perplexity Paradox

#### A. The Mathematical Fallacy in Raw Discrete Log-Loss
In the current implementation ([`evaluate_rolling_origin.py:L122`](file:///Users/abhyuday/Desktop/DelhiHotspots_ML/src/delhi_hotspots/evaluate_rolling_origin.py#L122)), the multiclass log-loss is evaluated on the discrete counting measure:
$$L_{\text{discrete}} = -\sum_{u=1}^N q(u) \log p(u)$$
Where the uniform baseline $p_{\text{uniform}}(u) = \frac{1}{N}$ yields a default loss of $\ln N$ (perplexity $N$).

Comparing raw log-loss across non-identical spatial partitions creates an **illusion of predictive superiority**:
* **Missing Persons ($N = 193$ police stations):** $\ln 193 \approx 5.263 \text{ nats} \implies \text{Gain} = 5.263 - 4.991 \approx \mathbf{0.272 \text{ nats}}$
* **Stolen Vehicles · Metro ($N = 233$ metro stations):** $\ln 233 \approx 5.451 \text{ nats} \implies \text{Gain} = 5.451 - 3.902 \approx \mathbf{1.549 \text{ nats}}$
* **Stolen Vehicles · PIN ($N = 95$ postal delivery zones):** $\ln 95 \approx 4.554 \text{ nats} \implies \text{Gain} = 4.554 - 4.022 \approx \mathbf{0.532 \text{ nats}}$

#### Why is Metro's gain $\approx 5.7\times$ higher than Missing Persons?
This is largely an **artifact of cell geometry, not superior modeling**:
1. **Unequal Spatial Volumes:** Metro stations in Central Delhi (Rajiv Chowk, Patel Chowk, Mandi House) are spaced $< 800\text{ m}$ apart, creating tiny Voronoi cells ($\approx 0.5 - 1.5\text{ km}^2$). At the Delhi periphery, metro stations are sparse, creating enormous catchments.
2. **Police Stations Are More Uniform:** Police station jurisdictions cover both dense urban cores and rural outer tracts (Narela, Alipur, Kanjhawala, Bawana) under a relatively balanced administrative distribution.
3. Under the counting measure, assigning probability $p(u) = 0.05$ to a $0.5\text{ km}^2$ metro cell yields the exact same log-loss score as assigning $p(u) = 0.05$ to a $60\text{ km}^2$ outer police station catchment. The discrete metric rewards models that concentrate probability on tiny central transit hubs without penalizing the fact that their physical spatial footprint is minute.

---

### 2. Transition to Continuous Lebesgue Density $f(s) = \frac{p(u)}{a_u}$

#### A. Continuous Cross-Entropy Derivation
Let $\Omega \subset \mathbb{R}^2$ be the spatial domain of Delhi. Define the predictive probability density with respect to the 2D Lebesgue measure $ds$ as a piecewise-constant step function over cell $\mathcal{V}_u$:
$$f(s) = \sum_{u=1}^N \frac{p(u)}{a_u} \mathbb{I}(s \in \mathcal{V}_u), \quad \text{where } a_u = \operatorname{Leb}(\mathcal{V}_u) = \int_{\mathcal{V}_u} ds$$
Notice that $\int_\Omega f(s) ds = \sum_u \frac{p(u)}{a_u} \int_{\mathcal{V}_u} ds = \sum_u p(u) = 1$.

Evaluating the continuous differential cross-entropy under the empirical event distribution $q(s) = \sum_u \frac{q(u)}{a_u} \mathbb{I}(s \in \mathcal{V}_u)$:
$$\mathcal{L}_{\text{cont}} = -\int_\Omega q(s) \log f(s) \, ds = -\sum_{u=1}^N q(u) \log\left(\frac{p(u)}{a_u}\right) = \underbrace{-\sum_{u=1}^N q(u) \log p(u)}_{L_{\text{discrete}}} + \underbrace{\sum_{u=1}^N q(u) \log a_u}_{\text{Geometric Area Entropy}}$$

#### B. The Direct Operational Effect:
$$\mathcal{L}_{\text{cont}} = L_{\text{discrete}} + \mathbb{E}_q[\log a_u]$$
* **For Stolen Vehicles (Metro):** Events occur predominantly near dense central stations where $a_u$ is tiny ($a_u \ll 1\text{ km}^2 \implies \log a_u < 0$). The area correction term $\mathbb{E}_q[\log a_u]$ is **heavily negative**, properly penalizing the apparent 1.55 nats advantage.
* **For Police Stations:** Catchments are larger and more uniform ($\log a_u$ is closer to $\log(\bar{a})$), so the area correction is balanced.
* **Cross-Partition Comparability via Common Refinement:**
  To compare the PIN model ($N=95$), Police Station model ($N=193$), and Metro model ($N=233$) on an identical footing, project all models onto a fine continuous grid (e.g., $100\text{ m} \times 100\text{ m}$ raster mesh $\mathcal{G}$) or the polygonal overlay mesh $\mathcal{M} = \{ \mathcal{V}_u^{\text{police}} \cap \mathcal{V}_v^{\text{metro}} \}$. The continuous Kullback-Leibler divergence:
  $$D_{\text{KL}}(q \parallel f) = \int_\Omega q(s) \log \frac{q(s)}{f(s)} \, ds$$
  becomes **invariant to the chosen administrative discretization**.

---

### 3. Population/Built-Environment Measure $\rho(s)ds$ vs. Flat Physical Area

$$\text{Current Baseline: } a_u = \int_{\mathcal{V}_u} 1 \, ds \quad \longrightarrow \quad \text{Proposed: } a_u = \int_{\mathcal{V}_u} \rho(s) \, ds$$

```
   Physical Area Measure (km²)                   Population Measure ρ(s)ds
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│ Outer Delhi (Narela / Bawana)   │           │ Outer Delhi (Agrarian / Sparse) │
│ Area = 65 km²  (Huge Multiplier)│           │ Population = 80,000 (Low Exp.)  │
├─────────────────────────────────┤           ├─────────────────────────────────┤
│ Central Delhi (Pahar Ganj)      │           │ Central Delhi (Ultra Dense)     │
│ Area = 1.8 km² (Tiny Multiplier)│           │ Population = 320,000 (Huge Exp.)│
└─────────────────────────────────┘           └─────────────────────────────────┘
Result: Rural zones get inflated              Result: Model isolates true
expected counts; urban cores penalized.       "per-capita excess risk" (Hotspots).
```

#### A. The Shift from "Crime Density" to "Per-Capita Relative Risk"
In the current Poisson-GP model in [`lgcp_layer.py:L6`](file:///Users/abhyuday/Desktop/DelhiHotspots_ML/src/delhi_hotspots/lgcp_layer.py#L6):
$$y_u \mid f \sim \operatorname{Poisson}\big(a_u \exp(b + f(s_u))\big)$$
* **With Physical Area ($a_u = \text{km}^2$):** $\exp(b + f(s_u))$ models **incidents per square kilometer**.
  * *Failure Mode:* Rural agrarian stations in North-West / South-West Delhi (e.g., Alipur, Narela, Chhawla, Najafgarh) have jurisdictions exceeding $50 - 70\text{ km}^2$. The model assigns them an enormous baseline count simply because they occupy empty land.
* **With Population Density ($\rho(s) = \text{residents / km}^2$ from WorldPop / GHSL):**
  * $a_u = \int_{\mathcal{V}_u} \rho(s) ds$ is the total exposed human population.
  * $\exp(b + f(s_u))$ represents the **crimes per capita (epidemiological relative risk)**.
  * *Effect on Missing Persons & Dead Bodies:* Accurately identifies areas where missing person reports are disproportionately high relative to local inhabitants, rather than highlighting them merely because they contain large, unpopulated tracts.
* **With Built-Environment Exposure for Vehicle Theft:**
  * For motor vehicle theft, human residential population can be misleading (vehicles are stolen outside metro transit park-and-rides, commercial hubs like Karol Bagh / Connaught Place, or industrial belts).
  * Setting $\rho(s) = \text{Road Centerline Length (m)} + \beta \cdot \text{Parking/Transit Nodes}$ creates a true opportunity exposure measure for property crime.

---

### 4. Exact Polygon Clipping $\operatorname{Leb}(\mathcal{V}_u \cap \Omega_{\text{Delhi}})$ vs. 7 km Heuristic Bounding Radius

#### A. Flaws of the Current $7\text{ km}$ Bounding Buffer
In [`lgcp_layer.py:L35-L54`](file:///Users/abhyuday/Desktop/DelhiHotspots_ML/src/delhi_hotspots/lgcp_layer.py#L35-L54):
```python
def catchment_areas(xy: np.ndarray, cell_km: float = 0.4, max_radius_km: float = 7.0) -> np.ndarray:
    ...
    nearest, dmin = d.argmin(1), d.min(1)
    keep = dmin <= max_radius_km
    np.add.at(area, nearest[keep], cell_km ** 2)
```
1. **Transboundary Leakage:** Delhi is bounded by Haryana (Gurugram, Faridabad, Sonipat, Jhajjar) and Uttar Pradesh (Noida, Ghaziabad). A $7\text{ km}$ circular radius around Kapashera, Badarpur, or Anand Vihar extends several kilometers across state borders into jurisdictions where Delhi Police have no jurisdiction and ZIPNET records zero events.
2. **Boundary Truncation Holes:** Rural stations separated by $> 7\text{ km}$ drop unassigned grid cells inside Delhi, creating artificial internal "voids".
3. **Partition Violation:**
   $$\bigcup_{u=1}^N \mathcal{V}_u \neq \Omega_{\text{Delhi}}, \qquad \sum_{u=1}^N a_u \neq \operatorname{Area}(\text{NCT of Delhi}) \approx 1,483 \text{ km}^2$$

#### B. The Effect of Exact Clipping: $a_u = \operatorname{Leb}(\mathcal{V}_u \cap \Omega_{\text{Delhi}})$
Using Shapely / GEOS to compute the exact polygon intersection against the dissolved boundary from [`delhi_election_districts.geojson`](file:///Users/abhyuday/Desktop/DelhiHotspots_ML/data/reference/delhi_election_districts.geojson):
1. **Mathematical Partition Guarantee:**
   $$\sum_{u=1}^N a_u = \operatorname{Area}(\Omega_{\text{Delhi}}) \equiv 1,483.0 \text{ km}^2 \quad \text{and} \quad \mathcal{V}_i \cap \mathcal{V}_j = \emptyset \quad (\forall i \neq j)$$
2. **Eliminates Transboundary Distortion in the Laplace Approximation:**
   The Laplace marginal likelihood currently overestimates the baseline rate $b = \log(\sum y / \sum a_u)$ because $\sum a_u$ includes unmonitored land in Haryana and Uttar Pradesh. Exact clipping forces the GP log-intensity to represent strictly Delhi's municipal territory.
3. **Corrects Matérn Kernel Hyperparameters ($\ell, \sigma^2$):**
   Boundary stations will no longer have artificially inflated catchment areas, preventing the Newton solver from pushing the spatial lengthscale $\ell$ to overly diffuse values ($16\text{ km}$) to compensate for edge leakage.

---

### 5. Architectural Trade-Off & Impact Matrix

| Dimension | Current Implementation | Proposed Measure-Theoretic Approach | Practical Impact on System |
| :--- | :--- | :--- | :--- |
| **Log-Loss & Perplexity** | Discrete counting measure ($-\sum q_u \log p_u$). Inflated by partition cardinality and central station density. | Continuous density cross-entropy ($-\sum q_u \log(p_u / a_u)$) or common mesh KL. | Eliminates the false appearance of Metro outperforming Police Stations by $5.7\times$. Enables valid cross-dataset comparisons. |
| **Spatial Exposure ($a_u$)** | Physical geographic area (km² via $0.4\text{ km}$ grid MC integral). | Population measure $\int_{\mathcal{V}_u} \rho(s)ds$ or road density network. | Shifts predictions from "empty land crime density" to "per-capita victimization risk". De-biases large rural stations. |
| **Boundary Geometry** | Heuristic Euclidean buffer ($d \le 7.0\text{ km}$). | Exact polygon clipping ($\mathcal{V}_u \cap \Omega_{\text{Delhi}}$) using Shapely. | Guarantees $\sum a_u = 1,483\text{ km}^2$. Eliminates transboundary leakage into UP/Haryana. |
| **Computational Overhead** | High-speed NumPy vectorized Euclidean distance matrix ($\sim 15\text{ ms}$). | Requires polygon clipping (Shapely) and 2D raster sampling (GDAL/Rasterio). | One-time offline precomputation ($\sim 2 - 5\text{ s}$) stored in `police_unit_catalogue.json`. Zero overhead at inference! |
| **Operational Utility for Law Enforcement** | Ranks administrative police station jurisdictions by volume. | Can isolate both **Volume Hotspots** (patrol dispatch) and **Per-Capita Risk Hotspots** (root-cause intervention). | Beat officers get dual-perspective briefs: patrol resources where incidents cluster, and social interventions where per-capita vulnerability spikes. |

---

### 6. Recommended Transition Blueprint (When Ready to Implement)

When you decide to implement this in the codebase, the changes isolate cleanly into three localized modules without breaking existing APIs:

1. **`data/reference/` (Precomputed Static Geometries):**
   * Run a one-time script using `delhi_election_districts.geojson` to compute exact clipped Voronoi polygons $\mathcal{V}_u \cap \Omega_{\text{Delhi}}$ and cache exact $a_u^{\text{area}}$ and $a_u^{\text{pop}}$ values directly into `police_unit_catalogue.json` and `metro_unit_catalogue.json`.
2. **[`src/delhi_hotspots/lgcp_layer.py`](file:///Users/abhyuday/Desktop/DelhiHotspots_ML/src/delhi_hotspots/lgcp_layer.py):**
   * Replace the heuristic grid Monte-Carlo function `catchment_areas()` with direct lookup of precomputed clipped areas.
   * Parameterize `fit_lgcp_base(..., exposure=areas_or_pop)` to accept population offsets.
3. **[`src/delhi_hotspots/evaluate_rolling_origin.py`](file:///Users/abhyuday/Desktop/DelhiHotspots_ML/src/delhi_hotspots/evaluate_rolling_origin.py):**
   * Retain the existing discrete metrics (`accuracy`, `f1`, `average_precision`) for backward compatibility with the dashboard.
   * Add continuous Lebesgue cross-entropy and area-corrected perplexity:
     ```python
     continuous_log_loss = logloss + sum(target[u] * math.log(areas[u]) for u in units)
     ```
   * Compute $D_{\text{KL}}$ on a unified $100\text{ m}$ raster grid to provide an authoritative, cross-dataset benchmark across all four incident types.