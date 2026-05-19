"""
特征提取 —— 从原始事件窗口计算特征向量
"""

import time
from collections import Counter

from storage.db import get_events_in_range, upsert_feature_window
from config import WINDOW_SIZE_SEC, IDLE_THRESHOLD_SEC


def extract_and_save_features(window_start: float, window_end: float):
    """
    从指定时间范围内的事件提取特征，保存到 feature_windows 表
    由定时器每分钟检查并调用
    """
    events = get_events_in_range(window_start, window_end)
    if not events:
        # 空窗口 —— 仍然写入一条空记录，供 UI 判断空闲
        upsert_feature_window({
            "window_start":   window_start,
            "window_end":     window_end,
            "clicks_total":   0,
            "clicks_left":    0,
            "clicks_right":   0,
            "clicks_middle":  0,
            "scroll_distance": 0,
            "key_presses":    0,
            "key_letter":     0,
            "key_modifier":   0,
            "key_nav":        0,
            "key_num":        0,
            "key_function":   0,
            "key_other":      0,
            "key_wasd":       0,
            "key_arrow":      0,
            "key_backspace":  0,
            "key_enter":      0,
            "key_space":      0,
            "key_ctrl_cv":    0,
            "key_shift_letter":0,
            "active_seconds": 0,
        })
        return

    clicks_left = clicks_right = clicks_middle = 0
    scroll_dist = 0
    key_counts: Counter = Counter()
    total_keys = 0

    # 活跃时间计算：找到事件的时间跨度
    timestamps = [e["ts"] for e in events if e["event_type"] != "mouse_move"]
    if not timestamps:
        timestamps = [e["ts"] for e in events]

    active_sec = 0.0
    if len(timestamps) >= 2:
        timestamps.sort()
        # 总跨时间
        total_span = timestamps[-1] - timestamps[0]
        if total_span > 0:
            # 减去内部超过空闲阈值的间隙
            idle_gaps = 0.0
            for i in range(1, len(timestamps)):
                gap = timestamps[i] - timestamps[i - 1]
                if gap > IDLE_THRESHOLD_SEC:
                    idle_gaps += gap
            active_sec = max(total_span - idle_gaps, 0)

    for ev in events:
        etype = ev["event_type"]
        if etype == "mouse_click":
            btn = ev.get("button", "")
            if "left" in btn.lower():
                clicks_left += 1
            elif "right" in btn.lower():
                clicks_right += 1
            else:
                clicks_middle += 1

        elif etype == "mouse_scroll":
            scroll_dist += 1  # 每次滚动事件计1

        elif etype == "key_down":
            cat = ev.get("button", "other")
            key_counts[cat] += 1
            total_keys += 1
            # 特定按键统计
            kchar = ev.get("key_char", "")
            if kchar in ("w","a","s","d"):
                key_counts["wasd"] += 1
            elif kchar in ("up","down","left","right"):
                key_counts["arrow"] += 1
            elif kchar == "backspace":
                key_counts["backspace"] += 1
            elif kchar == "enter":
                key_counts["enter"] += 1
            elif kchar == "space":
                key_counts["space"] += 1
            elif kchar == "ctrl_c" or kchar == "ctrl_v":
                key_counts["ctrl_cv"] += 1

    upsert_feature_window({
        "window_start":    window_start,
        "window_end":      window_end,
        "clicks_total":    clicks_left + clicks_right + clicks_middle,
        "clicks_left":     clicks_left,
        "clicks_right":    clicks_right,
        "clicks_middle":   clicks_middle,
        "scroll_distance": scroll_dist,
        "key_presses":     total_keys,
        "key_letter":      key_counts.get("letter", 0),
        "key_modifier":    key_counts.get("modifier", 0),
        "key_nav":         key_counts.get("nav", 0),
        "key_num":         key_counts.get("digit", 0),
        "key_function":    key_counts.get("function", 0),
        "key_other":       key_counts.get("other", 0),
        "key_wasd":        key_counts.get("wasd", 0),
        "key_arrow":       key_counts.get("arrow", 0),
        "key_backspace":   key_counts.get("backspace", 0),
        "key_enter":       key_counts.get("enter", 0),
        "key_space":       key_counts.get("space", 0),
        "key_ctrl_cv":     key_counts.get("ctrl_cv", 0),
        "key_shift_letter":0,
        "active_seconds":  active_sec,
    })
