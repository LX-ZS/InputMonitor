"""
活动图标加载器 —— 使用补充包的 SVG 渲染图标
"""

import os
from PIL import Image
import customtkinter as ctk

_ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons_png")
_CACHE = {}

def get_ctk_image(activity: str, size: int = 18) -> ctk.CTkImage:
    key = (activity, size)
    if key in _CACHE:
        return _CACHE[key]

    path = os.path.join(_ICON_DIR, f"{activity}.png")
    if os.path.exists(path):
        img = Image.open(path).convert("RGBA")
    else:
        img = Image.new("RGBA", (24, 24), (0, 0, 0, 0))

    ct = ctk.CTkImage(img, size=(size, size))
    _CACHE[key] = ct
    return ct
