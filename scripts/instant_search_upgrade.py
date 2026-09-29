#!/usr/bin/env python3
"""
Fast, Instant In-Memory Spatial Search & Removal of 'Fetch API' Toggle.
Addresses user request:
- Remove the toggle/button of 'Fetch API'
- Fix search being too slow or stuck on 'Searching & fetching hotspots...'
- Provide instant 0ms in-memory spatial lookup for any Delhi location (e.g. Rajiv Chowk, Kashmere Gate, Metro Stations, Districts)
"""

from pathlib import Path
import re

TARGET_FILES = [
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/.hf_staging/Oculon/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/.hf_staging/Oculon/src/oculon/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/hf_space/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/src/delhi_hotspots/maps/four_dataset_hotspot_explorer.html"),
]

NEW_QUERY_CARD = """<aside class="query-card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <h2 style="margin:0;font-size:15px">Top Hotspots & Search</h2>
    <span class="live-pill" id="api-status-pill"><span class="dot-live"></span> Instant Spatial Index</span>
  </div>
  <div class="small">Instant search any Delhi metro station, district, police jurisdiction, or place name:</div>
  <div class="query-tools" style="margin-top:8px">
    <input id="query" aria-label="Location search" placeholder="e.g. Rajiv Chowk, Kashmere Gate, Central, Rohini..." />
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
      <option value="all">All Locations</option>
    </select>
  </div>
  <div class="unlocated" id="mobile-note" style="display:none"></div>
  <div id="results" class="results" aria-live="polite"></div>
</aside>"""

NEW_QUERY_JS = """function query() {
  const qInput = document.getElementById('query');
  const q = (qInput ? qInput.value : '').trim();
  const qLower = q.toLowerCase();
  const distFilter = (document.getElementById('district-filter') ? document.getElementById('district-filter').value : '').trim().toLowerCase();
  const limitVal = document.getElementById('limit-filter') ? document.getElementById('limit-filter').value : '7';
  const limit = limitVal === 'all' ? 1000 : parseInt(limitVal, 10);
  const box = document.getElementById('results');
  if (!box) return;

  const key = datasetSelect.value;
  const d = D.datasets[key];
  const target = d.forecast_month || months[months.length - 1];
  const row = d.months ? d.months[target] : null;
  const v = methodData(row, key);

  // 1. Build a master deduplicated spatial dictionary of Delhi locations
  const locMap = new Map();

  // Seed with canonical reference points for this dataset (e.g. police stations or corridors)
  if (d.reference_points) {
    for (const p of d.reference_points) {
      if (!p.name) continue;
      locMap.set(p.name.toLowerCase(), {
        name: p.name,
        district: p.district || '',
        lon: p.lon,
        lat: p.lat,
        score: 0.05,
        count: 0,
        isForecast: false
      });
    }
  }

  // Cross-reference Delhi Metro stations from stolen_vehicles or missing_mobiles so transit searches always work
  for (const dsKey of ['stolen_vehicles', 'missing_mobiles', 'missing_persons']) {
    const refList = D.datasets[dsKey] ? D.datasets[dsKey].reference_points : null;
    if (refList) {
      for (const p of refList) {
        if (!p.name) continue;
        const lk = p.name.toLowerCase();
        if (!locMap.has(lk)) {
          locMap.set(lk, {
            name: p.name,
            district: p.district || '',
            lon: p.lon,
            lat: p.lat,
            score: 0.04,
            count: 0,
            isForecast: false
          });
        }
      }
    }
  }

  // Aggregate observed counts across historical timeline
  if (d.months) {
    for (const m in d.months) {
      const mRow = methodData(d.months[m], key);
      if (!mRow) continue;
      const combined = (mRow.train || []).concat(mRow.actual || []);
      for (const item of combined) {
        if (!item.name) continue;
        const lk = item.name.toLowerCase();
        let rec = locMap.get(lk);
        if (!rec) {
          rec = {
            name: item.name,
            district: item.district || '',
            lon: item.lon,
            lat: item.lat,
            score: 0.05,
            count: 0,
            isForecast: false
          };
          locMap.set(lk, rec);
        }
        rec.count = (rec.count || 0) + (item.count || 1);
        if (item.lon && !rec.lon) rec.lon = item.lon;
        if (item.lat && !rec.lat) rec.lat = item.lat;
        if (item.district && !rec.district) rec.district = item.district;
      }
    }
  }

  // Overlay current month forecast/predicted hotspots
  let targetHotspots = [];
  if (v) {
    targetHotspots = (v.forecast && v.forecast.length ? v.forecast : (v.predicted && v.predicted.length ? v.predicted : (v.actual || []))).slice();
    for (const item of targetHotspots) {
      if (!item.name) continue;
      const lk = item.name.toLowerCase();
      let rec = locMap.get(lk);
      if (!rec) {
        rec = {
          name: item.name,
          district: item.district || '',
          lon: item.lon,
          lat: item.lat,
          score: item.score || 0.1,
          count: item.count || 0,
          isForecast: true
        };
        locMap.set(lk, rec);
      } else {
        if (item.score !== undefined) rec.score = item.score;
        rec.isForecast = true;
      }
    }
  }

  // Determine items to display
  let items = [];
  if (!q && !distFilter) {
    // Default view: top forecast/predicted hotspots for target month
    items = targetHotspots.slice();
    if (!items.length) {
      items = Array.from(locMap.values());
    }
    items.sort((a, b) => (b.score || 0) - (a.score || 0));
  } else {
    // User search query or district filter: comprehensive instant search across all locations
    const all = Array.from(locMap.values());
    items = all.filter(item => {
      const name = (item.name || '').toLowerCase();
      const dist = (item.district || '').toLowerCase();
      const matchQ = !qLower || name.includes(qLower) || dist.includes(qLower);
      const matchD = !distFilter || dist.includes(distFilter);
      return matchQ && matchD;
    });

    items.sort((a, b) => {
      if (a.isForecast !== b.isForecast) return a.isForecast ? -1 : 1;
      return (b.score || 0) - (a.score || 0) || (b.count || 0) - (a.count || 0);
    });
  }

  items = items.slice(0, limit);

  if (!items.length) {
    box.innerHTML = `<div class="unlocated">No hotspots found matching "${esc(q || distFilter)}". Try searching for another station (e.g. "Rajiv Chowk", "Kashmere Gate", "Rohini") or select a district.</div>`;
    return;
  }

  const heading = q 
    ? `Matches for "${esc(q)}" · ${items.length} locations` 
    : (distFilter ? `${distFilter.toUpperCase()} District · ${items.length} locations` : `${d.label} · ${target} · Top ${items.length} hotspots`);

  let html = `<div style="font-weight:600;font-size:12px;margin-bottom:8px;color:${d.color}">${heading}</div>`;

  items.forEach((item, idx) => {
    const scoreVal = item.score !== undefined ? Number(item.score).toFixed(4) : '0.0500';
    const riskClass = (item.isForecast || idx < 3) ? (idx < 3 ? 'risk-crit' : (idx < 7 ? 'risk-high' : 'risk-mod')) : 'risk-mod';
    const riskLabel = (item.isForecast || idx < 3) ? (idx < 3 ? 'CRITICAL' : 'ELEVATED') : 'MONITORED';

    html += `
    <div class="result-card" onclick="pinLocation(${item.lon}, ${item.lat}, '${esc(item.name)}', '${esc(item.district || '')}', '${scoreVal}')">
      <div class="card-left">
        <span style="font-weight:700;color:#64748b;font-size:12px;width:18px">#${idx + 1}</span>
        <div>
          <div style="font-weight:600;font-size:12px;color:#0f172a">${esc(item.name)}</div>
          <div style="margin-top:2px">
            ${item.district ? `<span class="badge-district">${esc(item.district)}</span>` : ''}
            <span class="badge-risk ${riskClass}">${riskLabel}</span>
            ${item.count ? `<span style="font-size:10px;color:#64748b;margin-left:4px">${item.count} events</span>` : ''}
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

datasetSelect.addEventListener('change',()=>refreshDataset());
slider.addEventListener('input',draw);
monthSelect.addEventListener('change',()=>{slider.value=monthSelect.value;draw()});
document.getElementById('prev').onclick=()=>{slider.value=Math.max(0,+slider.value-1);draw()};
document.getElementById('next').onclick=()=>{slider.value=Math.min(months.length-1,+slider.value+1);draw()};
methodSelect.addEventListener('change',()=>{draw();if(document.getElementById('results').textContent)query()});
document.getElementById('run-query').onclick=query;

// Real-time instantaneous search as user types
const qInput = document.getElementById('query');
qInput.addEventListener('input', query);
qInput.addEventListener('keydown', e => { if (e.key === 'Enter') query(); });

document.getElementById('police-toggle').addEventListener('change',e=>{const g=document.getElementById('layer-police');g.style.display=e.target.checked?'':'none';if(e.target.checked){const refs=D.datasets[datasetSelect.value].reference_points||[];for(const p of refs)addPoint(g,p,datasetSelect.value,'police')}});
document.querySelectorAll('[data-layer]').forEach(c=>c.addEventListener('change',()=>{const g=document.getElementById('layer-'+c.dataset.layer);g.style.display=c.checked?'':'none'}));
function view(){scene.setAttribute('transform',`translate(${tx} ${ty}) translate(440 410) scale(${zoom}) translate(-440 -410)`)}
document.getElementById('zin').onclick=()=>{zoom=Math.min(8,zoom*1.25);view()};
document.getElementById('zout').onclick=()=>{zoom=Math.max(1,zoom/1.25);view()};
svg.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(1,Math.min(8,zoom*(e.deltaY<0?1.1:.9)));view()},{passive:false});
svg.addEventListener('pointerdown',e=>{if(e.target.closest('circle,path,rect,image'))return;drag=[e.clientX,e.clientY,tx,ty];svg.setPointerCapture(e.pointerId)});
svg.addEventListener('pointermove',e=>{if(!drag)return;const r=svg.getBoundingClientRect(),f=820/Math.min(r.width,r.height);tx=drag[2]+(e.clientX-drag[0])*f;ty=drag[3]+(e.clientY-drag[1])*f;view()});
svg.addEventListener('pointerup',()=>drag=null);

document.getElementById('heatmap-toggle').addEventListener('change', draw);
if (document.getElementById('district-filter')) document.getElementById('district-filter').addEventListener('change', query);
if (document.getElementById('limit-filter')) document.getElementById('limit-filter').addEventListener('change', query);

refreshDataset();query();
</script></body></html>"""

def update_file(path: Path):
    if not path.exists():
        print(f"Skipping non-existent: {path}")
        return
    text = path.read_text(encoding="utf-8")
    
    # 1. Replace <aside class="query-card"> ... </aside>
    query_card_pattern = re.compile(r'<aside class="query-card">.*?</aside>', re.DOTALL)
    if not query_card_pattern.search(text):
        print(f"Error: query-card not found in {path}")
        return
    text = query_card_pattern.sub(NEW_QUERY_CARD, text, count=1)
    
    # 2. Replace from async function query() to </script></body></html>
    query_js_pattern = re.compile(r'async function query\(\)\s*\{.*?</script></body></html>', re.DOTALL)
    if not query_js_pattern.search(text):
        # maybe function query() without async
        query_js_pattern = re.compile(r'function query\(\)\s*\{.*?</script></body></html>', re.DOTALL)
        if not query_js_pattern.search(text):
            print(f"Error: query() function not found in {path}")
            return
            
    text = query_js_pattern.sub(NEW_QUERY_JS, text, count=1)
    
    path.write_text(text, encoding="utf-8")
    print(f"[+] Successfully upgraded {path} ({path.stat().st_size / 1024:.1f} KB)")

def main():
    print("--> Upgrading map explorer to instant in-memory search and removing fetch api toggle...")
    for f in TARGET_FILES:
        update_file(f)

if __name__ == "__main__":
    main()
