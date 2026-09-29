#!/usr/bin/env python3
"""
Oculon Static Web Portal Builder
--------------------------------
Builds the static GitHub Pages deployment payload for Account B (tesseractthou-code/tessracting-oculon).
Packaging:
1. index.html - Modern, responsive web portal embedding the Oculon Hotspot Explorer with tabs for individual maps.
2. maps/ - Directory containing all 4 self-contained HTML maps.
3. .nojekyll - Prevents GitHub Pages from ignoring files with underscores.
4. README.md - Documentation for the generated GitHub Pages repository.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
MAPS_SRC_DIR = ROOT_DIR / "hf_space" / "maps" if (ROOT_DIR / "hf_space" / "maps").exists() else ROOT_DIR / "app"
OUTPUT_DIR = ROOT_DIR / "dist_pages"

INDEX_HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OCULON | Spatiotemporal Urban Risk & Crime Hotspot Explorer</title>
  <meta name="description" content="Predictive Crime & Incident Hotspot Mapping Assistant for Delhi NCR. Live interactive GIS maps powered by Multigram Markov and Log-Gaussian Cox Process (LGCP) models.">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>👁️</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #090d16;
      --card-bg: rgba(18, 25, 41, 0.85);
      --border-color: rgba(255, 255, 255, 0.12);
      --primary-accent: #3b82f6;
      --primary-glow: rgba(59, 130, 246, 0.35);
      --danger-accent: #ef4444;
      --warning-accent: #f59e0b;
      --success-accent: #10b981;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    header {
      background: rgba(10, 16, 29, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      padding: 0.85rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .brand-icon {
      font-size: 1.8rem;
      filter: drop-shadow(0 0 12px var(--primary-accent));
    }

    .brand-title {
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #60a5fa, #a855f7);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .nav-links {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s ease;
      border: 1px solid var(--border-color);
      background: var(--card-bg);
      color: var(--text-main);
    }

    .badge:hover {
      border-color: var(--primary-accent);
      box-shadow: 0 0 12px var(--primary-glow);
      transform: translateY(-1px);
    }

    .badge-primary {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      border: none;
      color: #fff;
    }

    .dot-live {
      width: 7px;
      height: 7px;
      background-color: var(--success-accent);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--success-accent);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    .tabs-bar {
      background: #0f172a;
      border-bottom: 1px solid var(--border-color);
      padding: 0.5rem 1.5rem;
      display: flex;
      gap: 0.5rem;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 0.45rem 1rem;
      border-radius: 8px;
      font-size: 0.825rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      white-space: nowrap;
      transition: all 0.2s ease;
    }

    .tab-btn:hover {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-main);
    }

    .tab-btn.active {
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border-color: rgba(59, 130, 246, 0.4);
    }

    .main-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      position: relative;
    }

    .map-frame-wrapper {
      flex: 1;
      width: 100%;
      height: calc(100vh - 130px);
      position: relative;
      background: #060911;
    }

    iframe {
      width: 100%;
      height: 100%;
      border: none;
      display: block;
    }

    .controls-overlay {
      position: absolute;
      top: 1rem;
      right: 1.5rem;
      z-index: 50;
      display: flex;
      gap: 0.5rem;
    }

    .btn-action {
      background: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: all 0.2s ease;
      cursor: pointer;
    }

    .btn-action:hover {
      background: var(--primary-accent);
      border-color: var(--primary-accent);
      box-shadow: 0 0 15px var(--primary-glow);
    }

    footer {
      background: #0a0f1d;
      border-top: 1px solid var(--border-color);
      padding: 0.65rem 1.5rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    footer a {
      color: #60a5fa;
      text-decoration: none;
    }

    footer a:hover {
      text-decoration: underline;
    }

    @media (max-width: 768px) {
      header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.6rem;
      }
      .nav-links {
        width: 100%;
        overflow-x: auto;
      }
      .map-frame-wrapper {
        height: calc(100vh - 170px);
      }
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">👁️</div>
      <div>
        <div class="brand-title">OCULON</div>
        <div class="brand-sub">Delhi Police ZIPNET Spatiotemporal Predictive Hotspot System</div>
      </div>
    </div>
    <div class="nav-links">
      <div class="badge"><span class="dot-live"></span> Live Web Maps</div>
      <a href="https://abhyudaymishr-oculon.hf.space" target="_blank" class="badge">🤗 HF ZeroGPU Space</a>
      <a href="https://abhyudaymishr-oculon.hf.space/gradio_api/mcp/sse" target="_blank" class="badge">🔌 MCP SSE Server</a>
      <a href="https://github.com/abhyudaymishr/bob-ai-hackathon-oculon" target="_blank" class="badge badge-primary">GitHub Source</a>
    </div>
  </header>

  <div class="tabs-bar">
    <button class="tab-btn active" onclick="switchMap('maps/four_dataset_hotspot_explorer.html', this)">
      🌐 Four-Dataset Hotspot Explorer (All-in-One)
    </button>
    <button class="tab-btn" onclick="switchMap('maps/missing_persons_map.html', this)">
      🔵 Missing Persons Spatiotemporal Map
    </button>
    <button class="tab-btn" onclick="switchMap('maps/stolen_vehicles_map.html', this)">
      🔴 Stolen Vehicles (Metro & PIN Centroids)
    </button>
    <button class="tab-btn" onclick="switchMap('maps/mobiles_and_bodies_map.html', this)">
      🟣 Bodies & Mobiles Timeline Map
    </button>
  </div>

  <div class="main-container">
    <div class="controls-overlay">
      <a id="fullscreen-btn" href="maps/four_dataset_hotspot_explorer.html" target="_blank" class="btn-action">
        ↗ Open Fullscreen Map
      </a>
      <button onclick="toggleInfoModal()" class="btn-action">
        ℹ️ Model Rationale
      </button>
    </div>

    <div class="map-frame-wrapper">
      <iframe id="map-frame" src="maps/four_dataset_hotspot_explorer.html" title="Oculon Map Explorer"></iframe>
    </div>
  </div>

  <footer>
    <div>
      <strong>Oculon Team</strong>: Abhyuday Mishra (Lead) · Abhishek Kumar · Shivam Ahirwal · Aditya Soni | IBM Bob AI Hackathon 2026
    </div>
    <div>
      Hosted via GitHub Pages on <a href="https://github.com/tesseractthou-code/tessracting-oculon" target="_blank">tesseractthou-code/tessracting-oculon</a>
    </div>
  </footer>

  <script>
    function switchMap(path, btn) {
      document.getElementById('map-frame').src = path;
      document.getElementById('fullscreen-btn').href = path;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }

    function toggleInfoModal() {
      alert("OCULON PREDICTIVE CRIME SYSTEM\\n\\n" +
            "• Mathematical Engine: High-Order Multigram Markov Process + Log-Gaussian Cox Process (LGCP)\\n" +
            "• Spatial Resolution: 210 Delhi Police Station polygons, 259 Metro stops, 98 PIN sectors\\n" +
            "• Data Foundation: 142,000+ historical records across Delhi ZIPNET incident sinks\\n" +
            "• Station House Officer (SHO) Patrol Redeployment: Weekly dynamic patrol briefs targeting top-5 micro-zones\\n\\n" +
            "To connect AI agents via Model Context Protocol (MCP):\\nhttps://abhyudaymishr-oculon.hf.space/gradio_api/mcp/sse");
    }
  </script>
</body>
</html>
"""

PAGES_REPO_README = """# 👁️ Oculon Web Maps (GitHub Pages Portal)

Live static web map mirror for **OCULON: Predictive Crime Hotspot Mapping Assistant**.

- **Live Website**: [https://tesseractthou-code.github.io/tessracting-oculon/](https://tesseractthou-code.github.io/tessracting-oculon/)
- **Upstream Source Code**: [https://github.com/abhyudaymishr/bob-ai-hackathon-oculon](https://github.com/abhyudaymishr/bob-ai-hackathon-oculon)
- **Live Hugging Face Space & MCP Server**: [https://abhyudaymishr-oculon.hf.space](https://abhyudaymishr-oculon.hf.space)

---

## 🗺️ Available Maps

| Map View | File Route |
| :--- | :--- |
| **All-in-One Hotspot Explorer** | [`/maps/four_dataset_hotspot_explorer.html`](./maps/four_dataset_hotspot_explorer.html) |
| **Missing Persons Spatiotemporal Map** | [`/maps/missing_persons_map.html`](./maps/missing_persons_map.html) |
| **Stolen Vehicles Hotspot Map** | [`/maps/stolen_vehicles_map.html`](./maps/stolen_vehicles_map.html) |
| **Bodies & Mobiles Timeline Map** | [`/maps/mobiles_and_bodies_map.html`](./maps/mobiles_and_bodies_map.html) |

---

*Automatically generated and deployed via GitHub Actions CI/CD from `abhyudaymishr/bob-ai-hackathon-oculon`.*
"""

def find_map_file(filename: str) -> Optional[Path]:
    candidate_dirs = [
        ROOT_DIR / "maps",
        ROOT_DIR / "src" / "oculon" / "maps",
        ROOT_DIR / "hf_space" / "maps",
        ROOT_DIR / "app",
        ROOT_DIR / "app" / "individual_maps",
    ]
    for d in candidate_dirs:
        candidate = d / filename
        if candidate.exists() and candidate.is_file():
            return candidate
    return None

def build():
    print(f"--> Building Oculon static web pages site...")
    print(f"    Root directory: {ROOT_DIR}")
    print(f"    Output dir:     {OUTPUT_DIR}")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dest_maps_dir = OUTPUT_DIR / "maps"
    dest_maps_dir.mkdir(parents=True, exist_ok=True)

    # Copy all html maps
    map_files = [
        "four_dataset_hotspot_explorer.html",
        "missing_persons_map.html",
        "mobiles_and_bodies_map.html",
        "stolen_vehicles_map.html",
    ]

    for filename in map_files:
        src_file = find_map_file(filename)
        if src_file:
            shutil.copy2(src_file, dest_maps_dir / filename)
            print(f"    [+] Copied map: {filename} from {src_file.parent.name} ({src_file.stat().st_size / 1024:.1f} KB)")
        else:
            raise FileNotFoundError(f"CRITICAL: map file {filename} could not be located in any candidate directory!")

    # Write root index.html
    (OUTPUT_DIR / "index.html").write_text(INDEX_HTML_CONTENT, encoding="utf-8")
    print("    [+] Created index.html portal")

    # Write .nojekyll for GitHub Pages
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print("    [+] Created .nojekyll")

    # Write README.md for pages repo
    (OUTPUT_DIR / "README.md").write_text(PAGES_REPO_README, encoding="utf-8")
    print("    [+] Created README.md")

    print("--> Build complete! Total files generated:")
    for p in OUTPUT_DIR.rglob("*"):
        if p.is_file():
            print(f"    - {p.relative_to(OUTPUT_DIR)} ({p.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    build()
