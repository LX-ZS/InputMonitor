"""
Generate unified SVG icons for InputMonitor.

运行：
    python tools/generate_svg_icons.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

SVG_HEADER = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none"
xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="g" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
<stop stop-color="#00D4FF"/>
<stop offset="0.52" stop-color="#7C5CFF"/>
<stop offset="1" stop-color="#FF5C8A"/>
</linearGradient>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
<feGaussianBlur stdDeviation="1.2" result="blur"/>
<feColorMatrix in="blur" type="matrix" values="0 0 0 0 0.49 0 0 0 0 0.36 0 0 0 0 1 0 0 0 0.55 0"/>
<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
</defs>
"""

COMMON = 'stroke="url(#g)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
DOT = 'fill="url(#g)" filter="url(#glow)"'

ICONS = {
"app_logo": f"""
<rect x="4" y="4" width="16" height="16" rx="5" {COMMON}/>
<path d="M8 13.5L10.3 10.5L12.7 14.2L16 8.8" {COMMON}/>
<circle cx="16" cy="8.8" r="1.5" {DOT}/>
""",
"dashboard": f"""
<rect x="4" y="4" width="7" height="7" rx="2" {COMMON}/>
<rect x="13" y="4" width="7" height="10" rx="2" {COMMON}/>
<rect x="4" y="13" width="7" height="7" rx="2" {COMMON}/>
<path d="M14 18H20" {COMMON}/>
<path d="M14 21H18" {COMMON}/>
""",
"timeline": f"""
<path d="M6 5V19" {COMMON}/>
<circle cx="6" cy="6" r="2" {COMMON}/>
<circle cx="6" cy="12" r="2" {COMMON}/>
<circle cx="6" cy="18" r="2" {COMMON}/>
<path d="M10 6H19" {COMMON}/>
<path d="M10 12H16" {COMMON}/>
<path d="M10 18H20" {COMMON}/>
""",
"settings": f"""
<path d="M12 8.2A3.8 3.8 0 1 0 12 15.8A3.8 3.8 0 0 0 12 8.2Z" {COMMON}/>
<path d="M4.8 13.6L3.8 12L4.8 10.4L6.6 10.1C6.9 9.4 7.1 8.9 7.6 8.4L7.1 6.7L8.7 5.7L10.2 6.5C10.8 6.3 11.4 6.2 12 6.2C12.6 6.2 13.2 6.3 13.8 6.5L15.3 5.7L16.9 6.7L16.4 8.4C16.9 8.9 17.1 9.4 17.4 10.1L19.2 10.4L20.2 12L19.2 13.6L17.4 13.9C17.1 14.6 16.9 15.1 16.4 15.6L16.9 17.3L15.3 18.3L13.8 17.5C13.2 17.7 12.6 17.8 12 17.8C11.4 17.8 10.8 17.7 10.2 17.5L8.7 18.3L7.1 17.3L7.6 15.6C7.1 15.1 6.9 14.6 6.6 13.9L4.8 13.6Z" {COMMON}/>
""",
"privacy": f"""
<path d="M12 3.8L18.5 6.4V11.2C18.5 15.4 15.8 18.7 12 20.2C8.2 18.7 5.5 15.4 5.5 11.2V6.4L12 3.8Z" {COMMON}/>
<path d="M9.2 12.2L11.2 14.2L15 9.8" {COMMON}/>
""",
"tray": f"""
<rect x="5" y="6" width="14" height="11" rx="3" {COMMON}/>
<path d="M8 10H16" {COMMON}/>
<path d="M8 14H12" {COMMON}/>
<circle cx="17.5" cy="17.5" r="2" {DOT}/>
""",
"mouse": f"""
<rect x="8" y="3.5" width="8" height="17" rx="4" {COMMON}/>
<path d="M12 4V9" {COMMON}/>
<path d="M8 10H16" {COMMON}/>
""",
"keyboard": f"""
<rect x="3.5" y="6" width="17" height="12" rx="3" {COMMON}/>
<path d="M7 10H7.1M10 10H10.1M13 10H13.1M16 10H16.1" {COMMON}/>
<path d="M7 14H17" {COMMON}/>
""",
"scroll": f"""
<path d="M12 4V20" {COMMON}/>
<path d="M8 8L12 4L16 8" {COMMON}/>
<path d="M8 16L12 20L16 16" {COMMON}/>
""",
"coding": f"""
<path d="M9 8L5 12L9 16" {COMMON}/>
<path d="M15 8L19 12L15 16" {COMMON}/>
<path d="M13 6L11 18" {COMMON}/>
""",
"writing": f"""
<path d="M5 18.5L9.2 17.5L18.2 8.5C19.1 7.6 19.1 6.2 18.2 5.3C17.3 4.4 15.9 4.4 15 5.3L6 14.3L5 18.5Z" {COMMON}/>
<path d="M13.8 6.5L17 9.7" {COMMON}/>
""",
"chat": f"""
<path d="M5 6.5C5 5.1 6.1 4 7.5 4H16.5C17.9 4 19 5.1 19 6.5V12.5C19 13.9 17.9 15 16.5 15H10L6.2 19V15H7.5C6.1 15 5 13.9 5 12.5V6.5Z" {COMMON}/>
<path d="M8.5 9.5H8.6M12 9.5H12.1M15.5 9.5H15.6" {COMMON}/>
""",
"browsing": f"""
<circle cx="12" cy="12" r="8" {COMMON}/>
<path d="M4 12H20" {COMMON}/>
<path d="M12 4C14 6.2 15 8.8 15 12C15 15.2 14 17.8 12 20" {COMMON}/>
<path d="M12 4C10 6.2 9 8.8 9 12C9 15.2 10 17.8 12 20" {COMMON}/>
""",
"reading": f"""
<path d="M4.5 5.5H10C11.1 5.5 12 6.4 12 7.5V19C12 17.9 11.1 17 10 17H4.5V5.5Z" {COMMON}/>
<path d="M19.5 5.5H14C12.9 5.5 12 6.4 12 7.5V19C12 17.9 12.9 17 14 17H19.5V5.5Z" {COMMON}/>
""",
"gaming": f"""
<path d="M7.5 10H16.5C18.7 10 20 11.6 20.4 14.2L20.7 16.2C21 18 19.1 19.1 17.8 17.8L16 16H8L6.2 17.8C4.9 19.1 3 18 3.3 16.2L3.6 14.2C4 11.6 5.3 10 7.5 10Z" {COMMON}/>
<path d="M8 13V16M6.5 14.5H9.5" {COMMON}/>
<path d="M15.5 14H15.6M18 14H18.1" {COMMON}/>
""",
"idle": f"""
<path d="M16.8 17.4C13.2 18.9 9 17.2 7.4 13.6C5.9 10.1 7.3 6 10.5 4.2C10.2 5.8 10.4 7.5 11.1 9.1C12.2 11.8 14.8 13.5 17.7 13.6C17.7 15 17.4 16.3 16.8 17.4Z" {COMMON}/>
""",
"mixed": f"""
<circle cx="7" cy="7" r="2.5" {COMMON}/>
<circle cx="17" cy="7" r="2.5" {COMMON}/>
<circle cx="12" cy="17" r="2.5" {COMMON}/>
<path d="M9.1 8.3L14.9 8.3" {COMMON}/>
<path d="M8.2 9.1L10.8 14.8" {COMMON}/>
<path d="M15.8 9.1L13.2 14.8" {COMMON}/>
"""
}

for name, body in ICONS.items():
    svg = SVG_HEADER + body + "\n</svg>\n"
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")

print(f"Generated {len(ICONS)} icons in {OUT}")
