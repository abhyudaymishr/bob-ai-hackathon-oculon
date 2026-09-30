#!/usr/bin/env python3
"""
Add Live Aerial View & Tactical Recon HUD to Oculon Hotspot Maps
--------------------------------------------------------------
Enables high-resolution satellite imagery (Esri World Imagery / Maxar)
at sub-meter 0.3m resolution across Delhi NCR when any hotspot marker
is clicked, with interactive tactical concentric surveillance perimeters
(100m, 250m, 500m), multi-spectral sensor simulation (RGB, Hybrid, FLIR, IR),
patrol dispatch simulation, and instant satellite basemap switching.
"""
from pathlib import Path
import re
import shutil

ROOT_DIR = Path("/Users/abhyuday/Desktop/DelhiHotspots_ML")

MAP_FILES = [
    ROOT_DIR / "src" / "oculon" / "maps" / "four_dataset_hotspot_explorer.html",
    ROOT_DIR / "app" / "four_dataset_hotspot_explorer.html",
    ROOT_DIR / "hf_space" / "maps" / "four_dataset_hotspot_explorer.html",
    ROOT_DIR / "hf_space" / "src" / "oculon" / "maps" / "four_dataset_hotspot_explorer.html",
    ROOT_DIR / ".hf_staging" / "Oculon" / "maps" / "four_dataset_hotspot_explorer.html",
    ROOT_DIR / ".hf_staging" / "Oculon" / "src" / "oculon" / "maps" / "four_dataset_hotspot_explorer.html",
    ROOT_DIR / ".hf_staging" / "Oculon" / "dist_pages" / "maps" / "four_dataset_hotspot_explorer.html",
    ROOT_DIR / "dist_pages" / "maps" / "four_dataset_hotspot_explorer.html",
]

AERIAL_CSS = """
/* ====================================================================== */
/* 🛰️ LIVE AERIAL TACTICAL RECONNAISSANCE HUD MODAL & SATELLITE ENGINE     */
/* ====================================================================== */
.aerial-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: rgba(5, 8, 18, 0.88);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: none;
  align-items: center;
  justify-content: center;
  padding: 16px;
  animation: aerialFadeIn 0.22s ease-out;
}
@keyframes aerialFadeIn {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}
.aerial-modal-container {
  width: 95vw;
  max-width: 960px;
  max-height: 92vh;
  background: #090d16;
  border: 1px solid rgba(56, 189, 248, 0.45);
  box-shadow: 0 0 40px rgba(2, 132, 199, 0.4), 0 25px 50px -12px rgba(0, 0, 0, 0.7);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  color: #f8fafc;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.aerial-modal-container.fullscreen {
  width: 100vw;
  max-width: 100vw;
  height: 100vh;
  max-height: 100vh;
  border-radius: 0;
  border: none;
}
.aerial-modal-header {
  padding: 12px 18px;
  background: rgba(15, 23, 42, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.aerial-live-beacon {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #38bdf8;
  margin-bottom: 2px;
}
.pulse-beacon {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 8px #ef4444;
  animation: beaconPulse 1.2s infinite ease-in-out;
}
@keyframes beaconPulse {
  0% { transform: scale(0.9); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.6; }
  100% { transform: scale(0.9); opacity: 1; }
}
.aerial-title {
  font-size: 16px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.01em;
}
.aerial-subtitle {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 1px;
}
.aerial-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.aerial-risk-tag {
  font-size: 11px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 4px;
  letter-spacing: 0.04em;
}
.aerial-btn-icon {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #f8fafc;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
}
.aerial-btn-icon:hover {
  background: rgba(255, 255, 255, 0.18);
}
.aerial-body {
  position: relative;
  width: 100%;
  height: 480px;
  min-height: 340px;
  background: #020617;
  overflow: hidden;
}
.aerial-map-canvas {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  transition: filter 0.3s ease;
}
.aerial-hud-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 2;
}
.hud-telemetry-box {
  position: absolute;
  top: 12px;
  left: 12px;
  background: rgba(10, 15, 29, 0.88);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(56, 189, 248, 0.35);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  gap: 3px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
  pointer-events: auto;
}
.hud-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.hud-row b {
  color: #f1f5f9;
}
.aerial-sensor-controls {
  position: absolute;
  top: 12px;
  right: 56px;
  display: flex;
  gap: 6px;
  pointer-events: auto;
  flex-wrap: wrap;
}
.sensor-btn {
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: #cbd5e1;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}
.sensor-btn:hover {
  background: rgba(30, 41, 59, 0.95);
  border-color: #38bdf8;
  color: #fff;
}
.sensor-btn.active {
  background: #0284c7;
  border-color: #38bdf8;
  color: #fff;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
}
.aerial-modal-footer {
  padding: 10px 18px;
  background: rgba(15, 23, 42, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.footer-left-actions, .footer-right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.action-btn {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  color: #f1f5f9;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  text-decoration: none;
}
.action-btn:hover {
  background: rgba(255, 255, 255, 0.16);
}
.action-btn.primary {
  background: #0284c7;
  border-color: #38bdf8;
  color: #fff;
  font-weight: 700;
}
.action-btn.primary:hover {
  background: #0369a1;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
}
.action-btn.link-btn {
  color: #38bdf8;
}
.aerial-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: #0f172a;
  color: #f8fafc;
  padding: 10px 18px;
  border-radius: 8px;
  border: 1px solid #38bdf8;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  z-index: 100000;
  font-size: 12px;
  animation: toastPop 0.2s ease-out;
  pointer-events: none;
}
@keyframes toastPop {
  from { opacity: 0; transform: translate(-50%, 10px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
@keyframes spinReticle {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
"""

AERIAL_MODAL_HTML = """
<!-- 🛰️ LIVE AERIAL TACTICAL RECONNAISSANCE SATELLITE HUD MODAL -->
<div id="aerial-modal" class="aerial-modal-overlay">
  <div class="aerial-modal-container" id="aerial-modal-box">
    <div class="aerial-modal-header">
      <div class="aerial-header-left">
        <div class="aerial-live-beacon">
          <span class="pulse-beacon"></span>
          <span>LIVE AERIAL RECONNAISSANCE SATELLITE HUD (0.3m/px)</span>
        </div>
        <div id="aerial-loc-title" class="aerial-title">Hotspot Location</div>
        <div id="aerial-loc-subtitle" class="aerial-subtitle">Delhi NCR · High-Res Satellite Telemetry</div>
      </div>
      <div class="aerial-header-right">
        <span id="aerial-risk-tag" class="aerial-risk-tag risk-crit">HOTSPOT</span>
        <button class="aerial-btn-icon" onclick="toggleAerialFullscreen()" title="Toggle Fullscreen">⛶</button>
        <button class="aerial-btn-icon" onclick="closeLiveAerialView()" title="Close Aerial View">✕</button>
      </div>
    </div>

    <div class="aerial-body">
      <div id="aerial-map-canvas" class="aerial-map-canvas"></div>
      <div class="aerial-hud-overlay">
        <div class="hud-telemetry-box">
          <div class="hud-row"><span>SATELLITE SENSOR:</span> <b>ESRI WORLD IMAGERY / MAXAR</b></div>
          <div class="hud-row"><span>RESOLUTION:</span> <b>0.3m/px SUB-METER RECON</b></div>
          <div class="hud-row"><span>TARGET GPS:</span> <b id="hud-gps">28.6250, 77.2150</b></div>
          <div class="hud-row"><span>CURSOR POS:</span> <b id="hud-live-crosshair">28.6250, 77.2150</b></div>
          <div class="hud-row"><span>INCIDENTS / INDEX:</span> <b id="hud-incidents">Active</b></div>
          <div class="hud-row"><span>SURVEILLANCE STATUS:</span> <b id="hud-status-badge" style="color:#ef4444;">ACTIVE TACTICAL CORDON</b></div>
        </div>

        <div class="aerial-sensor-controls">
          <button class="sensor-btn active" onclick="setAerialSensor('satellite', this)">🛰️ Natural Satellite</button>
          <button class="sensor-btn" onclick="setAerialSensor('hybrid', this)">🏙️ Street Overlay</button>
          <button class="sensor-btn" onclick="setAerialSensor('flir', this)">🟢 Night Vision (FLIR)</button>
          <button class="sensor-btn" onclick="setAerialSensor('thermal', this)">🔴 Thermal (IR)</button>
        </div>
      </div>
    </div>

    <div class="aerial-modal-footer">
      <div class="footer-left-actions">
        <button class="action-btn primary" onclick="applyAerialToMainMap()">
          🛰️ Switch Main Map to Satellite View
        </button>
        <button class="action-btn" onclick="simulatePatrolDispatch()">
          🚨 Simulate 3-Patrol Cordon Dispatch
        </button>
        <button class="action-btn" onclick="copyGpsCoordinates()">
          📋 Copy Tactical GPS
        </button>
      </div>
      <div class="footer-right-actions">
        <a id="aerial-google-earth-link" href="#" target="_blank" rel="noopener noreferrer" class="action-btn link-btn">
          🌍 Google Earth 3D ↗
        </a>
        <a id="aerial-google-maps-link" href="#" target="_blank" rel="noopener noreferrer" class="action-btn link-btn">
          📍 Google Maps Satellite ↗
        </a>
      </div>
    </div>
  </div>
</div>
"""

AERIAL_JS = """
// ======================================================================
// 🛰️ LIVE AERIAL TACTICAL RECONNAISSANCE SATELLITE ENGINE
// ======================================================================
let aerialLeafletMap = null;
let aerialSatelliteLayer = null;
let aerialHybridLabelsLayer = null;
let aerialCirclesGroup = null;
let activeAerialLoc = null;

function getTileXYZ(lat, lon, z) {
  const x = Math.floor((lon + 180) / 360 * Math.pow(2, z));
  const latRad = lat * Math.PI / 180;
  const y = Math.floor((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * Math.pow(2, z));
  return `${z}/${y}/${x}`;
}

function openLiveAerialView(lat, lon, name, district, score, count, kind) {
  if (typeof lat !== 'number' || typeof lon !== 'number') return;
  activeAerialLoc = { lat, lon, name, district, score, count, kind };

  const modal = document.getElementById('aerial-modal');
  if (!modal) return;
  modal.style.display = 'flex';

  document.getElementById('aerial-loc-title').textContent = name;
  const distText = district ? district + ' · ' : '';
  const scoreText = score !== undefined && score > 0 ? Number(score).toFixed(4) : 'N/A';
  document.getElementById('aerial-loc-subtitle').textContent = 
    `${distText}Score: ${scoreText} · Coordinates: ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;

  const riskEl = document.getElementById('aerial-risk-tag');
  if (riskEl) {
    if (score >= 0.08 || kind === 'forecast') {
      riskEl.className = 'aerial-risk-tag risk-crit';
      riskEl.textContent = 'CRITICAL HOTSPOT';
    } else if (score >= 0.03) {
      riskEl.className = 'aerial-risk-tag risk-high';
      riskEl.textContent = 'HIGH SURVEILLANCE';
    } else {
      riskEl.className = 'aerial-risk-tag risk-mod';
      riskEl.textContent = 'MONITORED ZONE';
    }
  }

  const gpsEl = document.getElementById('hud-gps');
  if (gpsEl) gpsEl.textContent = `${lat.toFixed(5)}° N, ${lon.toFixed(5)}° E`;
  const incEl = document.getElementById('hud-incidents');
  if (incEl) incEl.textContent = count ? `${count} Incidents` : (score > 0 ? `Risk Index ${score.toFixed(4)}` : 'Monitored Unit');

  const gEarth = document.getElementById('aerial-google-earth-link');
  if (gEarth) gEarth.href = `https://earth.google.com/web/search/${lat},${lon}`;
  const gMaps = document.getElementById('aerial-google-maps-link');
  if (gMaps) gMaps.href = `https://www.google.com/maps/@${lat},${lon},18z/data=!3m1!1e3`;

  // Init or re-center Leaflet Aerial Map
  if (!aerialLeafletMap && window.L) {
    aerialLeafletMap = L.map('aerial-map-canvas', {
      center: [lat, lon],
      zoom: 17,
      minZoom: 13,
      maxZoom: 19,
      zoomControl: false,
      attributionControl: true
    });
    L.control.zoom({ position: 'topright' }).addTo(aerialLeafletMap);

    aerialSatelliteLayer = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.esri.com/" target="_blank">Esri</a>, Maxar, Earthstar Geographics'
      }
    ).addTo(aerialLeafletMap);

    aerialCirclesGroup = L.layerGroup().addTo(aerialLeafletMap);

    aerialLeafletMap.on('mousemove', (e) => {
      const liveGps = document.getElementById('hud-live-crosshair');
      if (liveGps) liveGps.textContent = `${e.latlng.lat.toFixed(5)}° N, ${e.latlng.lng.toFixed(5)}° E`;
    });
  } else if (aerialLeafletMap) {
    aerialLeafletMap.setView([lat, lon], 17);
  }

  // Draw tactical surveillance perimeter rings
  if (aerialCirclesGroup) {
    aerialCirclesGroup.clearLayers();

    // 100m inner cordon (Red)
    L.circle([lat, lon], {
      radius: 100,
      color: '#ef4444',
      weight: 2,
      dashArray: '4, 4',
      fill: true,
      fillColor: '#ef4444',
      fillOpacity: 0.14
    }).addTo(aerialCirclesGroup).bindTooltip('100m Inner Rapid Response Zone', { permanent: false, direction: 'top' });

    // 250m tactical cordon (Amber)
    L.circle([lat, lon], {
      radius: 250,
      color: '#f59e0b',
      weight: 1.6,
      dashArray: '6, 5',
      fill: true,
      fillColor: '#f59e0b',
      fillOpacity: 0.06
    }).addTo(aerialCirclesGroup).bindTooltip('250m Tactical Response Perimeter', { permanent: false, direction: 'top' });

    // 500m area surveillance boundary (Cyan)
    L.circle([lat, lon], {
      radius: 500,
      color: '#06b6d4',
      weight: 1.5,
      dashArray: '8, 6',
      fill: false
    }).addTo(aerialCirclesGroup).bindTooltip('500m Outer Surveillance Radius', { permanent: false, direction: 'top' });

    // Center target reticle marker
    const crosshairIcon = L.divIcon({
      className: 'tactical-target-reticle',
      html: `
        <div style="position:relative;width:40px;height:40px;margin-left:-20px;margin-top:-20px;pointer-events:none;">
          <div style="position:absolute;inset:0;border:2px solid #ef4444;border-radius:50%;box-shadow:0 0 10px #ef4444, inset 0 0 10px rgba(239,68,68,0.5);animation:spinReticle 6s linear infinite;"></div>
          <div style="position:absolute;top:50%;left:0;right:0;height:1px;background:#ef4444;box-shadow:0 0 4px #ef4444"></div>
          <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:#ef4444;box-shadow:0 0 4px #ef4444"></div>
          <div style="position:absolute;top:50%;left:50%;width:6px;height:6px;margin:-3px;background:#ffffff;border-radius:50%;box-shadow:0 0 6px #ffffff"></div>
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 20]
    });
    L.marker([lat, lon], { icon: crosshairIcon }).addTo(aerialCirclesGroup);
  }

  [50, 150, 350, 600].forEach(delay => {
    setTimeout(() => { if (aerialLeafletMap) aerialLeafletMap.invalidateSize(); }, delay);
  });
}

function closeLiveAerialView() {
  const modal = document.getElementById('aerial-modal');
  if (modal) modal.style.display = 'none';
}

function toggleAerialFullscreen() {
  const box = document.getElementById('aerial-modal-box');
  if (box) {
    box.classList.toggle('fullscreen');
    setTimeout(() => { if (aerialLeafletMap) aerialLeafletMap.invalidateSize(); }, 100);
  }
}

function setAerialSensor(type, btn) {
  document.querySelectorAll('.sensor-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const canvas = document.getElementById('aerial-map-canvas');
  if (!canvas) return;

  if (aerialHybridLabelsLayer && aerialLeafletMap) {
    aerialLeafletMap.removeLayer(aerialHybridLabelsLayer);
    aerialHybridLabelsLayer = null;
  }

  canvas.style.filter = 'none';

  if (type === 'satellite') {
    canvas.style.filter = 'contrast(1.05) brightness(1.02)';
  } else if (type === 'hybrid') {
    canvas.style.filter = 'contrast(1.05) brightness(1.02)';
    if (aerialLeafletMap) {
      aerialHybridLabelsLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
        zIndex: 400
      }).addTo(aerialLeafletMap);
    }
  } else if (type === 'flir') {
    canvas.style.filter = 'grayscale(100%) brightness(1.3) contrast(1.5) sepia(100%) hue-rotate(85deg) saturate(3.5)';
  } else if (type === 'thermal') {
    canvas.style.filter = 'invert(100%) hue-rotate(180deg) saturate(3) contrast(1.6)';
  }
}

function simulatePatrolDispatch() {
  if (!activeAerialLoc || !aerialLeafletMap) return;
  const { lat, lon, name } = activeAerialLoc;
  
  const statusEl = document.getElementById('hud-status-badge');
  if (statusEl) {
    statusEl.innerHTML = '🚨 <span style="color:#22c55e">3 PATROL UNITS DISPATCHED (CORDON ACTIVE)</span>';
  }

  const patrolUnits = [
    { name: 'PCR Cobra-1', bearing: 45, dist: 0.005, color: '#38bdf8' },
    { name: 'PCR Cheetah-2', bearing: 165, dist: 0.006, color: '#f59e0b' },
    { name: 'PCR Hawk-3', bearing: 285, dist: 0.0055, color: '#ec4899' }
  ];

  patrolUnits.forEach((unit, idx) => {
    const uLat = lat + Math.sin(unit.bearing * Math.PI / 180) * unit.dist;
    const uLon = lon + Math.cos(unit.bearing * Math.PI / 180) * unit.dist;
    
    const carIcon = L.divIcon({
      className: 'patrol-unit-icon',
      html: `
        <div style="background:${unit.color};color:#000;padding:2px 6px;border-radius:4px;font-size:9px;font-weight:800;white-space:nowrap;box-shadow:0 0 8px ${unit.color};display:flex;align-items:center;gap:3px">
          <span>🚓</span> ${unit.name} <span style="font-size:8px;opacity:0.8">ETA 1.${idx+2}m</span>
        </div>
      `,
      iconSize: [80, 24],
      iconAnchor: [40, 12]
    });

    const marker = L.marker([uLat, uLon], { icon: carIcon }).addTo(aerialCirclesGroup);
    
    let step = 0;
    const interval = setInterval(() => {
      step++;
      const curLat = uLat + (lat - uLat) * (step / 30);
      const curLon = uLon + (lon - uLon) * (step / 30);
      marker.setLatLng([curLat, curLon]);
      if (step >= 28) clearInterval(interval);
    }, 100);
  });

  const toast = document.createElement('div');
  toast.className = 'aerial-toast';
  toast.innerHTML = `🚓 <b>3 Delhi Police Patrol Units Dispatched to ${esc(name)}</b><br><span style="font-size:10px;opacity:0.9">500m perimeter cordon established. ETAs: 1.2m, 1.3m, 1.4m.</span>`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function copyGpsCoordinates() {
  if (!activeAerialLoc) return;
  const text = `${activeAerialLoc.lat.toFixed(6)}, ${activeAerialLoc.lon.toFixed(6)}`;
  navigator.clipboard.writeText(text).then(() => {
    const toast = document.createElement('div');
    toast.className = 'aerial-toast';
    toast.innerHTML = `📋 <b>Copied Tactical GPS:</b> ${text}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
  });
}

function applyAerialToMainMap() {
  if (!activeAerialLoc) return;
  const { lat, lon } = activeAerialLoc;
  closeLiveAerialView();
  switchToAerialAndFocus(lat, lon);
}

function switchToAerialAndFocus(lat, lon) {
  const styleSelect = document.getElementById('map-style-select');
  if (styleSelect) styleSelect.value = 'satellite';
  setMapStyle('satellite');
  if (streetMap) {
    streetMap.flyTo([lat, lon], 17, { animate: true, duration: 1.2 });
  }
}
"""

def upgrade_file(path: Path):
    if not path.exists():
        print(f"[-] Skipping non-existent: {path}")
        return
    content = path.read_text(encoding="utf-8")
    
    # 1. Add Satellite & Hybrid to tileServers if not present
    if "'satellite':" not in content and '"satellite":' not in content:
        old_tile_servers = """const tileServers = {
  osm: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: {
      maxZoom: 19,
      subdomains: ['a', 'b', 'c'],
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors · Delhi Street Network'
    }
  },
  voyager: {
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    options: {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
    }
  },
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    options: {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
    }
  }
};"""
        new_tile_servers = """const tileServers = {
  osm: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: {
      maxZoom: 19,
      subdomains: ['a', 'b', 'c'],
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors · Delhi Street Network'
    }
  },
  voyager: {
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    options: {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
    }
  },
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    options: {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
    }
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    options: {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.esri.com/" target="_blank">Esri</a>, Maxar, Earthstar Geographics · Live High-Res Aerial'
    }
  },
  hybrid: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    options: {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.esri.com/" target="_blank">Esri</a>, Maxar · Satellite + Street Network'
    }
  }
};"""
        if old_tile_servers in content:
            content = content.replace(old_tile_servers, new_tile_servers)

    # 2. Add satellite options to <select id="map-style-select">
    if '<option value="satellite">' not in content:
        content = content.replace(
            '<option value="osm" selected>🗺️ Delhi Streets (OpenStreetMap)</option>',
            '<option value="osm" selected>🗺️ Delhi Streets (OpenStreetMap)</option>\n<option value="satellite">🛰️ Live Aerial / Satellite (High-Res)</option>\n<option value="hybrid">🏙️ Hybrid (Aerial + Street Labels)</option>'
        )

    # 3. Add Aerial CSS before </style>
    if "/* 🛰️ LIVE AERIAL TACTICAL RECONNAISSANCE" not in content:
        content = content.replace("</style>", AERIAL_CSS + "\n</style>")

    # 4. Add Aerial Modal HTML before </body>
    if 'id="aerial-modal"' not in content:
        content = content.replace("</body>", AERIAL_MODAL_HTML + "\n</body>")

    # 5. Add Aerial JS before </script></body> or at bottom of script
    if "function openLiveAerialView" not in content:
        # insert right before datasetSelect.addEventListener('change'
        target_script = "datasetSelect.addEventListener('change',()=>refreshDataset());"
        if target_script in content:
            content = content.replace(target_script, AERIAL_JS + "\n" + target_script)
        else:
            content = content.replace("</script>\n</body>", AERIAL_JS + "\n</script>\n</body>")

    # 6. Update Leaflet Hotspot Marker click popup to include Live Aerial Preview & Buttons
    old_popup_start = "    const popupHtml = `\n      <div style=\"font-family:system-ui,-apple-system,sans-serif;min-width:180px\">"
    new_popup = """    const tileKey = getTileXYZ(item.lat, item.lon, 16);
    const popupHtml = `
      <div style="font-family:system-ui,-apple-system,sans-serif;min-width:240px;max-width:320px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px">
          <div style="font-weight:800;font-size:13px;color:#0f172a;line-height:1.2">${esc(item.name)}</div>
          <span style="font-size:9px;background:#0284c7;color:#fff;padding:2px 5px;border-radius:3px;font-weight:700">LIVE SATELLITE</span>
        </div>
        <div style="font-size:11px;color:#64748b;margin-bottom:6px">District: ${esc(item.district || 'Delhi')} · ${kind.toUpperCase()}</div>
        <div style="margin-bottom:6px">${riskBadge}</div>
        
        <!-- Live Aerial Satellite Preview Card -->
        <div class="aerial-thumb-card" onclick="openLiveAerialView(${item.lat}, ${item.lon}, '${esc(item.name)}', '${esc(item.district || '')}', ${score}, ${count}, '${kind}')" style="position:relative;height:100px;border-radius:6px;overflow:hidden;margin-bottom:8px;cursor:pointer;border:1px solid #0284c7;box-shadow:0 2px 8px rgba(2,132,199,0.3);background:#020617;">
          <div style="position:absolute;inset:0;background:url('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${tileKey}') center/cover no-repeat;filter:contrast(1.08);"></div>
          <div style="position:absolute;inset:0;background:radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.65) 100%);"></div>
          <div style="position:absolute;top:6px;left:6px;background:rgba(15,23,42,0.88);backdrop-filter:blur(4px);color:#38bdf8;padding:2px 6px;border-radius:4px;font-size:9px;font-weight:800;display:flex;align-items:center;gap:4px;border:1px solid rgba(56,189,248,0.4)">
            <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#ef4444;box-shadow:0 0 6px #ef4444;"></span>
            AERIAL LIVE VIEW
          </div>
          <div style="position:absolute;bottom:6px;right:6px;background:#0284c7;color:#fff;padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;box-shadow:0 2px 4px rgba(0,0,0,0.4)">
            🛰️ Click for Full Aerial HUD ↗
          </div>
          <!-- Center Tactical Crosshair -->
          <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:26px;height:26px;border:1.5px solid #ef4444;border-radius:50%;pointer-events:none;box-shadow:0 0 6px rgba(239,68,68,0.8)">
            <div style="position:absolute;top:50%;left:0;right:0;height:1px;background:#ef4444"></div>
            <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:#ef4444"></div>
          </div>
        </div>

        <div style="font-size:11px;line-height:1.45;color:#334155;background:#f8fafc;padding:6px 8px;border-radius:6px;border:1px solid #e2e8f0;margin-bottom:6px">
          <div>Incident Count: <b>${count}</b></div>
          <div>Model Risk Score: <b>${score > 0 ? score.toFixed(4) : 'N/A'}</b></div>
          <div>GPS: <b>[${item.lat.toFixed(4)}, ${item.lon.toFixed(4)}]</b></div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:6px">
          <button onclick="openLiveAerialView(${item.lat}, ${item.lon}, '${esc(item.name)}', '${esc(item.district || '')}', ${score}, ${count}, '${kind}')" style="background:#0284c7;color:#fff;border:none;padding:6px 8px;border-radius:4px;font-size:11px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:4px">
            🛰️ Full Aerial HUD
          </button>
          <button onclick="switchToAerialAndFocus(${item.lat}, ${item.lon})" style="background:#f1f5f9;color:#0f172a;border:1px solid #cbd5e1;padding:6px 8px;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer">
            🗺️ Satellite Map
          </button>
        </div>

        <div style="display:flex;justify-content:space-between;font-size:10px;color:#64748b;padding-top:4px;border-top:1px solid #f1f5f9">
          <a href="https://www.google.com/maps/@${item.lat},${item.lon},18z/data=!3m1!1e3" target="_blank" rel="noopener noreferrer" style="color:#2563eb;text-decoration:none;font-weight:600">Google Maps ↗</a>
          <a href="https://earth.google.com/web/search/${item.lat},${item.lon}" target="_blank" rel="noopener noreferrer" style="color:#0284c7;text-decoration:none;font-weight:600">Google Earth 3D ↗</a>
        </div>
      </div>
    `;"""
    
    if old_popup_start in content:
        # find end of popupHtml
        idx_start = content.find(old_popup_start)
        idx_end = content.find("circle.bindPopup(popupHtml", idx_start)
        if idx_start != -1 and idx_end != -1:
            content = content[:idx_start] + new_popup + "\n\n    " + content[idx_end:]

    # Also update circle click to auto-notify status
    old_circle_click = "circle.on('click', () => {\n      document.getElementById('map-status').textContent = `📍 Selected on Street Map: ${item.name} · District: ${item.district || 'Delhi'} · Incidents: ${count} · Score: ${score}`;\n    });"
    new_circle_click = "circle.on('click', () => {\n      document.getElementById('map-status').textContent = `🛰️ Selected Hotspot: ${item.name} · Coordinates: [${item.lat.toFixed(4)}, ${item.lon.toFixed(4)}] · Click aerial thumbnail for live satellite recon`;\n    });"
    if old_circle_click in content:
        content = content.replace(old_circle_click, new_circle_click)

    # 7. Update pinLocation popup to include Live Aerial Preview & Buttons
    pin_popup_target = "streetReticleMarker.bindPopup(`\n      <div style=\"min-width:180px\">"
    if pin_popup_target in content:
        pin_popup_new = """const tileKey = getTileXYZ(lat, lon, 16);
    streetReticleMarker.bindPopup(`
      <div style="min-width:240px;max-width:320px;font-family:system-ui,-apple-system,sans-serif">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px">
          <div style="font-weight:800;font-size:13px;color:#dc2626">📍 ${esc(name)}</div>
          <span style="font-size:9px;background:#0284c7;color:#fff;padding:2px 5px;border-radius:3px;font-weight:700">LIVE AERIAL</span>
        </div>
        <div style="font-size:11px;color:#64748b;margin-bottom:6px">District: ${esc(district || 'Delhi')}</div>
        
        <!-- Live Aerial Satellite Preview Card -->
        <div class="aerial-thumb-card" onclick="openLiveAerialView(${lat}, ${lon}, '${esc(name)}', '${esc(district || '')}', ${score || 0}, 0, 'hotspot')" style="position:relative;height:100px;border-radius:6px;overflow:hidden;margin-bottom:8px;cursor:pointer;border:1px solid #0284c7;box-shadow:0 2px 8px rgba(2,132,199,0.3);background:#020617;">
          <div style="position:absolute;inset:0;background:url('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${tileKey}') center/cover no-repeat;filter:contrast(1.08);"></div>
          <div style="position:absolute;inset:0;background:radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.65) 100%);"></div>
          <div style="position:absolute;top:6px;left:6px;background:rgba(15,23,42,0.88);backdrop-filter:blur(4px);color:#38bdf8;padding:2px 6px;border-radius:4px;font-size:9px;font-weight:800;display:flex;align-items:center;gap:4px;border:1px solid rgba(56,189,248,0.4)">
            <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#ef4444;box-shadow:0 0 6px #ef4444;"></span>
            AERIAL LIVE VIEW
          </div>
          <div style="position:absolute;bottom:6px;right:6px;background:#0284c7;color:#fff;padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;box-shadow:0 2px 4px rgba(0,0,0,0.4)">
            🛰️ Open Aerial HUD ↗
          </div>
          <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:26px;height:26px;border:1.5px solid #ef4444;border-radius:50%;pointer-events:none;box-shadow:0 0 6px rgba(239,68,68,0.8)">
            <div style="position:absolute;top:50%;left:0;right:0;height:1px;background:#ef4444"></div>
            <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:#ef4444"></div>
          </div>
        </div>

        <div style="font-size:12px;line-height:1.4;background:#f8fafc;padding:6px 8px;border-radius:6px;border:1px solid #e2e8f0;margin-bottom:6px">
          Risk Score: <b>${score !== undefined ? score : 'N/A'}</b><br>
          GPS: <b>[${lat.toFixed(4)}, ${lon.toFixed(4)}]</b>
        </div>
        
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:6px">
          <button onclick="openLiveAerialView(${lat}, ${lon}, '${esc(name)}', '${esc(district || '')}', ${score || 0}, 0, 'hotspot')" style="background:#0284c7;color:#fff;border:none;padding:6px 8px;border-radius:4px;font-size:11px;font-weight:700;cursor:pointer">
            🛰️ Full Aerial HUD
          </button>
          <button onclick="switchToAerialAndFocus(${lat}, ${lon})" style="background:#f1f5f9;color:#0f172a;border:1px solid #cbd5e1;padding:6px 8px;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer">
            🗺️ Satellite Map
          </button>
        </div>
      </div>"""
        idx_pstart = content.find(pin_popup_target)
        idx_pend = content.find("`, { className: 'oculon-popup' }).openPopup();", idx_pstart)
        if idx_pstart != -1 and idx_pend != -1:
            content = content[:idx_pstart] + pin_popup_new + "\n    " + content[idx_pend:]

    # 8. Update search result cards in query() to include Aerial button
    old_pin_div = '<div style="font-size:10px;color:#2563eb;margin-top:2px">📍 Pin on map</div>'
    new_pin_div = '<div style="display:flex;gap:4px;justify-content:flex-end;margin-top:4px"><span style="font-size:10px;color:#2563eb">📍 Pin</span><span style="font-size:10px;color:#0284c7;font-weight:700;background:#e0f2fe;padding:1px 5px;border-radius:3px" onclick="event.stopPropagation(); openLiveAerialView(${item.lon ? item.lat : 28.625}, ${item.lon ? item.lon : 77.215}, \'${esc(item.name)}\', \'${esc(item.district || \'\')}\', ${item.score || 0}, ${item.count || 0}, \'hotspot\')">🛰️ Aerial</span></div>'
    if old_pin_div in content:
        content = content.replace(old_pin_div, new_pin_div)

    # 9. Update setMapStyle to support hybrid layer with labels
    old_set_map_style = """    if (tileServers[styleKey]) {
      if (streetTileLayer) streetMap.removeLayer(streetTileLayer);
      streetTileLayer = L.tileLayer(tileServers[styleKey].url, tileServers[styleKey].options).addTo(streetMap);
      currentTileKey = styleKey;
    }"""
    new_set_map_style = """    if (tileServers[styleKey]) {
      if (streetTileLayer) streetMap.removeLayer(streetTileLayer);
      if (window.streetHybridLabelsLayer) {
        streetMap.removeLayer(window.streetHybridLabelsLayer);
        window.streetHybridLabelsLayer = null;
      }
      streetTileLayer = L.tileLayer(tileServers[styleKey].url, tileServers[styleKey].options).addTo(streetMap);
      if (styleKey === 'hybrid') {
        window.streetHybridLabelsLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png', {
          maxZoom: 19,
          subdomains: 'abcd',
          zIndex: 400
        }).addTo(streetMap);
      }
      currentTileKey = styleKey;
    }"""
    if old_set_map_style in content:
        content = content.replace(old_set_map_style, new_set_map_style)

    path.write_text(content, encoding="utf-8")
    print(f"[+] Successfully upgraded with Live Aerial View: {path}")

def main():
    print("=" * 70)
    print("🛰️ Upgrading Oculon Hotspot Maps with Live Aerial Satellite View")
    print("=" * 70)
    for p in MAP_FILES:
        upgrade_file(p)

    # Also rebuild dist_pages via build_pages_site.py
    build_script = ROOT_DIR / "scripts" / "build_pages_site.py"
    if build_script.exists():
        import subprocess
        print("[*] Rebuilding static GitHub Pages portal...")
        subprocess.run(["python3", str(build_script)], check=True)

if __name__ == "__main__":
    main()
