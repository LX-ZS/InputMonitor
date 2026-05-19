"""
InputMonitor UI style tokens.

用法：
    from ui.style_tokens import PALETTE, ACTIVITY_COLORS, SPACING
"""

from __future__ import annotations

PALETTE = {
    "dark": {
        "bg": "#070A12",
        "bg_soft": "#0D1320",
        "card": "#111827",
        "card_hover": "#172033",
        "border": "#263247",
        "text": "#EAF0FF",
        "muted": "#8A93A6",
        "accent": "#7C5CFF",
        "accent_2": "#00D4FF",
        "success": "#29D3A6",
        "warning": "#FFB347",
        "danger": "#FF5C8A",
    },
    "light": {
        "bg": "#F7F8FC",
        "bg_soft": "#EEF3FF",
        "card": "#FFFFFF",
        "card_hover": "#F3F6FF",
        "border": "#D9E1F2",
        "text": "#111827",
        "muted": "#667085",
        "accent": "#4F7CFF",
        "accent_2": "#25B6E8",
        "success": "#17A887",
        "warning": "#E7952D",
        "danger": "#E54872",
    },
}

ACTIVITY_COLORS = {
    "coding": "#7C5CFF",
    "writing": "#FFB347",
    "chat": "#29D3A6",
    "browsing": "#4DB6FF",
    "reading": "#9AA7FF",
    "gaming": "#FF5C8A",
    "idle": "#8A93A6",
    "mixed": "#C77DFF",
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 18,
    "xl": 24,
    "xxl": 32,
}

RADIUS = {
    "sm": 10,
    "md": 14,
    "lg": 18,
    "xl": 24,
    "pill": 999,
}

FONT = {
    "family": "Microsoft YaHei UI",
    "title": 24,
    "subtitle": 18,
    "body": 14,
    "small": 12,
    "metric": 28,
}


def get_palette(mode: str = "dark") -> dict:
    return PALETTE.get(mode, PALETTE["dark"])


def activity_color(activity: str) -> str:
    return ACTIVITY_COLORS.get(activity, ACTIVITY_COLORS["mixed"])
