#!/usr/bin/env python3
"""
Complete upgrade for four_dataset_hotspot_explorer.html:
- Full SVG Heatmap rendering across all 4 datasets (Missing Persons, Unidentified Bodies, Missing Mobiles, Stolen Vehicles).
- Dynamic location search by place name, metro station, district, or police jurisdiction.
- Live API integration with Hugging Face Space with fallback to local spatial index.
- Click-to-locate reticle centering and zooming on the map.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "hf_space" / "maps" / "four_dataset_hotspot_explorer.html"

UPGRADED_CSS = """
/* Upgraded Dynamic Heatmap & Location Search Styles */
.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  color: #334155;
}
.dot-live {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 6px #10b981;
  animation: pulseDot 2s infinite;
}
@keyframes pulseDot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(1.25); }
}
.target-pulse {
  animation: reticlePulse 1.8s ease-out infinite;
  transform-origin: center;
}
@keyframes reticlePulse {
  0% { r: 6px; opacity: 1; stroke-width: 2.5px; }
  100% { r: 38px; opacity: 0; stroke-width: 1px; }
}
.result-card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  background: #fff;
  cursor: pointer;
  transition: all 0.18s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.result-card:hover {
  border-color: #3b82f6;
  background: #f8fafc;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
  transform: translateY(-1px);
}
.result-card.active-pin {
  border-color: #ef4444;
  background: #fef2f2;
}
.card-left {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
}
.badge-district {
  display: inline-block;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
}
.badge-risk {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}
.risk-crit { background: #fee2e2; color: #dc2626; }
.risk-high { background: #fef3c7; color: #d97706; }
.risk-mod  { background: #e0e7ff; color: #4338ca; }
"""

UPGRADED_SIDEBAR_HTML = """<aside class="query-card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <h2 style="margin:0;font-size:15px">Top Hotspots & Search</h2>
    <span class="live-pill" id="api-status-pill"><span class="dot-live"></span> Live API Ready</span>
  </div>
  <div class="small">Search any Delhi metro station, district, police jurisdiction, or place name:</div>
  <div class="query-tools" style="margin-top:8px">
    <input id="query" aria-label="Location search" placeholder="e.g. Kashmere Gate, Wazirabad, North District, Rohini..." />
    <button class="primary" id="run-query">Search</button>
  </div>
  <div class="filter-row" style="display:flex;gap:5px;margin-top:6px;flex-wrap:wrap">
    <select id="district-filter" aria-label="District Filter" style="flex:1;font-size:11px">
      <option value="">All 11 Districts</option>
      <option value="North">North</option>
      <option value="North West">North West</option>
      <option value="North East">North East</option>
      <option value="Central">Central</option>
      <option value="New Delhi">New Delhi</option>
      <option value="East">East</option>
      <option value="West">West</option>
      <option value="South">South</option>
      <option value="South West">South West</option>
      <option value="South East">South East</option>
      <option value="Shahdara">Shahdara</option>
    </select>
    <select id="limit-filter" aria-label="Results Limit" style="font-size:11px">
      <option value="7">Top 7</option>
      <option value="15">Top 15</option>
      <option value="30">Top 30</option>
      <option value="all">All Units</option>
    </select>
    <button id="fetch-live-btn" style="font-size:11px;background:#0f172a;color:#fff;border-color:#334155" title="Fetch live dynamic model forecast via API">⚡ Fetch API</button>
  </div>
  <div class="unlocated" id="mobile-note" style="display:none"></div>
  <div id="results" class="results" aria-live="polite"></div>
</aside>"""

UPGRADED_JS_ENGINE = """
// --- UPGRADED HEATMAP & LOCATION SEARCH ENGINE ---
let activePinnedMarker = null;

function drawHeatmap(group, key, items, isHotspot) {
  if (!document.getElementById('heatmap-toggle') || !document.getElementById('heatmap-toggle').checked) return;
  for (const item of items || []) {
    if (!item.lon || !item.lat) continue;
    const [x, y] = project(item.lon, item.lat);
    const circle = document.createElementNS(NS, 'circle');
    circle.setAttribute('cx', x);
    circle.setAttribute('cy', y);
    let r = isHotspot 
      ? Math.max(26, Math.min(72, 24 + (item.score || 0.05) * 220))
      : Math.max(16, Math.min(50, 14 + Math.sqrt(item.count || 1) * 4.2));
    circle.setAttribute('r', r);
    circle.setAttribute('fill', `url(#grad-heat-${key})`);
    circle.setAttribute('opacity', isHotspot ? '0.80' : '0.62');
    circle.setAttribute('style', 'pointer-events: none;');
    group.appendChild(circle);
  }
}

function pinLocation(lon, lat, name, district, score) {
  const [x, y] = project(lon, lat);
  
  // Smoothly center the map view
  tx = 440 - x;
  ty = 410 - y;
  zoom = Math.max(zoom, 2.5);
  view();
  
  // Clear and draw reticle
  clear('layer-reticle');
  const retGroup = document.getElementById('layer-reticle');
  
  // Outer pulsing circle
  const pulse = document.createElementNS(NS, 'circle');
  pulse.setAttribute('cx', x);
  pulse.setAttribute('cy', y);
  pulse.setAttribute('class', 'target-pulse');
  pulse.setAttribute('stroke', '#ef4444');
  pulse.setAttribute('fill', 'rgba(239,68,68,0.25)');
  retGroup.appendChild(pulse);
  
  // Inner center dot
  const dot = document.createElementNS(NS, 'circle');
  dot.setAttribute('cx', x);
  dot.setAttribute('cy', y);
  dot.setAttribute('r', 5);
  dot.setAttribute('fill', '#ef4444');
  dot.setAttribute('stroke', '#ffffff');
  dot.setAttribute('stroke-width', 2);
  retGroup.appendChild(dot);
  
  // Floating text label
  const txt = document.createElementNS(NS, 'text');
  txt.setAttribute('x', x);
  txt.setAttribute('y', y - 14);
  txt.setAttribute('text-anchor', 'middle');
  txt.setAttribute('class', 'district-label');
  txt.setAttribute('style', 'font-size:12px;font-weight:700;fill:#dc2626;stroke:#fff;stroke-width:3px;');
  txt.textContent = `${name} (${district || 'Delhi'})`;
  retGroup.appendChild(txt);
  
  document.getElementById('map-status').textContent = `📍 Focused on: ${name} · ${district ? district + ' · ' : ''}Score: ${score || 'N/A'} · Coordinates: [${lat.toFixed(4)}, ${lon.toFixed(4)}]`;
}

function draw() {
  const key = datasetSelect.value, d = D.datasets[key], month = months[Number(slider.value) || 0];
  monthSelect.value = slider.value;
  document.getElementById('month-label').textContent = month || '';
  
  for (const layer of ['heatmap', 'train', 'actual', 'predicted', 'forecast', 'police']) {
    clear('layer-' + layer);
  }
  
  const raw = d.months ? d.months[month] : null, v = methodData(raw, key);
  if (!v) {
    document.getElementById('metrics').textContent = `${d.label} · ${month} · no model data for this month.`;
    return;
  }
  
  currentData = { key, month, row: v };
  document.getElementById('metrics').textContent = `${d.label} · ${month} · ${v.split === 'forecast' ? 'forecast' : 'train ' + (v.train_events || 0).toLocaleString() + ' / test ' + (v.test_events || 0).toLocaleString()} · ${v.hotspot_note || ''} · ${d.unit}`;
  
  // Render Heatmap Layer First (Soft density glow)
  const heatGroup = document.getElementById('layer-heatmap');
  if (heatGroup) {
    drawHeatmap(heatGroup, key, v.train, false);
    drawHeatmap(heatGroup, key, v.actual, false);
    drawHeatmap(heatGroup, key, v.predicted, true);
    drawHeatmap(heatGroup, key, v.forecast, true);
  }
  
  // Render Discrete Point Markers on Top
  for (const item of v.train || []) addPoint(document.getElementById('layer-train'), item, key, 'train');
  for (const item of v.actual || []) addPoint(document.getElementById('layer-actual'), item, key, 'actual');
  for (const item of v.predicted || []) addPoint(document.getElementById('layer-predicted'), item, key, 'predicted');
  for (const item of v.forecast || []) addPoint(document.getElementById('layer-forecast'), item, key, 'forecast');
  
  document.getElementById('map-status').textContent = '🔥 Density Heatmap & Hotspots rendered. Click any marker or list result to center and inspect.';
  document.getElementById('prev').disabled = Number(slider.value) === 0;
  document.getElementById('next').disabled = Number(slider.value) === months.length - 1;
}

async function query() {
  const q = document.getElementById('query').value.trim();
  const distFilter = (document.getElementById('district-filter') ? document.getElementById('district-filter').value : '').trim().toLowerCase();
  const limitVal = document.getElementById('limit-filter') ? document.getElementById('limit-filter').value : '7';
  const limit = limitVal === 'all' ? 1000 : parseInt(limitVal, 10);
  const box = document.getElementById('results');
  const pill = document.getElementById('api-status-pill');
  
  box.innerHTML = '<div style="padding:12px;text-align:center;color:#64748b"><span class="dot-live"></span> Searching & fetching hotspots...</div>';
  
  const key = datasetSelect.value;
  const d = D.datasets[key];
  const target = d.forecast_month || months[months.length - 1];
  
  let cloudItems = null;
  // Try Live Cloud API request first
  try {
    const apiUrl = `https://abhyudaymishr-oculon.hf.space/api/hotspots?dataset=${key}&month=${target}&top_k=${limitVal}&query=${encodeURIComponent(q)}`;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2500);
    const resp = await fetch(apiUrl, { signal: ctrl.signal });
    clearTimeout(timer);
    if (resp.ok) {
      const data = await resp.json();
      if (data && data.hotspots && data.hotspots.length > 0) {
        cloudItems = data.hotspots.map(h => ({
          name: h.name || h.station || h.location || 'Location',
          district: h.district || '',
          lon: h.lon || h.longitude,
          lat: h.lat || h.latitude,
          score: h.score !== undefined ? h.score : h.relative_model_score
        }));
        if (pill) pill.innerHTML = '<span class="dot-live"></span> Live API Connected (ZeroGPU)';
      }
    }
  } catch (err) {
    if (pill) pill.innerHTML = '<span class="dot-live" style="background:#3b82f6;box-shadow:0 0 6px #3b82f6"></span> Local Spatial Index (High-Speed)';
  }
  
  // Fallback to local comprehensive store if cloud API was unavailable
  let items = cloudItems;
  if (!items) {
    const row = d.months ? d.months[target] : null;
    const v = methodData(row, key);
    let pool = [];
    if (v) {
      pool = (v.forecast && v.forecast.length ? v.forecast : (v.predicted && v.predicted.length ? v.predicted : (v.actual || []))).slice();
    }
    if (!pool.length && d.reference_points) {
      pool = d.reference_points.map(p => ({ ...p, score: 0.05 }));
    }
    
    // Apply text search & district filter
    items = pool.filter(item => {
      const name = (item.name || '').toLowerCase();
      const dist = (item.district || '').toLowerCase();
      const matchQ = !q || name.includes(q.toLowerCase()) || dist.includes(q.toLowerCase());
      const matchD = !distFilter || dist.includes(distFilter);
      return matchQ && matchD;
    });
    
    items.sort((a, b) => (b.score || b.count || 0) - (a.score || a.count || 0));
    items = items.slice(0, limit);
  }
  
  if (!items || !items.length) {
    box.innerHTML = `<div class="unlocated">No hotspots found matching "${esc(q || distFilter)}". Try searching for another district (e.g. "North") or station name.</div>`;
    return;
  }
  
  const heading = `${d.label} · ${target} · ${items.length} hotspots`;
  let html = `<div style="font-weight:600;font-size:12px;margin-bottom:8px;color:${d.color}">${heading}</div>`;
  
  items.forEach((item, idx) => {
    const scoreVal = item.score !== undefined ? Number(item.score).toFixed(4) : (item.count || 'N/A');
    const riskClass = idx < 3 ? 'risk-crit' : (idx < 7 ? 'risk-high' : 'risk-mod');
    const riskLabel = idx < 3 ? 'CRITICAL' : (idx < 7 ? 'ELEVATED' : 'MODERATE');
    
    html += `
    <div class="result-card" onclick="pinLocation(${item.lon}, ${item.lat}, '${esc(item.name)}', '${esc(item.district)}', '${scoreVal}')">
      <div class="card-left">
        <span style="font-weight:700;color:#64748b;font-size:12px;width:18px">#${idx + 1}</span>
        <div>
          <div style="font-weight:600;font-size:12px;color:#0f172a">${esc(item.name)}</div>
          <div style="margin-top:2px">
            ${item.district ? `<span class="badge-district">${esc(item.district)}</span>` : ''}
            <span class="badge-risk ${riskClass}">${riskLabel}</span>
          </div>
        </div>
      </div>
      <div style="text-align:right">
        <div style="font-weight:700;font-size:12px;color:#1e293b;font-variant-numeric:tabular-nums">${scoreVal}</div>
        <div style="font-size:10px;color:#2563eb;margin-top:2px">📍 Pin on map</div>
      </div>
    </div>`;
  });
  
  box.innerHTML = html;
}
"""

def main():
    print(f"--> Reading {MAP_FILE}...")
    content = MAP_FILE.read_text(encoding="utf-8")
    
    # 1. Inject UPGRADED_CSS before </style>
    if '.result-card' not in content:
        content = content.replace('</style>', f'{UPGRADED_CSS}\n</style>')
        print("    [+] Injected upgraded CSS styles.")
        
    # 2. Add Heatmap Layer checkbox into toolbar if not present
    if 'id="heatmap-toggle"' not in content:
        content = content.replace(
            '<label><input type="checkbox" data-layer="train" checked>',
            '<label style="font-weight:600;color:#c026d3"><input type="checkbox" id="heatmap-toggle" checked> 🔥 Density Heatmap</label> <label><input type="checkbox" data-layer="train" checked>'
        )
        print("    [+] Added Heatmap toggle checkbox.")
        
    # 3. Replace <aside class="query-card">...</aside>
    aside_start = content.find('<aside class="query-card">')
    aside_end = content.find('</aside>', aside_start) + len('</aside>')
    if aside_start != -1 and aside_end != -1:
        content = content[:aside_start] + UPGRADED_SIDEBAR_HTML + content[aside_end:]
        print("    [+] Upgraded Sidebar query card.")
        
    # 4. Replace draw() and query() functions in JS
    js_marker = "function draw(){"
    js_start = content.find(js_marker)
    if js_start != -1:
        # Find where query() finishes before refreshDataset()
        query_finish_marker = "datasetSelect.addEventListener('change'"
        js_end = content.find(query_finish_marker, js_start)
        if js_end != -1:
            content = content[:js_start] + UPGRADED_JS_ENGINE + "\n" + content[js_end:]
            print("    [+] Upgraded draw() and query() JavaScript engine with live fetching & reticle pin.")
            
    # 5. Add event listener for heatmap toggle and live button
    init_marker = "refreshDataset();query();"
    if 'document.getElementById("heatmap-toggle")' not in content:
        listeners = """
document.getElementById('heatmap-toggle').addEventListener('change', draw);
if (document.getElementById('district-filter')) document.getElementById('district-filter').addEventListener('change', query);
if (document.getElementById('limit-filter')) document.getElementById('limit-filter').addEventListener('change', query);
if (document.getElementById('fetch-live-btn')) document.getElementById('fetch-live-btn').addEventListener('click', query);
"""
        content = content.replace(init_marker, f"{listeners}\n{init_marker}")
        print("    [+] Added interactive event listeners for heatmap and filters.")
        
    MAP_FILE.write_text(content, encoding="utf-8")
    print(f"--> Saved upgraded map to {MAP_FILE} ({MAP_FILE.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    main()
