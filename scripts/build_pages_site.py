#!/usr/bin/env python3
"""
Oculon Static Web Portal Builder & Cross-Browser Engine
------------------------------------------------------
Builds the static GitHub Pages deployment payload for Account B (tesseractthou-code/tessracting-oculon).
Supports all modern browsers:
- Google Chrome (Desktop, Android, iOS)
- Microsoft Edge (Windows, Mac, iOS, Android, High-Contrast mode)
- Brave Browser (Brave Shields, aggressive ad-blocking, local font fallback)
- Safari / WebKit (macOS, iOS)
- Firefox / Gecko
"""

import os
import shutil
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "dist_pages"

INDEX_HTML_CONTENT = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>OCULON | Predictive Crime & Hotspot Intelligence Assistant (Delhi Police ZIPNET)</title>
  <meta name="description" content="Predictive Crime & Incident Hotspot Mapping Assistant for Delhi NCR. Live interactive GIS maps powered by Multigram Markov and Log-Gaussian Cox Process (LGCP) models across Chrome, Edge, Brave, and Safari.">
  <meta name="theme-color" content="#090d16">
  <meta name="color-scheme" content="dark light">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>👁️</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #070a12;
      --card-bg: rgba(15, 23, 42, 0.88);
      --card-bg-solid: #0f172a;
      --border-color: rgba(255, 255, 255, 0.12);
      --border-focus: rgba(96, 165, 250, 0.6);
      --primary-accent: #3b82f6;
      --primary-glow: rgba(59, 130, 246, 0.4);
      --danger-accent: #ef4444;
      --warning-accent: #f59e0b;
      --success-accent: #10b981;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --nav-height: 60px;
      --tabs-height: 48px;
      --footer-height: 38px;
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }

    html {
      -webkit-text-size-adjust: 100%;
      text-size-adjust: 100%;
      height: 100%;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      min-height: 100vh;
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeLegibility;
    }

    /* Custom Cross-Browser Scrollbar (Chrome, Edge, Brave, Safari, Firefox) */
    * {
      scrollbar-width: thin;
      scrollbar-color: rgba(255, 255, 255, 0.22) transparent;
    }
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.2);
      border-radius: 9999px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: rgba(255, 255, 255, 0.38);
    }

    header {
      background: rgba(10, 16, 29, 0.94);
      -webkit-backdrop-filter: blur(16px);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-color);
      padding: 0.65rem 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
      min-height: var(--nav-height);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      text-decoration: none;
      color: inherit;
    }

    .brand-icon {
      font-size: 1.75rem;
      line-height: 1;
      filter: drop-shadow(0 0 10px var(--primary-accent));
      user-select: none;
      -webkit-user-select: none;
    }

    .brand-title {
      font-size: 1.2rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #60a5fa;
      background: linear-gradient(135deg, #60a5fa 10%, #c084fc 90%);
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-sub {
      font-size: 0.72rem;
      color: var(--text-muted);
      font-weight: 500;
      letter-spacing: 0.01em;
    }

    .nav-links {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      flex-wrap: wrap;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.32rem 0.7rem;
      border-radius: 9999px;
      font-size: 0.74rem;
      font-weight: 600;
      text-decoration: none;
      transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
      border: 1px solid var(--border-color);
      background: var(--card-bg);
      color: var(--text-main);
      cursor: pointer;
      user-select: none;
      -webkit-user-select: none;
    }

    .badge:hover {
      border-color: var(--primary-accent);
      box-shadow: 0 0 12px var(--primary-glow);
      transform: translateY(-1px);
    }

    .badge-primary {
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      border: 1px solid #3b82f6;
      color: #fff;
    }

    .badge-engine {
      background: rgba(16, 185, 129, 0.12);
      border-color: rgba(16, 185, 129, 0.35);
      color: #34d399;
    }

    .dot-live {
      width: 7px;
      height: 7px;
      background-color: var(--success-accent);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--success-accent);
      animation: pulse 2s infinite;
      flex-shrink: 0;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }

    .tabs-bar {
      background: #0b1120;
      border-bottom: 1px solid var(--border-color);
      padding: 0.4rem 1.25rem;
      display: flex;
      gap: 0.45rem;
      overflow-x: auto;
      white-space: nowrap;
      -webkit-overflow-scrolling: touch;
      touch-action: pan-x;
    }

    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 0.42rem 0.85rem;
      border-radius: 7px;
      font-size: 0.81rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.38rem;
      white-space: nowrap;
      transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
      user-select: none;
      -webkit-user-select: none;
      outline: none;
    }

    .tab-btn:hover {
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-main);
    }

    .tab-btn:focus-visible {
      border-color: var(--primary-accent);
      box-shadow: 0 0 0 2px var(--primary-glow);
    }

    .tab-btn.active {
      background: rgba(59, 130, 246, 0.16);
      color: #60a5fa;
      border-color: rgba(59, 130, 246, 0.45);
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
    }

    .main-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      position: relative;
      background: #faf9f4;
      min-height: 0;
    }

    .map-frame-wrapper {
      flex: 1;
      width: 100%;
      height: calc(100vh - 146px);
      height: calc(100dvh - 146px);
      min-height: 580px;
      position: relative;
      background: #faf9f4;
      overflow: hidden;
    }

    iframe {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      border: none;
      display: block;
      background: #faf9f4;
    }

    .controls-overlay {
      position: absolute;
      top: 0.65rem;
      right: 1rem;
      z-index: 50;
      display: flex;
      gap: 0.45rem;
      pointer-events: auto;
    }

    .btn-action {
      background: rgba(15, 23, 42, 0.88);
      -webkit-backdrop-filter: blur(10px);
      backdrop-filter: blur(10px);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.42rem 0.8rem;
      border-radius: 7px;
      font-size: 0.77rem;
      font-weight: 600;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.38rem;
      transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
      cursor: pointer;
      user-select: none;
      -webkit-user-select: none;
      outline: none;
    }

    .btn-action:hover {
      background: var(--primary-accent);
      border-color: var(--primary-accent);
      box-shadow: 0 0 14px var(--primary-glow);
    }

    .btn-action:focus-visible {
      box-shadow: 0 0 0 2px #fff, 0 0 0 4px var(--primary-accent);
    }

    footer {
      background: #080d1a;
      border-top: 1px solid var(--border-color);
      padding: 0.55rem 1.25rem;
      font-size: 0.74rem;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.5rem;
      min-height: var(--footer-height);
    }

    footer a {
      color: #60a5fa;
      text-decoration: none;
      transition: color 0.15s ease;
    }

    footer a:hover {
      color: #93c5fd;
      text-decoration: underline;
    }

    /* Cross-Browser Accessible Glass Dialog Modal */
    dialog#info-modal {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: min(92vw, 680px);
      background: rgba(15, 23, 42, 0.96);
      -webkit-backdrop-filter: blur(20px);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.18);
      border-radius: 12px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.65), 0 0 25px rgba(59, 130, 246, 0.25);
      color: var(--text-main);
      padding: 1.5rem;
      z-index: 1000;
      outline: none;
    }

    dialog#info-modal::backdrop {
      background: rgba(4, 7, 18, 0.75);
      -webkit-backdrop-filter: blur(6px);
      backdrop-filter: blur(6px);
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border-color);
    }

    .modal-title {
      font-size: 1.15rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #60a5fa;
    }

    .modal-close {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 1rem;
      transition: background 0.15s ease, color 0.15s ease;
    }

    .modal-close:hover {
      background: #ef4444;
      color: #fff;
      border-color: #ef4444;
    }

    .modal-body {
      font-size: 0.85rem;
      line-height: 1.6;
      color: #cbd5e1;
    }

    .modal-body p {
      margin-bottom: 0.75rem;
    }

    .modal-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 0.75rem;
      margin: 1rem 0;
    }

    .modal-stat {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-color);
      padding: 0.75rem;
      border-radius: 8px;
    }

    .modal-stat-title {
      font-size: 0.72rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.25rem;
    }

    .modal-stat-val {
      font-size: 1.05rem;
      font-weight: 700;
      color: #f8fafc;
    }

    /* Windows High Contrast Mode Resilience */
    @media (forced-colors: active) {
      .badge, .tab-btn, .btn-action, dialog#info-modal {
        border: 2px solid ButtonText !important;
      }
      .tab-btn.active {
        background: Highlight !important;
        color: HighlightText !important;
      }
      .dot-live {
        background: Highlight !important;
      }
    }

    @media (max-width: 768px) {
      header {
        flex-direction: column;
        align-items: flex-start;
        padding: 0.6rem 1rem;
        gap: 0.5rem;
      }
      .nav-links {
        width: 100%;
        overflow-x: auto;
        padding-bottom: 0.2rem;
      }
      .tabs-bar {
        padding: 0.4rem 0.75rem;
      }
      .controls-overlay {
        top: 0.5rem;
        right: 0.75rem;
      }
      .map-frame-wrapper {
        height: calc(100vh - 170px);
        height: calc(100dvh - 170px);
      }
    }
  </style>
</head>
<body>

  <header role="banner">
    <a href="#" class="brand" aria-label="Oculon Home">
      <div class="brand-icon">👁️</div>
      <div>
        <h1 class="brand-title">OCULON</h1>
        <div class="brand-sub">Delhi Police ZIPNET Spatiotemporal Predictive Hotspot System</div>
      </div>
    </a>
    <nav class="nav-links" aria-label="Quick links">
      <div class="badge badge-engine" id="browser-engine-badge"><span class="dot-live"></span> Universal Browser Engine</div>
      <a href="https://abhyudaymishr-oculon.hf.space" target="_blank" rel="noopener noreferrer" class="badge">🤗 HF Space</a>
      <a href="https://abhyudaymishr-oculon.hf.space/mcp" target="_blank" rel="noopener noreferrer" class="badge">🔌 MCP Streamable HTTP</a>
      <a href="https://github.com/abhyudaymishr/bob-ai-hackathon-oculon" target="_blank" rel="noopener noreferrer" class="badge badge-primary">GitHub Source</a>
    </nav>
  </header>

  <nav class="tabs-bar" role="tablist" aria-label="Available crime hotspot map views">
    <button role="tab" aria-selected="true" class="tab-btn active" onclick="switchMap('maps/four_dataset_hotspot_explorer.html', this)">
      🗺️ Delhi Street Map & Hotspot Explorer (All-in-One)
    </button>
    <button role="tab" aria-selected="false" class="tab-btn" onclick="switchMap('maps/missing_persons_map.html', this)">
      🔵 Missing Persons Spatiotemporal Map
    </button>
    <button role="tab" aria-selected="false" class="tab-btn" onclick="switchMap('maps/stolen_vehicles_map.html', this)">
      🔴 Stolen Vehicles (Metro & PIN Centroids)
    </button>
    <button role="tab" aria-selected="false" class="tab-btn" onclick="switchMap('maps/mobiles_and_bodies_map.html', this)">
      🟣 Bodies & Mobiles Timeline Map
    </button>
  </nav>

  <main class="main-container">
    <div class="controls-overlay">
      <button onclick="toggleFullscreen()" class="btn-action" title="Toggle Fullscreen" id="fs-toggle-btn">
        ⛶ Fullscreen
      </button>
      <a id="fullscreen-btn" href="maps/four_dataset_hotspot_explorer.html" target="_blank" rel="noopener noreferrer" class="btn-action" title="Open Map Standalone">
        ↗ Standalone Map
      </a>
      <button onclick="openInfoModal()" class="btn-action" title="View Model Context & Architecture">
        ℹ️ Model Rationale
      </button>
    </div>

    <div class="map-frame-wrapper">
      <iframe id="map-frame" src="maps/four_dataset_hotspot_explorer.html" title="Oculon Map Explorer" loading="eager" allow="geolocation" sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-downloads allow-modals"></iframe>
    </div>
  </main>

  <!-- Modern Accessible Glass Modal Dialog -->
  <dialog id="info-modal" aria-labelledby="modal-title-heading">
    <div class="modal-header">
      <div class="modal-title" id="modal-title-heading">
        <span>👁️</span> OCULON Predictive Crime System
      </div>
      <button class="modal-close" onclick="closeInfoModal()" aria-label="Close dialog">×</button>
    </div>
    <div class="modal-body">
      <p>
        <strong>Operational Real-World Objective:</strong> Built for Delhi Police Station House Officers (SHOs) to transform historical ZIPNET incident sink logs into weekly predictive beat-patrol deployments.
      </p>

      <div class="modal-grid">
        <div class="modal-stat">
          <div class="modal-stat-title">Statistical Machine Learning Engine</div>
          <div class="modal-stat-val">Multigram Markov + LGCP</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-title">Spatial Micro-Zone Coverage</div>
          <div class="modal-stat-val">210 PS · 259 Metro · 98 PIN</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-title">Historical Training Archive</div>
          <div class="modal-stat-val">142,000+ Verified Records</div>
        </div>
        <div class="modal-stat">
          <div class="modal-stat-title">Cross-Browser Support</div>
          <div class="modal-stat-val">Chrome · Edge · Brave · Safari</div>
        </div>
      </div>

      <p style="font-size:0.8rem;color:#94a3b8;margin-top:0.75rem;">
        ⚡ <strong>Model Context Protocol (MCP) Integration:</strong> Autonomous agents (Claude, Cursor, AGY) can connect to the remote SSE endpoint at:
        <br><code style="color:#60a5fa;font-family:'JetBrains Mono',monospace;">https://abhyudaymishr-oculon.hf.space/gradio_api/mcp/sse</code>
      </p>
    </div>
  </dialog>

  <footer role="contentinfo">
    <div>
      <strong>Oculon Team</strong>: Abhyuday Mishra (Lead) · Abhishek Kumar · Shivam Ahirwal · Aditya Soni | IBM Bob AI Hackathon 2026
    </div>
    <div>
      Hosted via GitHub Pages on <a href="https://github.com/tesseractthou-code/tessracting-oculon" target="_blank" rel="noopener noreferrer">tesseractthou-code/tessracting-oculon</a>
    </div>
  </footer>

  <script>
    // Tab Switching
    function switchMap(path, btn) {
      const frame = document.getElementById('map-frame');
      const fsBtn = document.getElementById('fullscreen-btn');
      if (frame) frame.src = path;
      if (fsBtn) fsBtn.href = path;
      document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
    }

    // Modal Control (Standard HTML5 Dialog API with fallback)
    const modal = document.getElementById('info-modal');
    function openInfoModal() {
      if (modal && typeof modal.showModal === 'function') {
        modal.showModal();
      } else if (modal) {
        modal.setAttribute('open', '');
      }
    }
    function closeInfoModal() {
      if (modal && typeof modal.close === 'function') {
        modal.close();
      } else if (modal) {
        modal.removeAttribute('open');
      }
    }
    if (modal) {
      modal.addEventListener('click', (e) => {
        const rect = modal.getBoundingClientRect();
        if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) {
          closeInfoModal();
        }
      });
    }

    // Universal Cross-Browser Fullscreen API (Chrome, Edge, Brave, Safari, Firefox)
    function toggleFullscreen() {
      const doc = window.document;
      const elem = document.querySelector('.map-frame-wrapper') || doc.documentElement;
      const isFs = doc.fullscreenElement || doc.webkitFullscreenElement || doc.mozFullScreenElement || doc.msFullscreenElement;
      
      if (!isFs) {
        if (elem.requestFullscreen) {
          elem.requestFullscreen().catch(() => {});
        } else if (elem.webkitRequestFullscreen) {
          elem.webkitRequestFullscreen();
        } else if (elem.mozRequestFullScreen) {
          elem.mozRequestFullScreen();
        } else if (elem.msRequestFullscreen) {
          elem.msRequestFullscreen();
        }
      } else {
        if (doc.exitFullscreen) {
          doc.exitFullscreen().catch(() => {});
        } else if (doc.webkitExitFullscreen) {
          doc.webkitExitFullscreen();
        } else if (doc.mozCancelFullScreen) {
          doc.mozCancelFullScreen();
        } else if (doc.msExitFullscreen) {
          doc.msExitFullscreen();
        }
      }
    }

    // Dynamic Browser Detection & Status Badge
    (function detectBrowser() {
      const ua = navigator.userAgent;
      let browserName = "Universal Web Browser";
      if (navigator.brave && typeof navigator.brave.isBrave === 'function') {
        browserName = "Brave Verified (Shields Active)";
      } else if (ua.indexOf("Edg/") > -1) {
        browserName = "Microsoft Edge Engine";
      } else if (ua.indexOf("Chrome") > -1 && ua.indexOf("Chromium") === -1) {
        browserName = "Google Chrome Engine";
      } else if (ua.indexOf("Safari") > -1 && ua.indexOf("Chrome") === -1) {
        browserName = "Apple Safari WebKit";
      } else if (ua.indexOf("Firefox") > -1) {
        browserName = "Mozilla Firefox Gecko";
      }
      const badge = document.getElementById('browser-engine-badge');
      if (badge) {
        badge.innerHTML = `<span class="dot-live"></span> ${browserName}`;
      }
    })();
  </script>
</body>
</html>
"""

PAGES_REPO_README = """# 👁️ Oculon Web Maps (GitHub Pages Portal)

Live static web map mirror for **OCULON: Predictive Crime Hotspot Mapping Assistant**.
Optimized for **Google Chrome**, **Microsoft Edge**, **Brave Browser**, **Apple Safari**, and **Mozilla Firefox**.

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
    print("    [+] Created cross-browser index.html portal")

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
