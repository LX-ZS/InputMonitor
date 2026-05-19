"""
分类器 —— 基于特征窗口推断活动类型

规则引擎 + 可选的简单加权投票
"""

from dataclasses import dataclass
from typing import Optional

from config import (
    WINDOW_SIZE_SEC,
    TYPING_WPM_HIGH,
    TYPING_WPM_MED,
    MODIFIER_RATIO_HIGH,
    CLICK_RATE_GAMING,
    CLICK_RATE_LOW,
    SCROLL_HIGH,
    CLICK_RATE_BROWSING_MIN,
    CLICK_RATE_BROWSING_MAX,
    DRAG_RATIO_HIGH,
)


@dataclass
class Features:
    """从 feature_windows 行解析出的特征"""
    clicks_total: int = 0
    clicks_left: int = 0
    clicks_right: int = 0
    key_presses: int = 0
    key_letter: int = 0
    key_modifier: int = 0
    key_nav: int = 0
    key_num: int = 0
    scroll_distance: int = 0
    active_seconds: float = 0
    key_wasd: int = 0
    key_arrow: int = 0
    key_backspace: int = 0
    key_enter: int = 0
    key_space: int = 0
    key_ctrl_cv: int = 0
    key_shift_letter: int = 0

    # ---- 派生特征 ----
    @property
    def window_minutes(self) -> float:
        return WINDOW_SIZE_SEC / 60.0

    @property
    def clicks_per_min(self) -> float:
        return self.clicks_total / max(self.window_minutes, 0.01)

    @property
    def keys_per_min(self) -> float:
        return self.key_presses / max(self.window_minutes, 0.01)

    @property
    def typing_wpm(self) -> float:
        """估算打字速度（词/分钟，1词 ≈ 5击）"""
        return self.key_letter / max(self.window_minutes, 0.01) / 5.0

    @property
    def modifier_ratio(self) -> float:
        """修饰键在总按键中的占比"""
        if self.key_presses == 0:
            return 0.0
        return self.key_modifier / self.key_presses

    @property
    def nav_ratio(self) -> float:
        """导航键在总按键中的占比"""
        if self.key_presses == 0:
            return 0.0
        return self.key_nav / self.key_presses

    @property
    def num_ratio(self) -> float:
        if self.key_presses == 0:
            return 0.0
        return self.key_num / self.key_presses

    @property
    def right_click_ratio(self) -> float:
        if self.clicks_total == 0:
            return 0.0
        return self.clicks_right / self.clicks_total

    @property
    def wasd_ratio(self) -> float:
        """WASD 在字母键中的占比"""
        if self.key_letter == 0:
            return 0.0
        return self.key_wasd / self.key_letter

    @property
    def arrow_ratio(self) -> float:
        if self.key_presses == 0:
            return 0.0
        return self.key_arrow / self.key_presses

    @property
    def backspace_ratio(self) -> float:
        if self.key_letter == 0:
            return 0.0
        return self.key_backspace / self.key_letter


ACTIVITY_LABELS = {
    "coding":    "💻 编码",
    "writing":   "✍️ 写作",
    "chatting":  "💬 聊天",
    "browsing":  "🌐 浏览",
    "reading":   "📖 阅读",
    "gaming":    "🎮 游戏",
    "idle":      "💤 空闲",
    "mixed":     "🔄 混合",
}


def classify_window(f: Features) -> tuple[str, float]:
    """
    基于规则对单个窗口分类
    返回 (activity_type, confidence)
    """
    cpm = f.clicks_per_min
    wpm = f.typing_wpm
    mod_ratio = f.modifier_ratio
    scroll = f.scroll_distance
    nav = f.nav_ratio
    num = f.num_ratio
    wasd = f.wasd_ratio
    arrow = f.arrow_ratio
    bs = f.backspace_ratio

    # --- 空闲 ---
    if f.active_seconds < 30 and f.clicks_total < 2 and f.key_presses < 5:
        return ("idle", 0.9)

    # === 按键特征优先判断 ===

    # --- 游戏：WASD 占比高 + 高导航键 ---
    if wasd > 0.3 and (nav > 0.08 or arrow > 0.1):
        return ("gaming", 0.85)
    if cpm > CLICK_RATE_GAMING or f.keys_per_min > 300:
        return ("gaming", 0.8)
    if wasd > 0.2 and cpm > 30:
        return ("gaming", 0.7)

    # --- 编码：高退格 + 高修饰键 + 中速打字 ---
    if bs > 0.15 and mod_ratio > 0.08 and wpm >= TYPING_WPM_MED:
        return ("coding", 0.8)
    if wpm >= TYPING_WPM_MED and mod_ratio >= MODIFIER_RATIO_HIGH:
        return ("coding", 0.75)
    if mod_ratio >= 0.15 and nav >= 0.05:
        return ("coding", 0.65)
    if f.key_ctrl_cv > 3:
        return ("coding", 0.6)

    # --- 聊天：打字快 + 回车多 + 退格多 + 修饰键少 ---
    if f.key_enter > 8 and wpm >= TYPING_WPM_MED and mod_ratio <= 0.06:
        return ("chatting", 0.8)
    if f.key_enter > 4 and wpm >= TYPING_WPM_HIGH and f.key_space > 3:
        return ("chatting", 0.7)
    if f.key_enter > 2 and wpm >= TYPING_WPM_MED and bs > 0.1:
        return ("chatting", 0.6)

    # --- 写作：高速打字 + 低修饰 + 高空格 ---
    if wpm >= TYPING_WPM_HIGH and mod_ratio <= 0.08 and f.key_space > 5:
        return ("writing", 0.75)
    if wpm >= TYPING_WPM_HIGH and cpm <= CLICK_RATE_BROWSING_MAX and mod_ratio <= 0.08:
        return ("writing", 0.7)

    # --- 浏览：高滚动 + 中等点击 ---
    if scroll >= SCROLL_HIGH and CLICK_RATE_BROWSING_MIN <= cpm <= CLICK_RATE_BROWSING_MAX:
        return ("browsing", 0.7)
    if scroll >= SCROLL_HIGH // 2 and CLICK_RATE_BROWSING_MIN <= cpm <= CLICK_RATE_BROWSING_MAX:
        return ("browsing", 0.55)

    # --- 阅读：极低交互 + 一些滚动或点击 ---
    if cpm <= CLICK_RATE_LOW and wpm <= TYPING_WPM_MED and scroll >= 10:
        return ("reading", 0.6)
    if cpm < 3 and f.key_presses < 10 and scroll > 5:
        return ("reading", 0.5)

    # --- 默认：混合 ---
    return ("mixed", 0.4)


def classify_window_from_row(row: dict) -> tuple[str, float]:
    """从数据库行直接分类"""
    f = Features(
        clicks_total=row.get("clicks_total", 0),
        clicks_left=row.get("clicks_left", 0),
        clicks_right=row.get("clicks_right", 0),
        key_presses=row.get("key_presses", 0),
        key_letter=row.get("key_letter", 0),
        key_modifier=row.get("key_modifier", 0),
        key_nav=row.get("key_nav", 0),
        key_num=row.get("key_num", 0),
        scroll_distance=row.get("scroll_distance", 0),
        active_seconds=row.get("active_seconds", 0),
        key_wasd=row.get("key_wasd", 0),
        key_arrow=row.get("key_arrow", 0),
        key_backspace=row.get("key_backspace", 0),
        key_enter=row.get("key_enter", 0),
        key_space=row.get("key_space", 0),
        key_ctrl_cv=row.get("key_ctrl_cv", 0),
        key_shift_letter=row.get("key_shift_letter", 0),
    )
    return classify_window(f)


def vote_activity(windows: list[dict]) -> tuple[str, float]:
    """
    对多个窗口进行加权投票，得到今日/近期主要活动
    返回 (activity_type, weight)
    """
    if not windows:
        return ("idle", 0.0)

    scores: dict[str, float] = {}
    for w in windows:
        activity, conf = classify_window_from_row(w)
        scores[activity] = scores.get(activity, 0) + conf

    if not scores:
        return ("mixed", 0.0)

    best = max(scores, key=scores.get)
    return (best, scores[best] / len(windows))
