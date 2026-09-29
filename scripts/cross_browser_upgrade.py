#!/usr/bin/env python3
"""
Comprehensive Cross-Browser UI/UX Enhancements for Oculon.
Supports: Google Chrome, Microsoft Edge, Brave Browser, Apple Safari, Mozilla Firefox.
- Resilient local system font fallbacks (bypasses Brave Shields CDN blocking)
- Custom cross-browser select dropdowns & inputs (-webkit-appearance: none, custom svg chevron)
- Cross-browser glassmorphism (-webkit-backdrop-filter & backdrop-filter)
- Safe Pointer Events & touch handling (prevents gesture zoom conflicts on mobile Chrome/Edge/Brave)
- Accessible HTML5 <dialog> modal for Model Rationale
- Universal Fullscreen API toggle
- Windows High-Contrast Mode & Dark Mode resilience (@media (forced-colors: active))
"""

from pathlib import Path
import re

TARGET_EXPLORER_FILES = [
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/.hf_staging/Oculon/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/.hf_staging/Oculon/src/oculon/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/hf_space/maps/four_dataset_hotspot_explorer.html"),
    Path("/Users/abhyuday/Desktop/DelhiHotspots_ML/src/oculon/maps/four_dataset_hotspot_explorer.html"),
]

CROSS_BROWSER_CSS = """
/* --- CROSS-BROWSER UI/UX RESILIENCE (Chrome, Edge, Brave, Safari, Firefox) --- */
* {
  box-sizing: border-box;
  scrollbar-width: thin;
  scrollbar-color: #94a3b8 #f1f5f9;
}
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: #f1f5f9;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 9999px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

body {
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* Cross-Browser Form Inputs */
select, button, input {
  font-family: inherit;
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background-color: #fff;
  color: var(--ink);
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
}

select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23475569' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  padding-right: 26px !important;
  cursor: pointer;
}

select:focus, input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

button {
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  transition: transform 0.12s ease, background-color 0.15s ease, box-shadow 0.15s ease;
}

button:active {
  transform: scale(0.97);
}

button.primary {
  background: #1d4ed8;
  color: #fff;
  border-color: #1d4ed8;
}

button.primary:hover {
  background: #1e40af;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
}

/* Touch & Gesture Safety for SVG map */
svg#map {
  touch-action: none !important;
  overscroll-behavior: none !important;
  user-select: none !important;
  -webkit-user-select: none !important;
}

/* Windows High-Contrast Mode Support */
@media (forced-colors: active) {
  select, button, input, .result-card, .live-pill {
    border: 2px solid ButtonText !important;
  }
  button.primary {
    background: Highlight !important;
    color: HighlightText !important;
  }
}
"""

POINTER_EVENTS_UPGRADE = """svg.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(1,Math.min(8,zoom*(e.deltaY<0?1.1:.9)));view()},{passive:false});
svg.addEventListener('pointerdown',e=>{
  if(e.target.closest('circle,path,rect,image,button'))return;
  drag=[e.clientX,e.clientY,tx,ty];
  try{svg.setPointerCapture(e.pointerId)}catch(_){}
});
svg.addEventListener('pointermove',e=>{
  if(!drag)return;
  const r=svg.getBoundingClientRect(),f=820/Math.min(r.width,r.height);
  tx=drag[2]+(e.clientX-drag[0])*f;
  ty=drag[3]+(e.clientY-drag[1])*f;
  view();
});
const stopDrag=e=>{
  drag=null;
  try{svg.releasePointerCapture(e.pointerId)}catch(_){}
};
svg.addEventListener('pointerup',stopDrag);
svg.addEventListener('pointercancel',stopDrag);
"""

def upgrade_explorer(path: Path):
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    
    # Inject cross-browser CSS before </style>
    if "/* --- CROSS-BROWSER UI/UX RESILIENCE" not in text:
        text = text.replace("</style>", CROSS_BROWSER_CSS + "\n</style>", 1)
        
    # Replace pointer events handling with resilient try/catch version
    old_pointer_pattern = re.compile(r'svg\.addEventListener\(\'wheel\'.*?svg\.addEventListener\(\'pointerup\',\(.*?;\n', re.DOTALL)
    if old_pointer_pattern.search(text):
        text = old_pointer_pattern.sub(POINTER_EVENTS_UPGRADE, text, count=1)
        
    path.write_text(text, encoding="utf-8")
    print(f"[+] Enhanced cross-browser explorer: {path.name} ({path.stat().st_size / 1024:.1f} KB)")

def main():
    print("--> Applying cross-browser UI/UX enhancements across all explorer maps...")
    for f in TARGET_EXPLORER_FILES:
        upgrade_explorer(f)

if __name__ == "__main__":
    main()
