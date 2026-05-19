"""
InputMonitor 原始科技风色彩方案
"""

# ============ 核心色板 ============
BG_PRIMARY     = "#0a0e1a"
BG_SECONDARY   = "#121829"
BG_CARD        = "#1a1f2e"
BG_CARD_HOVER  = "#222840"

ACCENT_CYAN    = "#00d4ff"
ACCENT_PURPLE  = "#6c63ff"
ACCENT_GREEN   = "#00e676"
ACCENT_AMBER   = "#ffab00"
ACCENT_RED     = "#ff5252"

TEXT_PRIMARY   = "#e0e6f0"
TEXT_SECONDARY = "#8892b0"
TEXT_DIM       = "#4a5570"

BORDER_COLOR   = "#252d42"
DIVIDER_COLOR  = "#1e2538"

# ============ 活动类型颜色 ============
ACTIVITY_COLORS = {
    "coding":   "#00d4ff",
    "writing":  "#6c63ff",
    "chatting": "#ff6ec7",
    "browsing": "#00e676",
    "reading":  "#ffab00",
    "gaming":   "#ff5252",
    "idle":     "#4a5570",
    "mixed":    "#8892b0",
}

# ============ 布局常量 ============
PAD_SMALL  = 6
PAD_MEDIUM = 12
PAD_LARGE  = 20
RADIUS     = 10
RADIUS_SM  = 6

# ============ 字体 ============
FONT_FAMILY = "Microsoft YaHei"

def size_sm():
    return (FONT_FAMILY, 11)

def size_md():
    return (FONT_FAMILY, 13)

def size_lg():
    return (FONT_FAMILY, 16)

def size_xl():
    return (FONT_FAMILY, 22)

def size_xxl():
    return (FONT_FAMILY, 32)

# 别名兼容
BG_DEEPEST  = BG_PRIMARY
BG_SURFACE  = BG_SECONDARY
BG_RAISED   = BG_CARD
BG_HOVER    = BG_CARD_HOVER
BG_HEADER   = BG_SECONDARY
BORDER_SUBTLE = BORDER_COLOR
BORDER_DIM  = "#1e2538"
ACCENT_TEAL = ACCENT_CYAN
GLOW_CYAN   = BG_CARD_HOVER
GRID_LINE   = BORDER_COLOR
PAD_4 = 4
PAD_8 = 8
PAD_12 = 12
PAD_16 = 16
PAD_20 = 20
PAD_24 = 24
PAD_32 = 32
