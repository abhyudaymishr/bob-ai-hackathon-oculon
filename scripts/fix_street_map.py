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

for target in TARGET_FILES:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")
    
    # 1. Fix CSS of #street-map: start with display:none so it never blocks the vector street map with an opaque blank div
    content = re.sub(
        r'#street-map\s*\{[^}]*\}',
        """#street-map {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
  display: none;
  background: transparent;
}""",
        content
    )
    
    # 2. Make sure SVG #map is visible by default (display: block)
    content = re.sub(
        r'<svg id="map"([^>]*)style="[^"]*"',
        r'<svg id="map"\1style="width:100%;height:100%;display:block;"',
        content
    )
    if '<svg id="map"' in content and 'style=' not in content[content.find('<svg id="map"'):content.find('<svg id="map"')+80]:
        content = content.replace('<svg id="map"', '<svg id="map" style="width:100%;height:100%;display:block;"')

    # 3. Ensure initStreetMap is called at startup and on window load
    # Check line 1080: refreshDataset();query();
    if "initStreetMap();" not in content:
        content = content.replace("refreshDataset();query();", "refreshDataset();query();\ninitStreetMap();\nwindow.addEventListener('load', () => { initStreetMap(); });")
        
    # 4. Enhance setMapStyle to properly toggle display
    # When streetMap is ready, show #street-map, hide #map
    # When vector, show #map, hide #street-map
    content = re.sub(
        r'function setMapStyle\(styleKey\)\s*\{[\s\S]*?draw\(\);\s*\}',
        """function setMapStyle(styleKey) {
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
    setTimeout(() => { streetMap.invalidateSize(); }, 50);
  }
  draw();
}""",
        content
    )

    # 5. In initStreetMap, if successful and styleKey !== 'vector', activate street-map
    content = re.sub(
        r'function initStreetMap\(\)\s*\{[\s\S]*?streetMap\s*=\s*null;\s*\}\s*\}',
        """function initStreetMap() {
  if (streetMap || !window.L || !document.getElementById('street-map')) return;
  try {
    const mapEl = document.getElementById('street-map');
    const svgEl = document.getElementById('map');
    const zoomBtns = document.querySelector('.zoom');
    const styleSelect = document.getElementById('map-style-select');
    const chosenStyle = styleSelect ? styleSelect.value : 'osm';

    streetMap = L.map('street-map', {
      center: [28.625, 77.215],
      zoom: 11,
      minZoom: 9,
      maxZoom: 18,
      zoomControl: false
    });

    L.control.zoom({ position: 'topright' }).addTo(streetMap);
    streetTileLayer = L.tileLayer(tileServers[chosenStyle === 'vector' ? 'osm' : chosenStyle].url, tileServers[chosenStyle === 'vector' ? 'osm' : chosenStyle].options).addTo(streetMap);
    streetMarkersGroup = L.layerGroup().addTo(streetMap);

    if (chosenStyle !== 'vector') {
      mapEl.style.display = 'block';
      if (svgEl) svgEl.style.display = 'none';
      if (zoomBtns) zoomBtns.style.display = 'none';
      setTimeout(() => { streetMap.invalidateSize(); }, 50);
    }

    if (styleSelect && !styleSelect.dataset.bound) {
      styleSelect.dataset.bound = 'true';
      styleSelect.addEventListener('change', (e) => setMapStyle(e.target.value));
    }
  } catch (err) {
    console.warn('Leaflet initialization warning, falling back to Vector Street Map:', err);
    streetMap = null;
    const mapEl = document.getElementById('street-map');
    const svgEl = document.getElementById('map');
    if (mapEl) mapEl.style.display = 'none';
    if (svgEl) svgEl.style.display = 'block';
  }
}""",
        content
    )

    target.write_text(content, encoding="utf-8")
    print(f"Updated {target.name} ({len(content):,} bytes)")

