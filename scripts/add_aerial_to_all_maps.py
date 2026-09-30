#!/usr/bin/env python3
"""
Integrate Live Aerial View & Tactical Recon HUD across ALL Oculon Maps:
1. four_dataset_hotspot_explorer.html (All-in-one Explorer)
2. missing_persons_map.html
3. stolen_vehicles_map.html
4. mobiles_and_bodies_map.html
"""
from pathlib import Path
import re
import shutil

ROOT_DIR = Path("/Users/abhyuday/Desktop/DelhiHotspots_ML")

STANDALONE_MAP_NAMES = [
    "missing_persons_map.html",
    "stolen_vehicles_map.html",
    "mobiles_and_bodies_map.html"
]

STANDALONE_DIRS = [
    ROOT_DIR / "src" / "oculon" / "maps",
    ROOT_DIR / "app" / "individual_maps",
    ROOT_DIR / "hf_space" / "maps",
    ROOT_DIR / ".hf_staging" / "Oculon" / "maps",
    ROOT_DIR / ".hf_staging" / "Oculon" / "src" / "oculon" / "maps",
    ROOT_DIR / ".hf_staging" / "Oculon" / "dist_pages" / "maps",
    ROOT_DIR / "dist_pages" / "maps",
]

from add_live_aerial_view import AERIAL_CSS, AERIAL_MODAL_HTML, AERIAL_JS

LEAFLET_HEAD = """<!-- Leaflet & Aerial Satellite Assets -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
"""

def upgrade_standalone_map(path: Path):
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")

    # 1. Add Leaflet CSS/JS to <head>
    if "leaflet@1.9.4" not in content:
        content = content.replace("<head>", f"<head>\n{LEAFLET_HEAD}")

    # 2. Add AERIAL_CSS to <style>
    if "/* 🛰️ LIVE AERIAL TACTICAL RECONNAISSANCE" not in content:
        content = content.replace("</style>", AERIAL_CSS + "\n</style>")

    # 3. Add AERIAL_MODAL_HTML before </body>
    if 'id="aerial-modal"' not in content:
        content = content.replace("</body>", AERIAL_MODAL_HTML + "\n</body>")

    # 4. Add AERIAL_JS before </script>
    if "function openLiveAerialView" not in content:
        content = content.replace("</script>", AERIAL_JS + "\n</script>")

    # 5. Enhance click listener in point(...)
    old_listener = "c.addEventListener('click',()=>document.getElementById('status').textContent=t.textContent);"
    new_listener = "c.addEventListener('click',()=>{document.getElementById('status').textContent=t.textContent;if(item.lat&&item.lon)openLiveAerialView(item.lat,item.lon,item.name,item.district||'',item.score||0,item.count||0,cls);});"
    if old_listener in content:
        content = content.replace(old_listener, new_listener)

    path.write_text(content, encoding="utf-8")
    print(f"[+] Upgraded standalone map: {path}")

def main():
    print("=" * 70)
    print("🛰️ Upgrading All Standalone Maps with Live Aerial Recon HUD")
    print("=" * 70)
    for d in STANDALONE_DIRS:
        for map_name in STANDALONE_MAP_NAMES:
            p = d / map_name
            upgrade_standalone_map(p)

    # Rebuild pages
    build_script = ROOT_DIR / "scripts" / "build_pages_site.py"
    if build_script.exists():
        import subprocess
        print("[*] Rebuilding static GitHub Pages portal...")
        subprocess.run(["python3", str(build_script)], check=True)

if __name__ == "__main__":
    main()
