# Oculon Version 2.0.0: Release Manifest & Decoupled Architecture

**Release Identifier:** `v2.0.0`  
**Architecture Model:** Multi-Account Public Interface with Private Backend Engine  
**Release Date:** October 2026  
**Security Classification:** Strict Public/Private Boundary Isolation  

---

## 1. System Architecture Overview

```
                                 PUBLIC
┌───────────────────────────────────────────────────────────────────────┐
│ GitHub Account B: `tesseractthou-code`                                │
│ Repository: `tessracting-oculon` (GitHub Pages)                       │
│                                                                       │
│ Frontend Component (v2.0.0)                                           │
│ • Zero-dependency interactive SVG maps                                │
│ • Client-side string search & district filter                         │
│ • Real-time dynamic reticle & view panning                            │
│ • Consumes Public API v2 (Zero proprietary code in browser)           │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    │ HTTPS REST API (/api/v2/*)
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ GitHub Account A: `abhyudaymishr`                                     │
│ Repository: `Oculon` (Public Repo & PyPI `oculon`)                  │
│                                                                       │
│ Public Integration Backend & CI/CD (v2.0.0 / API v2)                  │
│ • Public API Client (`src/oculon/client_v2.py`)                       │
│ • Model Context Protocol Server (`src/oculon/mcp_server.py`)          │
│ • Continuous Integration & Deployment Workflows                       │
│ • Release Manifest & Schema Contracts                                │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    │ Invokes (Backend Host)
                                    ▼
                    ┌───────────────────────────────┐
                    │ PRIVATE RUNTIME (v2.1.0)      │
                    │ Hosted on Hugging Face Spaces │
                    │ `AbhyudayMishr/Oculon`        │
                    │                               │
                    │ Proprietary Algorithm Engine  │
                    │ (`internal-v2-lebesgue`)      │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ HUGGING FACE MODEL (v2.0)     │
                    │ `oculon-spatiotemporal-model` │
                    │ Discretized LGCP Poisson GP   │
                    │ + Multigram Markov Ensemble   │
                    └───────────────────────────────┘
```

---

## 2. Release Versioning Matrix

| Component | Target Platform / Host | Version Tag | Exposure Level | Permitted Shipped Content | Prohibited / Quarantined Content |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Frontend** | GitHub Account B (`tesseractthou-code/tessracting-oculon`) via GitHub Pages | `v2.0.0` | **PUBLIC** | • Static HTML maps (`dist_pages/maps/*.html`)<br>• Root portal (`index.html`)<br>• Client JS API consumers | • Proprietary algorithm source<br>• Model training routines<br>• Raw CSVs / PII<br>• Internal tokens / keys |
| **Public Backend** | GitHub Account A (`abhyudaymishr/oculon`) & PyPI (`oculon`) | `v2.0.0`<br>(API `v2`) | **PUBLIC** | • Public API client (`client_v2.py`)<br>• MCP tool schemas<br>• CI/CD workflows<br>• Version manifest (`release_manifest.json`) | • Internal Poisson GP derivations<br>• Private weights / calibration tables<br>• Cloud deployment credentials |
| **Private Runtime** | Hugging Face Spaces (`AbhyudayMishr/Oculon`) | `v2.1.0` | **PRIVATE BACKEND** | • Secure API handlers (`/api/v2/*`)<br>• Gradio 5 server<br>• Proprietary v2 Lebesgue engine | N/A (Server-side execution environment behind HTTPS) |
| **Proprietary Algorithm** | Private Engine (`src/delhi_hotspots/v2_lebesgue_engine.py`) | `internal-rev-2.0.4` | **PROPRIETARY** | • Continuous Lebesgue density engine<br>• Exact polygon boundary clipper<br>• Population exposure offsets | Never committed to public frontend or public git branches |
| **Hugging Face Model** | Model Layer (`oculon-spatiotemporal-hotspot-model`) | `v2.0` | **BACKEND MODEL** | • Trained model matrices<br>• Voronoi catchment lookup table | Shipped only in private inference container |

---

## 3. Mathematical Foundations of Proprietary Algorithm v2 (`change1.md`)

### 3.1 Exact Polygonal Boundary Clipping: $\operatorname{Leb}(\mathcal{V}_u \cap \Omega_{\text{Delhi}})$
* **Limitation of Legacy Heuristic:** The v1 implementation utilized an arbitrary $7.0\text{ km}$ circular bounding buffer. This leaked into Haryana (Gurugram, Sonipat, Faridabad) and Uttar Pradesh (Noida, Ghaziabad), while creating internal unassigned voids in rural Delhi.
* **v2 Exact Clipping:** Uses the official Survey of India 11-district boundaries (`delhi_election_districts.geojson`) to perform exact 2D ray-casting polygon clipping:
  $$\mathcal{V}_u^{\text{clipped}} = \mathcal{V}_u \cap \Omega_{\text{Delhi}}, \qquad a_u = \operatorname{Leb}(\mathcal{V}_u^{\text{clipped}})$$
  $$\sum_{u=1}^N a_u \equiv \operatorname{Area}(\Omega_{\text{Delhi}}) \approx 1,487.12 \text{ km}^2$$
  *Result:* Enforces a strict mathematical partition over the territory of Delhi and corrects edge station catchments in the Laplace GP approximation.

### 3.2 Population and Built-Environment Exposure Offsets
* **Limitation of Raw Physical Area:** Using geographic area ($a_u = \text{km}^2$) artificially inflates outer agrarian jurisdictions (e.g., Alipur, Narela, Bawana at $50-70\text{ km}^2$), giving empty farmland an enormous expected crime baseline.
* **v2 Exposure Measure:** Offsets are parameterized by total exposed human population $\rho(s)$:
  $$a_u^{\text{pop}} = \int_{\mathcal{V}_u} \rho(s) \, ds$$
  $$\tilde{y}_u \mid f_u \sim \operatorname{Poisson}\big(a_u^{\text{pop}} \exp(b + f_u)\big)$$
  *Result:* Shifts model output from raw spatial density (crimes/$\text{km}^2$) to **per-capita relative risk** (crimes per 100,000 residents), isolating true socioeconomic vulnerabilities.

### 3.3 Continuous Lebesgue Density Conversion & Perplexity Paradox Resolution
* **The Mathematical Paradox:**
  Under discrete counting measure ($-\sum q_u \log p_u$), uniform baselines equal $\ln N$.
  * Missing Persons ($N = 193$ police stations): Uniform = $5.263 \text{ nats} \implies \text{Gain} = 5.263 - 4.991 = \mathbf{0.272 \text{ nats}}$
  * Stolen Vehicles ($N = 233$ metro stations): Uniform = $5.451 \text{ nats} \implies \text{Gain} = 5.451 - 3.902 = \mathbf{1.549 \text{ nats}}$
  * *The Trap:* Metro appears to perform $5.7\times$ better simply because central metro Voronoi cells are tiny ($a_u \ll 1\text{ km}^2$), artificially concentrating discrete probability mass.
* **v2 Continuous Density Formulation:**
  Converts predictions to a probability density with respect to the 2D Lebesgue measure:
  $$f(s) = \frac{p(u)}{a_u}, \quad \text{for } s \in \mathcal{V}_u$$
  $$\mathcal{L}_{\text{cont}} = -\int_\Omega q(s) \log f(s) \, ds = \underbrace{-\sum_{u=1}^N q(u) \log p(u)}_{L_{\text{discrete}}} + \underbrace{\sum_{u=1}^N q(u) \log a_u}_{\text{Geometric Area Entropy } \mathbb{E}_q[\log a_u]}$$
  *Resolution:* For metro stations, the area correction $\mathbb{E}_q[\log a_u] = -0.892 \text{ nats}$ correctly penalizes tiny spatial footprints, while police stations have $\mathbb{E}_q[\log a_u] = +1.841 \text{ nats}$. The models are now directly comparable across non-nested partitions.

---

## 4. Public API v2 Specification

Hosted at `https://abhyudaymishr-oculon.hf.space/api/v2/*`:

### `GET /api/v2/manifest`
Returns the public component versioning manifest.
```json
{
  "release_version": "2.0.0",
  "frontend_version": "v2.0.0",
  "public_api": "v2",
  "private_runtime": "v2.1.0",
  "proprietary_algorithm": "internal-v2-lebesgue"
}
```

### `GET /api/v2/hotspots`
Query forecasted hotspots with continuous Lebesgue density and per-capita risk.
* **Parameters:** `dataset`, `month`, `query`, `top_k`, `district`, `include_density`
* **Response:**
```json
{
  "status": "success",
  "dataset": "missing_persons",
  "month": "2026-10",
  "hotspots": [
    {
      "rank": 1,
      "name": "Narela",
      "district": "North",
      "relative_multigram_score": 0.0812,
      "lebesgue_density_per_km2": 0.001249,
      "per_capita_risk_per_100k": 14.82,
      "catchment_area_km2": 65.02,
      "population_exposure": 109500.0
    }
  ],
  "v2_enhancements": {
    "version": "2.0.0",
    "proprietary_engine": "internal-v2-lebesgue",
    "exact_boundary_clipping": "Leb(V_u ∩ Delhi) == 1487.12 km^2",
    "exposure_offset": "Population & Built-environment Measure"
  }
}
```

### `GET /api/v2/risk-density`
Returns the complete continuous spatial density field and exposure offsets across all Delhi units.

### `GET /api/v2/metrics`
Returns both discrete baseline benchmarks and continuous Lebesgue area-entropy-corrected comparisons across datasets.

---

## 5. Security & Decoupling Guarantees

1. **Client Browser Zero-Leakage:**
   * Static web pages on GitHub Account B (`tesseractthou-code/tessracting-oculon`) receive only the aggregated JSON payloads and pre-rendered vector maps.
   * No Python dependencies, mathematical solvers, or training scripts exist in `dist_pages/`.
2. **Public Repository Hygiene:**
   * Account A (`abhyudaymishr/oculon`) maintains only integration clients, CI/CD runners, and public contracts.
   * Proprietary source code (`v2_lebesgue_engine.py`) is quarantined on the private Hugging Face inference backend.
3. **Traceability:**
   * Every release is tracked via `config/release_manifest.json`, allowing independent version upgrades of the frontend (`v2.0.0`), public API (`v2`), and internal proprietary engine (`internal-rev-2.0.4`) without breaking changes.
