#!/usr/bin/env python3
"""
Convert four_dataset_hotspot_explorer.html from Delhi's political district map
to Delhi's real interactive Street Map (OpenStreetMap & CartoDB Voyager) with
an enhanced vector street road network fallback.
"""
import re
from pathlib import Path

TARGET_FILES = [
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/app/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/dist_pages/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/hf_space/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/src/oculon/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/.hf_staging/Oculon/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/.hf_staging/Oculon/dist_pages/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/.hf_staging/Oculon/src/oculon/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/hf_space/src/oculon/maps/four_dataset_hotspot_explorer.html"),
]

LEAFLET_HEAD = """<!-- Leaflet & Street Map Assets -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
"""

STREET_CSS = """
/* Delhi Street Map Styles */
#street-map {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
  background: #f1f5f9;
}
.map-wrap {
  position: relative;
  width: 100%;
  height: calc(100% - 86px);
  overflow: hidden;
  background: #f8fafc;
}
.leaflet-container {
  font-family: inherit;
  background: #f8fafc;
}
.street-label {
  font: 700 11px system-ui, -apple-system, sans-serif;
  fill: #1e293b;
  paint-order: stroke;
  stroke: #ffffff;
  stroke-width: 3px;
  stroke-linejoin: round;
  pointer-events: none;
}
.street-highway {
  stroke: #d97706 !important;
  stroke-width: 2.4 !important;
}
.road {
  fill: none;
  stroke: #64748b;
  stroke-width: 1.25;
  vector-effect: non-scaling-stroke;
}
.yamuna-river {
  fill: none;
  stroke: #38bdf8;
  stroke-width: 14;
  opacity: 0.65;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}
.delhi-ridge {
  fill: #dcfce7;
  fill-opacity: 0.7;
  stroke: #86efac;
  stroke-width: 1;
}

/* Pulsing Reticle for Street Map */
.leaflet-pulse-icon {
  background: transparent;
  border: none;
}
.pulse-ring {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 3px solid #ef4444;
  background: rgba(239, 68, 68, 0.25);
  position: absolute;
  top: -17px;
  left: -17px;
  animation: leafletPulseRing 1.8s ease-out infinite;
  pointer-events: none;
}
.pulse-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #dc2626;
  border: 2px solid #ffffff;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.4);
  position: absolute;
  top: -5px;
  left: -5px;
  pointer-events: none;
}
@keyframes leafletPulseRing {
  0% { transform: scale(0.3); opacity: 1; }
  100% { transform: scale(1.6); opacity: 0; }
}

/* Custom Street Map Popup */
.oculon-popup .leaflet-popup-content-wrapper {
  background: #ffffff;
  color: #0f172a;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  padding: 2px;
}
.oculon-popup .leaflet-popup-content {
  margin: 10px 12px;
  line-height: 1.45;
  font-size: 12px;
}
.oculon-popup .leaflet-popup-tip {
  background: #ffffff;
}
"""

STREET_LABELS_SVG = """<g id="layer-yamuna">
  <path class="yamuna-river" d="M605 105 Q 585 180 575 220 T 580 320 T 605 420 T 620 480 T 635 560 T 645 650 T 630 730" />
</g>
<g id="layer-street-labels">
  <text class="street-label" x="440" y="390" text-anchor="middle">Outer Ring Road (North)</text>
  <text class="street-label" x="510" y="440" text-anchor="middle">Ring Road (Mahatma Gandhi Marg)</text>
  <text class="street-label" x="480" y="480" text-anchor="middle">Connaught Place (CP)</text>
  <text class="street-label" x="495" y="240" text-anchor="middle">GT Karnal Road / NH 44</text>
  <text class="street-label" x="330" y="460" text-anchor="middle">Delhi-Rohtak Road</text>
  <text class="street-label" x="650" y="460" text-anchor="middle">Vikas Marg (Trans-Yamuna)</text>
  <text class="street-label" x="280" y="540" text-anchor="middle">Delhi-Jaipur Expressway / NH 48</text>
  <text class="street-label" x="590" y="580" text-anchor="middle">Mathura Road / NH 19</text>
  <text class="street-label" x="550" y="520" text-anchor="middle">Barapullah Elevated Corridor</text>
  <text class="street-label" x="490" y="610" text-anchor="middle">Mehrauli-Badarpur (MB) Road</text>
  <text class="street-label" x="340" y="600" text-anchor="middle">Najafgarh - Kapashera Corridor</text>
</g>"""

def upgrade_html_content(content: str) -> str:
    # 1. Update Title and Headers
    content = content.replace("<title>Delhi Four Dataset Hotspot Map</title>", "<title>Delhi Street Map & Spatiotemporal Predictive Hotspot Explorer</title>")
    content = content.replace("<h1>Delhi hotspot explorer</h1>", "<h1>Delhi Street Map Hotspot Explorer</h1>")
    content = content.replace("aria-label=\"Delhi election-district map with spatiotemporal hotspot overlays\"", "aria-label=\"Delhi street map with spatiotemporal hotspot overlays\"")
    content = content.replace("Delhi election-district map with spatiotemporal hotspot overlays", "Delhi street map with spatiotemporal hotspot overlays")
    
    # 2. Inject Leaflet in <head>
    if "leaflet.js" not in content:
        content = content.replace("<style>", LEAFLET_HEAD + "\n<style>")
    
    # 3. Add Street CSS
    if "/* Delhi Street Map Styles */" not in content:
        content = content.replace("</style>", STREET_CSS + "\n</style>")
        
    # 4. Remove Political District Map layers from SVG
    # Remove layer-boundaries (the colored political election districts)
    content = re.sub(r'<g id=[\x22\x27]layer-boundaries[\x22\x27]>.*?</g>', '<g id="layer-boundaries"></g>', content, flags=re.DOTALL)
    # Remove layer-district-outline
    content = re.sub(r'<g id=[\x22\x27]layer-district-outline[\x22\x27]>.*?</g>', '<g id="layer-district-outline"></g>', content, flags=re.DOTALL)
    # Replace layer-district-labels with layer-street-labels
    if '<g id="layer-street-labels">' not in content:
        content = re.sub(r'<g id=[\x22\x27]layer-district-labels[\x22\x27]>.*?</g>', STREET_LABELS_SVG, content, flags=re.DOTALL)

    # 5. Insert #street-map container inside .map-wrap if not present
    if 'id="street-map"' not in content:
        content = content.replace('<div class="map-wrap">', '<div class="map-wrap">\n<div id="street-map"></div>')
        
    # 6. Add Street Map Style Selector to map-head toolbar
    style_select_html = """<select id="map-style-select" aria-label="Choose Street Map Style" style="font-weight:600;background:#f8fafc;color:#0f172a;border-color:#94a3b8">
<option value="osm" selected>🗺️ Delhi Streets (OpenStreetMap)</option>
<option value="voyager">🏙️ CartoDB Voyager Streets</option>
<option value="dark">🌙 Dark Mode Street Patrol</option>
<option value="vector">📐 Vector Street Network</option>
</select>"""
    if 'id="map-style-select"' not in content:
        content = content.replace('<div class="layers">', style_select_html + ' <div class="layers">')

    # 7. Add Leaflet Street Map JavaScript Logic
    street_js_logic = """
// ======================================================================
// 🗺️ DELHI STREET MAP ENGINE (LEAFLET + OPENSTREETMAP + CARTO VOYAGER)
// ======================================================================
let streetMap = null;
let streetTileLayer = null;
let currentTileKey = 'osm';
let streetMarkersGroup = null;
let streetHeatLayer = null;
let streetReticleMarker = null;

const tileServers = {
  osm: {
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors · Delhi Street Network'
    }
  },
  voyager: {
    url: 'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    options: {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
    }
  },
  dark: {
    url: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    options: {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>'
    }
  }
};

function initStreetMap() {
  if (streetMap || !window.L || !document.getElementById('street-map')) return;
  try {
    streetMap = L.map('street-map', {
      center: [28.625, 77.215],
      zoom: 11,
      minZoom: 9,
      maxZoom: 18,
      zoomControl: false
    });

    L.control.zoom({ position: 'topright' }).addTo(streetMap);

    streetTileLayer = L.tileLayer(tileServers.osm.url, tileServers.osm.options).addTo(streetMap);
    streetMarkersGroup = L.layerGroup().addTo(streetMap);

    const styleSelect = document.getElementById('map-style-select');
    if (styleSelect) {
      styleSelect.addEventListener('change', (e) => setMapStyle(e.target.value));
    }
  } catch (err) {
    console.warn('Leaflet initialization warning, falling back to Vector Street Map:', err);
    streetMap = null;
  }
}

function setMapStyle(styleKey) {
  const streetMapEl = document.getElementById('street-map');
  const svgMapEl = document.getElementById('map');
  const zoomBtns = document.querySelector('.zoom');

  if (styleKey === 'vector' || !streetMap) {
    if (streetMapEl) streetMapEl.style.display = 'none';
    if (svgMapEl) svgMapEl.style.display = 'block';
    if (zoomBtns) zoomBtns.style.display = 'grid';
    view();
  } else {
    if (streetMapEl) streetMapEl.style.display = 'block';
    if (svgMapEl) svgMapEl.style.display = 'none';
    if (zoomBtns) zoomBtns.style.display = 'none';

    if (tileServers[styleKey]) {
      if (streetTileLayer) streetMap.removeLayer(streetTileLayer);
      streetTileLayer = L.tileLayer(tileServers[styleKey].url, tileServers[styleKey].options).addTo(streetMap);
      currentTileKey = styleKey;
    }
    streetMap.invalidateSize();
  }
  draw();
}

function updateLeafletHotspots(key, row) {
  if (!streetMap || !streetMarkersGroup) return;

  streetMarkersGroup.clearLayers();
  if (streetHeatLayer) {
    streetMap.removeLayer(streetHeatLayer);
    streetHeatLayer = null;
  }

  const dColor = key === 'missing_persons' ? '#3b82f6' :
                 key === 'unidentified_bodies' ? '#a855f7' :
                 key === 'missing_mobiles' ? '#f59e0b' : '#ef4444';

  const showTrain = document.querySelector('input[data-layer="train"]') ? document.querySelector('input[data-layer="train"]').checked : true;
  const showActual = document.querySelector('input[data-layer="actual"]') ? document.querySelector('input[data-layer="actual"]').checked : true;
  const showPredicted = document.querySelector('input[data-layer="predicted"]') ? document.querySelector('input[data-layer="predicted"]').checked : true;
  const showForecast = document.querySelector('input[data-layer="forecast"]') ? document.querySelector('input[data-layer="forecast"]').checked : true;
  const showHeatmap = document.getElementById('heatmap-toggle') ? document.getElementById('heatmap-toggle').checked : true;

  const heatPoints = [];

  const addLeafletPoint = (item, kind) => {
    if (!item.lat || !item.lon) return;

    const count = item.count || 0;
    const score = item.score !== undefined ? item.score : 0;

    let radius = 6;
    let fillColor = dColor;
    let strokeColor = '#ffffff';
    let fillOpacity = 0.7;
    let weight = 1.2;
    let dashArray = null;

    if (kind === 'train') {
      radius = Math.max(5, Math.min(22, 5 + Math.sqrt(count) * 2.2));
      fillOpacity = 0.55;
      heatPoints.push([item.lat, item.lon, Math.min(1.0, 0.2 + count * 0.08)]);
    } else if (kind === 'actual') {
      radius = Math.max(7, Math.min(26, 7 + Math.sqrt(count) * 2.8));
      fillColor = '#dc2626';
      fillOpacity = 0.85;
      weight = 1.6;
      heatPoints.push([item.lat, item.lon, Math.min(1.0, 0.4 + count * 0.12)]);
    } else if (kind === 'predicted') {
      radius = Math.max(8, Math.min(28, 8 + score * 80));
      fillColor = '#7c3aed';
      strokeColor = '#312e81';
      fillOpacity = 0.90;
      dashArray = '3, 2';
      weight = 1.8;
      heatPoints.push([item.lat, item.lon, Math.min(1.0, 0.3 + score * 2.5)]);
    } else if (kind === 'forecast') {
      radius = Math.max(9, Math.min(30, 9 + score * 90));
      fillColor = '#f59e0b';
      strokeColor = '#78350f';
      fillOpacity = 0.92;
      weight = 2.0;
      heatPoints.push([item.lat, item.lon, Math.min(1.0, 0.4 + score * 3.0)]);
    }

    const circle = L.circleMarker([item.lat, item.lon], {
      radius,
      fillColor,
      color: strokeColor,
      weight,
      fillOpacity,
      dashArray,
      className: `leaflet-hotspot-marker marker-${kind}`
    });

    const riskBadge = score >= 0.08 ? '<span style="background:#fee2e2;color:#dc2626;padding:2px 6px;border-radius:4px;font-weight:700">CRITICAL HOTSPOT</span>' :
                      score >= 0.03 ? '<span style="background:#fef3c7;color:#d97706;padding:2px 6px;border-radius:4px;font-weight:600">HIGH SURVEILLANCE</span>' :
                      '<span style="background:#e0e7ff;color:#4338ca;padding:2px 6px;border-radius:4px;font-weight:600">MODERATE RISK</span>';

    const popupHtml = `
      <div style="font-family:system-ui,-apple-system,sans-serif;min-width:180px">
        <div style="font-weight:700;font-size:13px;color:#0f172a">${esc(item.name)}</div>
        <div style="font-size:11px;color:#64748b;margin-bottom:6px">District: ${esc(item.district || 'Delhi')} · ${kind.toUpperCase()}</div>
        <div style="margin-bottom:6px">${riskBadge}</div>
        <hr style="margin:6px 0;border:0;border-top:1px solid #e2e8f0">
        <div style="font-size:12px;line-height:1.4">
          <div>Incident Count: <b>${count}</b></div>
          <div>Model Risk Score: <b>${score > 0 ? score.toFixed(4) : 'N/A'}</b></div>
          <div>GPS: <b>[${item.lat.toFixed(4)}, ${item.lon.toFixed(4)}]</b></div>
        </div>
        <div style="margin-top:6px;font-size:11px;color:#2563eb;background:#eff6ff;padding:4px 6px;border-radius:4px">
          👮 <b>SHO Action</b>: Deploy mobile street patrol in 500m radius
        </div>
      </div>
    `;

    circle.bindPopup(popupHtml, { className: 'oculon-popup' });
    circle.bindTooltip(`${esc(item.name)} (${count > 0 ? count + ' incidents' : 'Score: ' + score})`, {
      direction: 'top',
      offset: [0, -radius]
    });

    circle.on('click', () => {
      document.getElementById('map-status').textContent = `📍 Selected on Street Map: ${item.name} · District: ${item.district || 'Delhi'} · Incidents: ${count} · Score: ${score}`;
    });

    streetMarkersGroup.addLayer(circle);
  };

  if (showTrain && row.train) row.train.forEach(p => addLeafletPoint(p, 'train'));
  if (showActual && row.actual) row.actual.forEach(p => addLeafletPoint(p, 'actual'));
  if (showPredicted && row.predicted) row.predicted.forEach(p => addLeafletPoint(p, 'predicted'));
  if (showForecast && row.forecast) row.forecast.forEach(p => addLeafletPoint(p, 'forecast'));

  // Leaflet Heatmap Layer
  if (showHeatmap && window.L && L.heatLayer && heatPoints.length > 0) {
    const heatGradients = {
      missing_persons: { 0.2: '#93c5fd', 0.5: '#3b82f6', 0.8: '#1d4ed8', 1.0: '#172554' },
      unidentified_bodies: { 0.2: '#e9d5ff', 0.5: '#c084fc', 0.8: '#9333ea', 1.0: '#581c87' },
      missing_mobiles: { 0.2: '#fde68a', 0.5: '#fbbf24', 0.8: '#d97706', 1.0: '#78350f' },
      stolen_vehicles: { 0.2: '#fecaca', 0.5: '#f87171', 0.8: '#dc2626', 1.0: '#7f1d1d' }
    };

    streetHeatLayer = L.heatLayer(heatPoints, {
      radius: 26,
      blur: 18,
      maxZoom: 15,
      gradient: heatGradients[key] || heatGradients.stolen_vehicles
    }).addTo(streetMap);
  }
}
"""

    if "function initStreetMap()" not in content:
        # Insert initStreetMap before function draw()
        content = content.replace("function draw() {", street_js_logic + "\nfunction draw() {")

    # Hook initStreetMap() at document load
    if "initStreetMap();" not in content:
        content = content.replace("draw();\nquery();", "initStreetMap();\ndraw();\nquery();")
        
    # Hook updateLeafletHotspots into draw()
    if "updateLeafletHotspots(key, v);" not in content:
        content = content.replace("currentData = { key, month, row: v };", "currentData = { key, month, row: v };\n  updateLeafletHotspots(key, v);")

    # Update pinLocation to fly on Leaflet Street Map
    old_pin_loc = """function pinLocation(lon, lat, name, district, score) {"""
    new_pin_loc = """function pinLocation(lon, lat, name, district, score) {
  // --- Leaflet Street Map Centering ---
  if (streetMap && document.getElementById('street-map').style.display !== 'none') {
    streetMap.flyTo([lat, lon], 15, { animate: true, duration: 1.1 });

    if (streetReticleMarker) {
      streetMap.removeLayer(streetReticleMarker);
      streetReticleMarker = null;
    }

    const pulseIcon = L.divIcon({
      className: 'leaflet-pulse-icon',
      html: '<div style="position:relative;"><div class="pulse-ring"></div><div class="pulse-dot"></div></div>',
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    streetReticleMarker = L.marker([lat, lon], { icon: pulseIcon }).addTo(streetMap);
    streetReticleMarker.bindPopup(`
      <div style="min-width:180px">
        <div style="font-weight:700;font-size:13px;color:#dc2626">📍 ${esc(name)}</div>
        <div style="font-size:11px;color:#64748b;margin-bottom:5px">District: ${esc(district || 'Delhi')}</div>
        <div style="font-size:12px;line-height:1.4">
          Risk Score: <b>${score !== undefined ? score : 'N/A'}</b><br>
          GPS: [${lat.toFixed(4)}, ${lon.toFixed(4)}]
        </div>
        <div style="margin-top:6px;font-size:11px;color:#16a34a;background:#f0fdf4;padding:3px 6px;border-radius:4px">
          🚦 Centered on Delhi Street Map
        </div>
      </div>
    `, { className: 'oculon-popup' }).openPopup();

    document.getElementById('map-status').textContent = `📍 Focused on Street Map: ${name} · ${district ? district + ' · ' : ''}Score: ${score || 'N/A'} · Coordinates: [${lat.toFixed(4)}, ${lon.toFixed(4)}]`;
    return;
  }
"""
    if "if (streetMap && document.getElementById('street-map').style.display !== 'none')" not in content:
        content = content.replace(old_pin_loc, new_pin_loc)

    return content


def main():
    print("🚀 Starting conversion to Delhi Street Map across all targets...")
    for target in TARGET_FILES:
        if not target.exists():
            print(f"Skipping {target} (not found)")
            continue
        print(f"Upgrading {target} ...")
        raw = target.read_text(encoding="utf-8")
        upgraded = upgrade_html_content(raw)
        target.write_text(upgraded, encoding="utf-8")
        print(f"✅ Successfully upgraded {target} ({len(upgraded):,} bytes)")

if __name__ == "__main__":
    main()
