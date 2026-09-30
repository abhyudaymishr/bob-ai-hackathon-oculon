#!/usr/bin/env python3
"""
Fix Delhi Street Map rendering across all copies of four_dataset_hotspot_explorer.html
and rebuild the static web portal for GitHub Pages.
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

def fix_map_html(content: str) -> str:
    # 1. Clean head leaflet tags (remove document.write)
    head_pattern = r'<!-- Leaflet & Street Map Assets -->.*?<script src="https://unpkg\.com/leaflet\.heat@0\.2\.0/dist/leaflet-heat\.js"></script>'
    clean_head = '''<!-- Leaflet & Street Map Assets -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>'''
    
    if re.search(head_pattern, content, re.DOTALL):
        content = re.sub(head_pattern, clean_head, content, flags=re.DOTALL)
    
    # 2. Fix CSS: make #street-map display: block and svg#map display: none by default, plus style .street-territory
    css_fix = '''
/* Delhi Street Map Styles */
#street-map {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
  display: block;
  background: #f8fafc;
}
svg#map {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  display: none;
  background: #f8fafc;
}
.street-territory {
  fill: #f1f5f9 !important;
  fill-opacity: 0.85 !important;
  stroke: #64748b !important;
  stroke-width: 1.2 !important;
  vector-effect: non-scaling-stroke;
}
.road-expressway {
  fill: none;
  stroke: #f59e0b;
  stroke-width: 3.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
.road-highway {
  fill: none;
  stroke: #64748b;
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
.road-arterial {
  fill: none;
  stroke: #94a3b8;
  stroke-width: 1.8;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}
.yamuna-river {
  fill: none;
  stroke: #38bdf8;
  stroke-width: 13;
  opacity: 0.78;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}
'''
    # Replace existing #street-map block
    street_map_css_pattern = r'/\* Delhi Street Map Styles \*/\s*#street-map\s*\{[^}]*\}'
    if re.search(street_map_css_pattern, content):
        content = re.sub(street_map_css_pattern, css_fix, content)
    else:
        # If not matched, insert before </style>
        content = content.replace('</style>', css_fix + '\n</style>', 1)
        
    # 3. Update tileServers with subdomains
    old_tile_servers = r"const tileServers = \{.*?\};"
    new_tile_servers = '''const tileServers = {
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
};'''
    content = re.sub(old_tile_servers, new_tile_servers, content, flags=re.DOTALL)
    
    # 4. Update startMapEngine logic
    start_engine_pattern = r'function startMapEngine\(\)\s*\{.*?\}\s*(?=function updateLeafletHotspots)'
    new_start_engine = '''function startMapEngine() {
  if (typeof window.L !== 'undefined') {
    initStreetMap();
  } else {
    let tries = 0;
    const interval = setInterval(() => {
      tries++;
      if (typeof window.L !== 'undefined') {
        clearInterval(interval);
        initStreetMap();
      } else if (tries > 35) {
        clearInterval(interval);
        console.warn('Leaflet timed out, falling back to vector.');
        setMapStyle('vector');
      }
    }, 100);
  }
}
'''
    content = re.sub(start_engine_pattern, new_start_engine, content, flags=re.DOTALL)

    # 5. Ensure startMapEngine() is invoked at the bottom of the script
    bottom_pattern = r'refreshDataset\(\);\s*query\(\);(?!\s*startMapEngine)'
    if re.search(bottom_pattern, content):
        content = re.sub(
            bottom_pattern,
            'refreshDataset();\nquery();\nstartMapEngine();\nwindow.addEventListener("load", () => { if (!streetMap) startMapEngine(); setTimeout(() => { if (streetMap) streetMap.invalidateSize(); }, 300); });',
            content
        )
    elif 'startMapEngine();' not in content:
        content = content.replace('refreshDataset();query();', 'refreshDataset();query();startMapEngine();\nwindow.addEventListener("load", () => { if (!streetMap) startMapEngine(); setTimeout(() => { if (streetMap) streetMap.invalidateSize(); }, 300); });')

    return content

def main():
    print("--> Patching all copies of four_dataset_hotspot_explorer.html...")
    for path in MAP_FILES:
        if path.exists():
            original = path.read_text(encoding="utf-8")
            patched = fix_map_html(original)
            path.write_text(patched, encoding="utf-8")
            print(f"    [+] Successfully patched: {path.relative_to(ROOT_DIR)}")
        else:
            print(f"    [-] File not found, skipping: {path}")

if __name__ == "__main__":
    main()
