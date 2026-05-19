"""
InputMonitor 主窗口
CustomTkinter 科技风 UI + 系统托盘
"""

import queue
import threading
import time
from datetime import datetime, date
from typing import Optional

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw

from ui.styles import *
from storage.db import (
    init_db, get_today_summary, get_today_windows,
    get_today_activity_segments, get_latest_activity,
    get_events_in_range, get_raw_counts, get_latest_activity_start,
    cleanup_old_data,
)
from engine.features import extract_and_save_features
from engine.classifier import classify_window_from_row, ACTIVITY_LABELS
from config import (
    WINDOW_SIZE_SEC, UPDATE_INTERVAL_MS, WINDOW_SIZE,
    WINDOW_TITLE, RAW_EVENT_RETENTION_DAYS, RECORD_MOUSE_COORDS,
)


# ================================================================
# 工具
# ================================================================

def _format_duration(seconds: float) -> str:
    """将秒数格式化为 Xh Ym"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def _make_tray_icon(size: int = 32) -> Image.Image:
    """绘制系统托盘图标 —— 科技感圆点"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size // 2
    r = size // 2 - 2
    # 外圈
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT_CYAN, width=2)
    # 内圈
    r2 = r - 5
    draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=ACCENT_CYAN)
    # 中心亮点
    r3 = r2 - 4
    draw.ellipse([cx - r3, cy - r3, cx + r3, cy + r3], fill="#ffffff")
    return img


# ================================================================
# 仪表盘卡片组件
# ================================================================

class MetricCard(ctk.CTkFrame):
    """指标卡片：顶部色条 + 大数字 + 标签"""

    def __init__(self, master, label: str, value: str = " — ",
                 unit: str = "", accent_color: str = ACCENT_CYAN, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=RADIUS,
                         border_width=1, border_color=BORDER_COLOR, **kwargs)
        self.accent = accent_color

        # 顶部色条
        bar = ctk.CTkFrame(self, height=3, fg_color=self.accent, corner_radius=0)
        bar.pack(fill="x", side="top")

        # 标签
        self._label = ctk.CTkLabel(self, text=label, font=size_sm(),
                                   text_color=TEXT_SECONDARY)
        self._label.pack(pady=(PAD_MEDIUM, 0))

        # 值
        self._value = ctk.CTkLabel(self, text=value, font=("Consolas", 28, "bold"),
                                   text_color=self.accent)
        self._value.pack(pady=(0, 0))

        # 单位
        self._unit = ctk.CTkLabel(self, text=unit, font=size_sm(),
                                  text_color=TEXT_DIM)
        self._unit.pack(pady=(0, PAD_MEDIUM))

    def set_value(self, value: str):
        self._value.configure(text=value)


class ActivityIndicator(ctk.CTkFrame):
    """当前活动指示器"""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=RADIUS,
                         border_width=1, border_color=BORDER_COLOR, **kwargs)
        self._label_top = ctk.CTkLabel(self, text="当前活动",
                                       font=size_sm(), text_color=TEXT_SECONDARY)
        self._label_top.pack(pady=(PAD_MEDIUM, 2))

        self._icon = ctk.CTkLabel(self, text="🔄", font=("Segoe UI Emoji", 36))
        self._icon.pack()

        self._activity = ctk.CTkLabel(self, text="检测中...",
                                      font=size_xl(), text_color=ACCENT_CYAN)
        self._activity.pack(pady=(0, 2))

        self._sub = ctk.CTkLabel(self, text="", font=size_sm(),
                                 text_color=TEXT_DIM)
        self._sub.pack(pady=(0, PAD_MEDIUM))

    def update(self, activity_key: str, confidence: float = 0.0):
        label = ACTIVITY_LABELS.get(activity_key, "🔄 未知")
        color = ACTIVITY_COLORS.get(activity_key, TEXT_SECONDARY)
        self._activity.configure(text=label, text_color=color)
        self._sub.configure(text=f"置信度 {confidence:.0%}" if confidence > 0 else "")


class TimelineBar(ctk.CTkFrame):
    """活动时间线横条"""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=RADIUS,
                         border_width=1, border_color=BORDER_COLOR, **kwargs)
        self._canvas = ctk.CTkCanvas(self, height=40, bg=BG_CARD,
                                     highlightthickness=0)
        self._canvas.pack(fill="x", padx=PAD_SMALL, pady=PAD_SMALL)
        self._time_label = ctk.CTkLabel(self, text="", font=size_sm(),
                                        text_color=TEXT_DIM)
        self._time_label.pack(pady=(0, PAD_SMALL))

    def redraw(self, segments: list[dict]):
        """绘制时间线"""
        c = self._canvas
        c.delete("all")
        w = c.winfo_width()
        if w < 50:
            w = 600
        h = 36
        if not segments:
            c.create_text(w // 2, h // 2, text="暂无数据", fill=TEXT_DIM,
                          font=("Microsoft YaHei", 11))
            return

        today_0 = datetime.combine(date.today(), datetime.min.time()).timestamp()
        now_ts = time.time()
        span = max(now_ts - today_0, 1)

        # 整点刻度线
        for hour in range(0, 24, 1):
            hx = (hour * 3600) / span * w
            c.create_line(hx, 2, hx, h - 2, fill=BORDER_SUBTLE, width=1)

        # 活动段
        for seg in segments:
            x1 = (seg["start_time"] - today_0) / span * w
            x2 = (seg["end_time"] - today_0) / span * w
            color = ACTIVITY_COLORS.get(seg["activity_type"], TEXT_SECONDARY)
            c.create_rectangle(x1, 4, x2, h - 4, fill=color, outline="", width=0)

        # 时间标签
        for hour in range(0, 24, 3):
            hx = (hour * 3600) / span * w
            c.create_text(hx, h + 2, text=f"{hour:02d}:00",
                          fill=TEXT_DIM, font=("Microsoft YaHei", 8), anchor="n")

        # 当前时间
        now_x = (now_ts - today_0) / span * w
        c.create_line(now_x, 2, now_x, h - 2, fill="#ffffff", width=1)


class DistributionBar(ctk.CTkFrame):
    """活动分布比例条"""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=RADIUS,
                         border_width=1, border_color=BORDER_COLOR, **kwargs)
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", padx=PAD_MEDIUM, pady=PAD_MEDIUM, expand=True)

    def redraw(self, segments: list[dict]):
        """根据活动段统计各活动占比"""
        for w in self._content.winfo_children():
            w.destroy()

        if not segments:
            ctk.CTkLabel(self._content, text="暂无数据", font=size_md(),
                         text_color=TEXT_DIM).pack(pady=20)
            return

        # 统计每个活动的段数
        from collections import Counter
        counts: Counter = Counter()
        for s in segments:
            counts[s["activity_type"]] += 1

        total = sum(counts.values())
        if total == 0:
            return

        # 按占比降序排列
        sorted_items = sorted(counts.items(), key=lambda x: -x[1])

        for act, cnt in sorted_items:
            pct = cnt / total * 100
            label = ACTIVITY_LABELS.get(act, act)
            color = ACTIVITY_COLORS.get(act, TEXT_SECONDARY)

            row = ctk.CTkFrame(self._content, fg_color="transparent")
            row.pack(fill="x", pady=3)

            # 标签
            ctk.CTkLabel(row, text=label, font=size_sm(),
                         text_color=TEXT_PRIMARY, width=80, anchor="w").pack(side="left")
            # 进度条
            bar_frame = ctk.CTkFrame(row, fg_color=BG_SECONDARY, height=18,
                                     corner_radius=RADIUS_SM)
            bar_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
            bar_width = max(pct / 100 * 200, 4)  # 最小宽度 4px
            bar = ctk.CTkFrame(bar_frame, fg_color=color, height=18, width=int(bar_width),
                               corner_radius=RADIUS_SM)
            bar.place(x=0, y=0)

            # 百分比
            ctk.CTkLabel(row, text=f"{pct:.0f}%", font=("Consolas", 11, "bold"),
                         text_color=TEXT_SECONDARY, width=40, anchor="e").pack(side="right")


# ================================================================
# 主应用
# ================================================================

class InputMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ---- 窗口设置 ----
        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.minsize(800, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # ---- 后台采集 ----
        self._ic: Optional[object] = None
        self._collector_running = False
        self._last_window_check = 0.0

        # ---- 初始化 DB ----
        init_db()
        # cleanup_old_data 移到 _lazy_init 延迟执行

        # ---- 构建 UI ----
        self._build_ui()

        # ---- 自动开始采集 ----
        self._auto_start()

        # ---- 启动定时刷新 ----
        self._schedule_refresh()

        # ---- 延迟加载（非关键初始化放到窗口显示后） ----
        self.after(100, self._lazy_init)

        # ---- 关闭事件 ----
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================================================================
    # UI 构建
    # ================================================================

    def _build_ui(self):
        # 主容器
        self._main = ctk.CTkFrame(self, fg_color=BG_PRIMARY)
        self._main.pack(fill="both", expand=True)

        # 标题栏
        title_bar = ctk.CTkFrame(self._main, fg_color=BG_SECONDARY, height=48,
                                 corner_radius=0)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        ctk.CTkLabel(title_bar,
                     text="◆ InputMonitor  —  行为感知系统",
                     font=("Microsoft YaHei", 15, "bold"),
                     text_color=ACCENT_CYAN).pack(side="left", padx=PAD_LARGE, pady=10)

        # 采集状态指示
        self._status_dot = ctk.CTkLabel(title_bar, text="●",
                                        font=("Consolas", 14), text_color=ACCENT_GREEN)
        self._status_dot.pack(side="right", padx=(0, 4))
        self._status_label = ctk.CTkLabel(title_bar, text="运行中",
                                          font=size_sm(), text_color=TEXT_SECONDARY)
        self._status_label.pack(side="right", padx=(0, PAD_LARGE))

        # 选项卡
        self._tabview = ctk.CTkTabview(self._main, fg_color=BG_PRIMARY,
                                       segmented_button_fg_color=BG_SECONDARY,
                                       segmented_button_selected_color=BG_CARD,
                                       segmented_button_selected_hover_color=BG_CARD_HOVER,
                                       text_color=TEXT_SECONDARY,
                                       segmented_button_unselected_color=BG_SECONDARY,
                                       segmented_button_unselected_hover_color=BG_CARD_HOVER)
        self._tabview.pack(fill="both", expand=True, padx=PAD_MEDIUM, pady=PAD_MEDIUM)

        # ---- 仪表盘 ----
        self._tab_dash = self._tabview.add("📊 仪表盘")
        self._build_dashboard()

        # ---- 时间线 ----
        self._tab_timeline = self._tabview.add("📅 时间线")
        self._build_timeline()

        # ---- 设置 ----
        self._tab_settings = self._tabview.add("⚙ 设置")
        self._build_settings()

    # ---------- 仪表盘 ----------

    def _build_dashboard(self):
        container = ctk.CTkScrollableFrame(self._tab_dash, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=PAD_MEDIUM, pady=PAD_MEDIUM)

        # 顶部：4 个指标卡片
        cards = ctk.CTkFrame(container, fg_color="transparent")
        cards.pack(fill="x")

        cards.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="card")

        self._card_clicks = MetricCard(cards, "今日点击", "—", "次", ACCENT_CYAN)
        self._card_clicks.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

        self._card_keys = MetricCard(cards, "今日按键", "—", "次", ACCENT_PURPLE)
        self._card_keys.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        self._card_time = MetricCard(cards, "活跃时长", "—", "", ACCENT_GREEN)
        self._card_time.grid(row=0, column=2, padx=4, pady=4, sticky="nsew")

        self._card_activity = ActivityIndicator(cards)
        self._card_activity.grid(row=0, column=3, padx=4, pady=4, sticky="nsew")

        # 刷新控件
        refresh_bar = ctk.CTkFrame(container, fg_color="transparent")
        refresh_bar.pack(fill="x", pady=(PAD_MEDIUM, 0))

        self._refresh_btn = ctk.CTkButton(
            refresh_bar, text="🔄 立即刷新", width=110,
            fg_color=ACCENT_CYAN, hover_color="#00a8cc",
            text_color="#080808", font=("Microsoft YaHei", 12, "bold"),
            command=self._manual_refresh,
        )
        self._refresh_btn.pack(side="left")

        self._updated_label = ctk.CTkLabel(
            refresh_bar, text="● 自动刷新中", font=("Microsoft YaHei", 10),
            text_color=ACCENT_GREEN,
        )
        self._updated_label.pack(side="left", padx=(PAD_MEDIUM, 0))

        self._last_update = ctk.CTkLabel(
            refresh_bar, text="", font=("Consolas", 9),
            text_color=TEXT_DIM,
        )
        self._last_update.pack(side="right")

        # ---- 快速标注栏 ----
        self._label_bar = ctk.CTkFrame(container, fg_color="transparent")
        self._label_bar.pack(fill="x", pady=(PAD_SMALL, 0))
        self._label_feedback = ctk.CTkLabel(self._label_bar, text="", font=("Microsoft YaHei", 9),
                                             text_color=ACCENT_GREEN)
        self._labeled_count = ctk.CTkLabel(self._label_bar, text="已标注: 0", font=("Consolas", 9),
                                            text_color=TEXT_DIM)
        self._rebuild_label_bar()

        # 中间：活动时间线
        timeline_label = ctk.CTkLabel(container, text="今日活动时间线",
                                      font=size_md(), text_color=TEXT_SECONDARY,
                                      anchor="w")
        timeline_label.pack(fill="x", pady=(PAD_LARGE, PAD_SMALL))
        self._timeline = TimelineBar(container)
        self._timeline.pack(fill="x")

        # 底部：活动分布
        dist_label = ctk.CTkLabel(container, text="活动分布",
                                  font=size_md(), text_color=TEXT_SECONDARY,
                                  anchor="w")
        dist_label.pack(fill="x", pady=(PAD_MEDIUM, PAD_SMALL))
        self._distribution = DistributionBar(container)
        self._distribution.pack(fill="x", pady=(0, PAD_MEDIUM))

    # ---------- 时间线 ----------

    def _build_timeline(self):
        container = ctk.CTkScrollableFrame(self._tab_timeline, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=PAD_MEDIUM, pady=PAD_MEDIUM)

        # 日期导航
        nav = ctk.CTkFrame(container, fg_color="transparent")
        nav.pack(fill="x", pady=(0, PAD_MEDIUM))

        ctk.CTkButton(nav, text="◀", width=30, font=("Consolas", 14),
                      fg_color="transparent", text_color=ACCENT_CYAN,
                      border_width=1, border_color=BORDER_DIM,
                      hover_color=GLOW_CYAN,
                      command=self._tl_prev_day).pack(side="left", padx=(0, 4))

        self._tl_date_label = ctk.CTkLabel(nav, text="", font=("Consolas", 14, "bold"),
                                            text_color=TEXT_PRIMARY, width=200)
        self._tl_date_label.pack(side="left")

        ctk.CTkButton(nav, text="▶", width=30, font=("Consolas", 14),
                      fg_color="transparent", text_color=ACCENT_CYAN,
                      border_width=1, border_color=BORDER_DIM,
                      hover_color=GLOW_CYAN,
                      command=self._tl_next_day).pack(side="left", padx=(4, 0))

        ctk.CTkButton(nav, text="TODAY", font=("Consolas", 9),
                      fg_color="transparent", text_color=TEXT_SECONDARY,
                      border_width=1, border_color=BORDER_DIM,
                      hover_color=GLOW_CYAN,
                      command=self._tl_goto_today).pack(side="left", padx=(PAD_MEDIUM, 0))

        # 摘要卡片
        tl_cards = ctk.CTkFrame(container, fg_color="transparent")
        tl_cards.pack(fill="x")
        tl_cards.grid_columnconfigure((0,1,2,3), weight=1, uniform="tl")

        self._tl_card_clicks = MetricCard(tl_cards, "TOTAL CLICKS", "—", "", ACCENT_CYAN)
        self._tl_card_clicks.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")
        self._tl_card_keys = MetricCard(tl_cards, "TOTAL KEYS", "—", "", ACCENT_PURPLE)
        self._tl_card_keys.grid(row=0, column=1, padx=3, pady=3, sticky="nsew")
        self._tl_card_time = MetricCard(tl_cards, "ACTIVE TIME", "—", "", ACCENT_GREEN)
        self._tl_card_time.grid(row=0, column=2, padx=3, pady=3, sticky="nsew")
        self._tl_card_top = MetricCard(tl_cards, "TOP ACTIVITY", "—", "", ACCENT_AMBER)
        self._tl_card_top.grid(row=0, column=3, padx=3, pady=3, sticky="nsew")

        # 时间线
        ctk.CTkLabel(container, text="ACTIVITY TIMELINE",
                     font=("Consolas", 10, "bold"), text_color=TEXT_SECONDARY, anchor="w").pack(
            fill="x", pady=(PAD_MEDIUM, PAD_SMALL))
        self._tl_timeline = TimelineBar(container)
        self._tl_timeline.pack(fill="x")

        # 活动分布
        ctk.CTkLabel(container, text="DISTRIBUTION",
                     font=("Consolas", 10, "bold"), text_color=TEXT_SECONDARY, anchor="w").pack(
            fill="x", pady=(PAD_MEDIUM, PAD_SMALL))
        self._tl_dist = DistributionBar(container)
        self._tl_dist.pack(fill="x", pady=(0, PAD_MEDIUM))

        # 活动日志
        ctk.CTkLabel(container, text="ACTIVITY LOG",
                     font=("Consolas", 10, "bold"), text_color=TEXT_SECONDARY, anchor="w").pack(
            fill="x", pady=(PAD_MEDIUM, PAD_SMALL))
        self._tl_list_frame = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=RADIUS,
                                            border_width=1, border_color=BORDER_DIM)
        self._tl_list_frame.pack(fill="x")

        # 初始化
        self._tl_current_date = date.today()
        self._tl_update()

    def _tl_update(self):
        from storage.db import get_date_summary, get_date_activity_segments
        from collections import Counter
        from datetime import datetime as _dt

        d = self._tl_current_date
        self._tl_date_label.configure(text=d.strftime("%Y / %m / %d  %a"))

        summary = get_date_summary(d)
        self._tl_card_clicks.set_value(str(summary["total_clicks"]))
        self._tl_card_keys.set_value(str(summary["total_keys"]))
        self._tl_card_time.set_value(_format_duration(summary["active_seconds"]))

        segs = get_date_activity_segments(d)
        self._tl_timeline.redraw(segs)
        self._tl_dist.redraw(segs)

        for w in self._tl_list_frame.winfo_children():
            w.destroy()

        if not segs:
            ctk.CTkLabel(self._tl_list_frame, text="-- NO DATA --",
                         font=("Consolas", 10), text_color=TEXT_DIM).pack(pady=20)
            self._tl_card_top.set_value("—")
            return

        # TOP ACTIVITY
        counts = Counter()
        for s in segs:
            counts[s["activity_type"]] += 1
        top_act = max(counts, key=counts.get)
        self._tl_card_top.set_value(ACTIVITY_LABELS.get(top_act, top_act))

        # 列表表头
        hdr = ctk.CTkFrame(self._tl_list_frame, fg_color=BG_SECONDARY, height=22)
        hdr.pack(fill="x")
        for i, t in enumerate(["TIME", "DURATION", "ACTIVITY", "CONF"]):
            ctk.CTkLabel(hdr, text=t, font=("Consolas", 8, "bold"),
                         text_color=TEXT_DIM, width=70 if i < 2 else 80).pack(side="left", padx=4)

        for s in segs[-50:]:
            start_str = _dt.fromtimestamp(s["start_time"]).strftime("%H:%M")
            end_str = _dt.fromtimestamp(s["end_time"]).strftime("%H:%M")
            dur = int((s["end_time"] - s["start_time"]) / 60)
            act = s["activity_type"]
            label = ACTIVITY_LABELS.get(act, act)
            color = ACTIVITY_COLORS.get(act, TEXT_SECONDARY)

            row = ctk.CTkFrame(self._tl_list_frame, fg_color="transparent", height=20)
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"{start_str}-{end_str}", font=("Consolas", 9),
                         text_color=TEXT_SECONDARY, width=70).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=f"{dur}m", font=("Consolas", 9),
                         text_color=TEXT_DIM, width=70).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=label, font=("Microsoft YaHei", 9),
                         text_color=color, width=80).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=f"{s.get('confidence',0):.0%}" if s.get('confidence',0) > 0 else "",
                         font=("Consolas", 9), text_color=TEXT_DIM, width=80).pack(side="left", padx=4)

    def _tl_prev_day(self):
        self._tl_current_date -= timedelta(days=1)
        self._tl_update()

    def _tl_next_day(self):
        self._tl_current_date += timedelta(days=1)
        if self._tl_current_date > date.today():
            self._tl_current_date = date.today()
        self._tl_update()

    def _tl_goto_today(self):
        self._tl_current_date = date.today()
        self._tl_update()

    # ---------- 设置 ----------

    def _build_settings(self):
        container = ctk.CTkScrollableFrame(self._tab_settings, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=PAD_MEDIUM, pady=PAD_MEDIUM)

        # 采集控制
        grp1 = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=RADIUS,
                            border_width=1, border_color=BORDER_COLOR)
        grp1.pack(fill="x", pady=(0, PAD_MEDIUM))

        ctk.CTkLabel(grp1, text="采集控制", font=size_md(),
                     text_color=ACCENT_CYAN).pack(anchor="w", padx=PAD_MEDIUM, pady=(PAD_MEDIUM, 4))

        ctrl_frame = ctk.CTkFrame(grp1, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=PAD_MEDIUM, pady=PAD_MEDIUM)

        self._start_btn = ctk.CTkButton(ctrl_frame, text="▶ 启动采集",
                                        fg_color=ACCENT_GREEN, hover_color="#00c853",
                                        text_color="#000000", font=size_sm(),
                                        command=self._toggle_collector)
        self._start_btn.pack(side="left", padx=(0, 8))

        self._pause_btn = ctk.CTkButton(ctrl_frame, text="⏸ 暂停采集",
                                        fg_color=ACCENT_AMBER, hover_color="#ff8f00",
                                        text_color="#000000", font=size_sm(),
                                        state="disabled", command=self._toggle_collector)
        self._pause_btn.pack(side="left")

        # 刷新间隔
        refresh_row = ctk.CTkFrame(grp1, fg_color="transparent")
        refresh_row.pack(fill="x", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))
        ctk.CTkLabel(refresh_row, text="仪表盘刷新", font=size_sm(),
                     text_color=TEXT_SECONDARY).pack(side="left")
        self._refresh_interval_combo = ctk.CTkComboBox(
            refresh_row, width=80, height=24, font=("Microsoft YaHei", 9),
            values=["1秒","2秒","5秒","10秒","30秒"],
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            button_color=ACCENT_CYAN, button_hover_color="#00a8cc",
            dropdown_fg_color=BG_CARD,
            command=lambda e: self._on_refresh_interval_change()
        )
        self._refresh_interval_combo.set("2秒")
        self._refresh_interval_combo.pack(side="left", padx=(4, 0))

        # 开机自启
        start_row = ctk.CTkFrame(grp1, fg_color="transparent")
        start_row.pack(fill="x", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))
        self._autostart_var = ctk.BooleanVar(value=self._is_autostart_enabled())
        ctk.CTkCheckBox(start_row, text="开机自动启动", variable=self._autostart_var,
                        font=size_sm(), text_color=TEXT_PRIMARY,
                        fg_color=ACCENT_CYAN, hover_color=ACCENT_CYAN,
                        command=self._toggle_autostart).pack(side="left")

        # 隐私
        grp2 = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=RADIUS,
                            border_width=1, border_color=BORDER_COLOR)
        grp2.pack(fill="x", pady=(0, PAD_MEDIUM))

        ctk.CTkLabel(grp2, text="隐私设置", font=size_md(),
                     text_color=ACCENT_CYAN).pack(anchor="w", padx=PAD_MEDIUM, pady=(PAD_MEDIUM, 4))

        self._coord_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(grp2, text="记录鼠标坐标（更精确但涉及位置隐私）",
                        variable=self._coord_var,
                        font=size_sm(), text_color=TEXT_PRIMARY,
                        fg_color=ACCENT_CYAN, hover_color=ACCENT_CYAN).pack(
            anchor="w", padx=PAD_MEDIUM, pady=PAD_SMALL)
        ctk.CTkButton(grp2, text="切换浅色/深色主题", font=size_sm(),
                      fg_color="transparent", text_color=ACCENT_CYAN,
                      border_width=1, border_color=BORDER_COLOR,
                      hover_color=BG_CARD_HOVER, width=140, height=26,
                      command=self._toggle_theme).pack(anchor="w", padx=PAD_MEDIUM, pady=(0, PAD_SMALL))

        ctk.CTkLabel(grp2,
                     text="⚠ 采集的数据全部保存在本地，不会上传到网络",
                     font=("Microsoft YaHei", 10), text_color=TEXT_DIM).pack(
            anchor="w", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))

        # 数据管理
        grp3 = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=RADIUS,
                            border_width=1, border_color=BORDER_COLOR)
        grp3.pack(fill="x", pady=(0, PAD_MEDIUM))

        ctk.CTkLabel(grp3, text="数据管理", font=size_md(),
                     text_color=ACCENT_CYAN).pack(anchor="w", padx=PAD_MEDIUM, pady=(PAD_MEDIUM, 4))

        ctk.CTkLabel(grp3,
                     text=f"原始事件保留 {RAW_EVENT_RETENTION_DAYS} 天 · 聚合数据保留 1 年（自动清理）",
                     font=size_sm(), text_color=TEXT_SECONDARY).pack(
            anchor="w", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))

        ctk.CTkButton(grp3, text="清空今日数据",
                      fg_color=ACCENT_RED, hover_color="#d32f2f",
                      font=size_sm(), command=self._clear_today).pack(
            anchor="w", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))

        # 定时提醒
        grp_r = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=RADIUS,
                             border_width=1, border_color=BORDER_COLOR)
        grp_r.pack(fill="x", pady=(0, PAD_MEDIUM))

        ctk.CTkLabel(grp_r, text="定时弹出询问", font=size_md(),
                     text_color=ACCENT_CYAN).pack(anchor="w", padx=PAD_MEDIUM, pady=(PAD_MEDIUM, 4))

        row1 = ctk.CTkFrame(grp_r, fg_color="transparent")
        row1.pack(fill="x", padx=PAD_MEDIUM)

        self._reminder_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text="启用", variable=self._reminder_var,
                        font=size_sm(), text_color=TEXT_PRIMARY,
                        fg_color=ACCENT_CYAN, hover_color=ACCENT_CYAN,
                        command=self._toggle_reminder).pack(side="left")

        ctk.CTkLabel(row1, text="每隔", font=size_sm(),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(PAD_MEDIUM, 4))

        self._reminder_combo = ctk.CTkComboBox(row1, values=["5分钟","10分钟","20分钟","30分钟","1小时","自定义"],
                                                 width=100, font=size_sm(),
                                                 fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
                                                 button_color=ACCENT_CYAN, button_hover_color="#00a8cc",
                                                 dropdown_fg_color=BG_CARD)
        self._reminder_combo.set("10分钟")
        self._reminder_combo.pack(side="left")
        self._reminder_combo.bind("<<ComboboxSelected>>", lambda e: self._on_reminder_change())

        self._reminder_custom_entry = ctk.CTkEntry(row1, placeholder_text="分钟", width=60,
                                                     font=size_sm(), fg_color=BG_SECONDARY,
                                                     border_color=BORDER_COLOR)
        # 只有选择"自定义"时才显示

        ctk.CTkLabel(grp_r,
                     text="到时间弹出小窗询问你刚才在做什么，帮助训练个性化模型",
                     font=("Microsoft YaHei", 10), text_color=TEXT_DIM).pack(
            anchor="w", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))

        # 自定义活动
        grp_ca = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=RADIUS,
                              border_width=1, border_color=BORDER_COLOR)
        grp_ca.pack(fill="x", pady=(0, PAD_MEDIUM))

        ctk.CTkLabel(grp_ca, text="自定义活动", font=size_md(),
                     text_color=ACCENT_CYAN).pack(anchor="w", padx=PAD_MEDIUM, pady=(PAD_MEDIUM, 4))

        ca_row = ctk.CTkFrame(grp_ca, fg_color="transparent")
        ca_row.pack(fill="x", padx=PAD_MEDIUM, pady=(0, PAD_SMALL))

        self._ca_entry = ctk.CTkEntry(ca_row, placeholder_text="输入活动名称...",
                                        font=size_sm(), fg_color=BG_SECONDARY,
                                        border_color=BORDER_COLOR)
        self._ca_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(ca_row, text="添加", width=50,
                      font=size_sm(), fg_color=ACCENT_CYAN, text_color="#080808",
                      command=self._add_custom_activity).pack(side="left")

        self._ca_list_frame = ctk.CTkFrame(grp_ca, fg_color="transparent")
        self._ca_list_frame.pack(fill="x", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))
        self._refresh_ca_list()

        # 关于
        grp4 = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=RADIUS,
                            border_width=1, border_color=BORDER_COLOR)
        grp4.pack(fill="x")

        ctk.CTkLabel(grp4, text="关于", font=size_md(),
                     text_color=ACCENT_CYAN).pack(anchor="w", padx=PAD_MEDIUM, pady=(PAD_MEDIUM, 4))
        ctk.CTkLabel(grp4, text="InputMonitor v1.0 · 基于输入行为推断活动状态",
                     font=size_sm(), text_color=TEXT_DIM).pack(
            anchor="w", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))
        ctk.CTkLabel(grp4,
                     text="不记录按键具体内容，不联网，所有数据存储在本地",
                     font=("Microsoft YaHei", 10), text_color=TEXT_DIM).pack(
            anchor="w", padx=PAD_MEDIUM, pady=(0, PAD_MEDIUM))

    # ================================================================
    # 活动列表（预定义 + 自定义）
    # ================================================================

    PREDEFINED_ACTIVITIES = [
        ("coding","💻 编码"), ("writing","✍️ 写作"), ("chatting","💬 聊天"),
        ("browsing","🌐 浏览"), ("reading","📖 阅读"),
        ("gaming","🎮 游戏"), ("idle","💤 空闲"), ("mixed","🔄 混合"),
    ]

    def _get_activity_list(self) -> list[tuple[str, str]]:
        """获取所有活动列表（预定义 + 自定义）"""
        from storage.db import get_custom_activities
        acts = list(self.PREDEFINED_ACTIVITIES)
        for ca in get_custom_activities():
            acts.append((ca["name"], ca["name"]))
        return acts

    def _rebuild_label_bar(self):
        """重建快速标注栏"""
        import customtkinter as ctk
        for w in self._label_bar.winfo_children():
            w.destroy()

        # 时间选择器（改成时长）
        ctk.CTkLabel(self._label_bar, text="标注", font=size_sm(),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 2))

        self._label_time_combo = ctk.CTkComboBox(self._label_bar, width=90, height=24,
                                                   font=("Microsoft YaHei", 9),
                                                   values=["最近5分钟","最近10分钟","最近15分钟","最近30分钟"],
                                                   fg_color=BG_SECONDARY,
                                                   border_color=BORDER_COLOR,
                                                   button_color=ACCENT_CYAN,
                                                   button_hover_color="#00a8cc",
                                                   dropdown_fg_color=BG_CARD)
        self._label_time_combo.set("最近5分钟")
        self._label_time_combo.pack(side="left", padx=(0, 4))

        ctk.CTkLabel(self._label_bar, text="在做什么:", font=size_sm(),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 4))

        # 预定义 + 自定义活动按钮
        for act_id, act_name in self._get_activity_list():
            color = ACTIVITY_COLORS.get(act_id, "#8892b0")
            btn = ctk.CTkButton(self._label_bar, text=act_name, width=70, height=24,
                            font=("Microsoft YaHei", 9),
                            fg_color=color, hover_color=BG_CARD_HOVER,
                            text_color="#ffffff",
                            command=lambda aid=act_id: self._do_label(aid))
            btn.pack(side="left", padx=2)


        # "+" 按钮：直接添加自定义活动
        ctk.CTkButton(self._label_bar, text="+", width=26, height=24,
                      font=("Microsoft YaHei", 14, "bold"),
                      fg_color=BG_CARD, text_color=ACCENT_CYAN,
                      border_width=1, border_color=BORDER_COLOR,
                      hover_color=BG_CARD_HOVER,
                      command=self._show_inline_ca_entry).pack(side="left", padx=2)

        self._label_feedback = ctk.CTkLabel(self._label_bar, text="", font=("Microsoft YaHei", 9),
                                            text_color=ACCENT_GREEN)
        self._label_feedback.pack(side="left", padx=(PAD_MEDIUM, 0))

        self._labeled_count = ctk.CTkLabel(self._label_bar, text="已标注: 0",
                                           font=("Consolas", 9), text_color=TEXT_DIM)
        self._labeled_count.pack(side="right")

        # 内联添加自定义活动的输入框（默认隐藏）
        self._inline_ca_entry = ctk.CTkEntry(self._label_bar, placeholder_text="活动名称回车添加...",
                                               width=120, height=24,
                                               font=("Microsoft YaHei", 9),
                                               fg_color=BG_SECONDARY,
                                               border_color=ACCENT_CYAN)
        self._inline_ca_entry.bind("<Return>", lambda e: self._confirm_inline_ca())

    def _show_inline_ca_entry(self):
        """显示内联自定义活动输入框"""
        self._inline_ca_entry.pack(side="left", padx=(2, 4))
        self._inline_ca_entry.focus_force()
        self._inline_ca_entry.delete(0, "end")

    def _confirm_inline_ca(self):
        """确认内联添加自定义活动"""
        name = self._inline_ca_entry.get().strip()
        if name:
            from storage.db import add_custom_activity
            if add_custom_activity(name):
                self._rebuild_label_bar()
                self._label_feedback.configure(text=f"✅ 已添加: {name}", text_color=ACCENT_GREEN)
                self.after(2000, lambda: self._label_feedback.configure(text=""))
        self._inline_ca_entry.pack_forget()

    # ================================================================
    # 采集控制
    # ================================================================

    def _auto_start(self):
        """启动时自动开始采集"""
        self._collector_running = True
        self._start_collector()
        self._status_dot.configure(text_color=ACCENT_GREEN)
        self._status_label.configure(text="运行中")

    def _toggle_collector(self):
        """启动/暂停采集"""
        if self._collector_running:
            # 暂停
            self._collector_running = False
            from collector.listener import InputCollector
            if hasattr(self, "_ic") and self._ic:
                self._ic.stop()
            self._status_dot.configure(text_color=ACCENT_AMBER)
            self._status_label.configure(text="已暂停")
            self._start_btn.configure(state="normal", text="▶ 启动采集")
            self._pause_btn.configure(state="disabled")
        else:
            # 启动
            self._collector_running = True
            self._start_collector()
            self._status_dot.configure(text_color=ACCENT_GREEN)
            self._status_label.configure(text="运行中")
            self._start_btn.configure(state="disabled")
            self._pause_btn.configure(state="normal", text="⏸ 暂停采集")

    def _is_autostart_enabled(self) -> bool:
        """检查开机自启是否已开启"""
        import os
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        lnk = os.path.join(startup, "InputMonitor.lnk")
        return os.path.exists(lnk)

    def _toggle_autostart(self):
        """开关开机自启（优先用打包 exe）"""
        import os, subprocess
        project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        lnk = os.path.join(startup, "InputMonitor.lnk")

        if self._autostart_var.get():
            exe_path = os.path.join(project, "dist", "InputMonitor", "InputMonitor.exe")
            if os.path.exists(exe_path):
                target = exe_path
                args = ""
                wd = os.path.dirname(exe_path)
            else:
                target = "pythonw.exe"
                args = os.path.join(project, "main.py")
                wd = project
            ps = f'''
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("{lnk}")
$sc.TargetPath = "{target}"
$sc.Arguments = "{args}"
$sc.WorkingDirectory = "{wd}"
$sc.Save()
'''
            subprocess.run(["powershell", "-Command", ps], capture_output=True)
        else:
            if os.path.exists(lnk):
                os.remove(lnk)

    def _start_collector(self):
        """在后台线程启动采集 + 后台处理"""
        from collector.listener import InputCollector
        self._ic = InputCollector()
        self._ic.start()
        self._start_processor()

    def _toggle_theme(self):
        """切换深色/浅色主题"""
        self._theme_mode = "light" if self._theme_mode == "dark" else "dark"
        ctk.set_appearance_mode("Light" if self._theme_mode == "light" else "Dark")

    def _lazy_init(self):
        """窗口显示后延迟加载的非关键初始化"""
        self._theme_mode = "dark"
        from storage.db import cleanup_old_data
        cleanup_old_data()
        self._start_reminder()
        self._setup_tray()

    def _start_processor(self):
        """后台线程：每 10 秒处理一次特征窗口"""
        def _loop():
            import time as _time
            while self._collector_running:
                try:
                    self._process_windows()
                except Exception:
                    pass
                _time.sleep(10)
        import threading
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    # ================================================================
    # 刷新循环
    # ================================================================

    def _add_custom_activity(self):
        name = self._ca_entry.get().strip()
        if not name:
            return
        from storage.db import add_custom_activity
        if add_custom_activity(name):
            self._ca_entry.delete(0, "end")
            self._refresh_ca_list()
            self._rebuild_label_bar()
            self._label_feedback.configure(text=f"✅ 已添加: {name}", text_color=ACCENT_GREEN)
            self.after(2000, lambda: self._label_feedback.configure(text=""))

    def _remove_custom_activity(self, name: str):
        from storage.db import remove_custom_activity
        remove_custom_activity(name)
        self._refresh_ca_list()
        self._rebuild_label_bar()
        self._label_feedback.configure(text=f"已删除: {name}", text_color=ACCENT_GREEN)
        self.after(2000, lambda: self._label_feedback.configure(text=""))

    def _refresh_ca_list(self):
        """刷新自定义活动列表 UI"""
        import customtkinter as ctk
        for w in self._ca_list_frame.winfo_children():
            w.destroy()
        from storage.db import get_custom_activities
        for ca in get_custom_activities():
            row = ctk.CTkFrame(self._ca_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"  {ca['name']}", font=size_sm(),
                         text_color=TEXT_PRIMARY).pack(side="left")
            ctk.CTkButton(row, text="✕", width=22, height=22,
                         font=("Consolas", 9), fg_color="transparent",
                         text_color=ACCENT_RED, hover=False,
                         command=lambda n=ca["name"]: self._remove_custom_activity(n)
                         ).pack(side="right")

    def _do_label(self, label: str):
        """标注选定时长内的最近一个窗口"""
        from storage.db import get_unlabeled_windows, insert_label, get_labeled_count
        import time

        # 用户选的时长（分钟）
        sel = self._label_time_combo.get()
        minutes = {"最近5分钟":5, "最近10分钟":10, "最近15分钟":15, "最近30分钟":30}.get(sel, 5)
        cutoff = time.time() - minutes * 60

        wins = get_unlabeled_windows(20)
        match = [w for w in wins if w["start_time"] >= cutoff]
        if not match:
            self._label_feedback.configure(text=f"{minutes}分钟内无未标注窗口", text_color=ACCENT_AMBER)
            self.after(2000, lambda: self._label_feedback.configure(text=""))
            return
        w = match[0]  # 取最近的一个

        insert_label(w["start_time"], label)
        cnt = get_labeled_count()
        if not wins:
            self._label_feedback.configure(text="没有可标注的窗口", text_color=ACCENT_AMBER)
            self.after(2000, lambda: self._label_feedback.configure(text=""))
            return
        w = wins[0]
        insert_label(w["start_time"], label)
        cnt = get_labeled_count()
        self._labeled_count.configure(text=f"已标注: {cnt}")
        self._label_feedback.configure(text=f"✅ 已标记为 {ACTIVITY_LABELS.get(label, label)}",
                                        text_color=ACCENT_GREEN)
        self.after(3000, lambda: self._label_feedback.configure(text=""))

    def _get_refresh_interval_ms(self) -> int:
        val = self._refresh_interval_combo.get()
        return {"1秒": 1000, "2秒": 2000, "5秒": 5000, "10秒": 10000, "30秒": 30000}.get(val, 2000)

    def _on_refresh_interval_change(self):
        pass  # 下次自动刷新就会用新间隔

    def _manual_refresh(self):
        """手动刷新 —— 点击按钮触发"""
        self._refresh_data()

    def _check_show_signal(self):
        """检查信号文件 → 显示窗口"""
        import os
        signal = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".show.signal")
        if os.path.exists(signal):
            try:
                with open(signal) as f:
                    if f.read().strip() == "show":
                        self._show_window()
                os.remove(signal)
            except:
                pass

    def _schedule_refresh(self):
        """定时刷新仪表盘"""
        try:
            self._refresh_data()
            self._check_show_signal()
        finally:
            ms = self._get_refresh_interval_ms()
            self.after(ms, self._schedule_refresh)

    def _refresh_data(self):
        """从数据库读取最新数据并刷新 UI"""
        try:
            # --- 引擎：检查并处理新的特征窗口 ---
            self._process_windows()

            # --- 实时原始计数（不等特征窗口，立刻显示） ---
            raw = get_raw_counts()
            raw_clicks = raw["clicks"]
            raw_keys = raw["keys"]

            # --- 用实时原始计数（不等特征窗口，立刻显示） ---
            self._card_clicks.set_value(str(raw_clicks))
            self._card_keys.set_value(str(raw_keys))
            self._card_time.set_value(_format_duration(raw.get("active_seconds", 0)))

            # --- 当前活动 ---
            latest = get_latest_activity()
            if latest:
                self._card_activity.update(latest, confidence=0.7)
            elif raw_clicks > 0 or raw_keys > 0:
                self._card_activity.update("mixed", confidence=0.3)

            # --- 时间线 ---
            segments = get_today_activity_segments()
            self._timeline.redraw(segments)

            # --- 活动分布（用已标注+已分类的段） ---
            self._distribution.redraw(segments)

            # --- 更新状态标签 ---
            now_str = datetime.now().strftime("%H:%M:%S")
            self._updated_label.configure(text="● 自动刷新中", text_color=ACCENT_GREEN)
            self._last_update.configure(text=f"最后更新: {now_str}")

        except Exception as e:
            # 写入错误日志到桌面
            import traceback
            traceback.print_exc()
            self._updated_label.configure(text=f"⚠ 刷新失败", text_color=ACCENT_RED)
            self._last_update.configure(text=str(e)[:60])

    def _process_windows(self):
        """轻量处理新窗口"""
        now = time.time()
        last_done = get_latest_activity_start()
        window_size = WINDOW_SIZE_SEC

        if last_done is None:
            # 首次：只处理最近一个完整窗口
            recent_start = int(now / window_size) * window_size - window_size
            today_0 = datetime.combine(date.today(), datetime.min.time()).timestamp()
            if recent_start >= today_0:
                self._process_one_window(recent_start, recent_start + window_size)
        else:
            # 处理后续的完整窗口
            next_start = int(last_done / window_size) * window_size + window_size
            while next_start + window_size <= now:
                self._process_one_window(next_start, next_start + window_size)
                next_start += window_size

    def _process_one_window(self, start: float, end: float):
        """处理单个时间窗口：提取特征 + 分类（避免重复插入）"""
        from storage.db import _get_conn, insert_activity_segment

        # 跳过已经有活动段的窗口
        existing = _get_conn().execute(
            "SELECT id FROM activity_segments WHERE start_time=?",
            (start,)
        ).fetchone()
        if existing:
            return

        extract_and_save_features(start, end)

        from storage.db import get_events_in_range
        from engine.classifier import classify_window
        from engine.classifier import Features

        events = get_events_in_range(start, end)
        clicks = sum(1 for e in events if e["event_type"] == "mouse_click")
        keys = sum(1 for e in events if e["event_type"] == "key_down")
        scroll = sum(1 for e in events if e["event_type"] == "mouse_scroll")
        letters = sum(1 for e in events if e.get("button") == "letter")
        modifiers = sum(1 for e in events if e.get("button") == "modifier")
        wasd = sum(1 for e in events if e.get("key_char") in ("w","a","s","d"))
        arrow = sum(1 for e in events if e.get("button")=="nav" and e.get("key_char") in ("up","down","left","right"))
        backspace = sum(1 for e in events if e.get("key_char")=="backspace")
        enter = sum(1 for e in events if e.get("key_char")=="enter")
        space = sum(1 for e in events if e.get("key_char")=="space")
        ctrl_cv = sum(1 for e in events if e.get("key_char") in ("ctrl_c","ctrl_v"))

        active_sec = (end - start) if (keys + clicks) > 0 else 0
        f = Features(
            clicks_total=clicks, key_presses=keys,
            key_letter=letters, key_modifier=modifiers,
            key_wasd=wasd, key_arrow=arrow,
            key_backspace=backspace, key_enter=enter,
            key_space=space, key_ctrl_cv=ctrl_cv,
            scroll_distance=scroll,
            active_seconds=active_sec,
        )
        activity, conf = classify_window(f)

        insert_activity_segment({
            "start_time": start,
            "end_time": end,
            "activity_type": activity,
            "confidence": conf,
        })

    # ================================================================
    # 清理
    # ================================================================

    def _clear_today(self):
        """清空今日数据"""
        from storage.db import _get_conn
        conn = _get_conn()
        today_0 = datetime.combine(date.today(), datetime.min.time()).timestamp()
        conn.execute("DELETE FROM raw_events WHERE ts >= ?", (today_0,))
        conn.execute("DELETE FROM feature_windows WHERE window_start >= ?", (today_0,))
        conn.execute("DELETE FROM activity_segments WHERE start_time >= ?", (today_0,))
        conn.commit()
        self._refresh_data()

    # ================================================================
    # 关闭
    # ================================================================

    def _setup_tray(self):
        """创建系统托盘图标"""
        # 生成图标
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=ACCENT_CYAN, outline="#ffffff", width=3)
        draw.ellipse([18, 18, 46, 46], fill="#ffffff")

        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", lambda: self.after(0, self._show_window)),
            pystray.MenuItem("隐藏", lambda: self.after(0, self._hide_window)),
            pystray.MenuItem("退出", lambda: self.after(0, self._quit_app)),
        )
        self._tray_icon = pystray.Icon("InputMonitor", img, "InputMonitor", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _hide_window(self):
        self.withdraw()

    def _quit_app(self):
        """彻底退出"""
        self._tray_icon.stop()
        if hasattr(self, "_ic") and self._ic:
            self._ic.stop()
        if hasattr(self, "_cleanup_lock"):
            self._cleanup_lock()
        self.destroy()
        self.quit()

    def _on_close(self):
        """关闭窗口 → 隐藏到系统托盘"""
        self.withdraw()

    # ================================================================
    # 定时弹窗提醒
    # ================================================================

    def _start_reminder(self):
        """启动定时提醒循环"""
        if not self._reminder_var.get():
            return
        sec = self._get_reminder_seconds()
        self.after(sec * 1000, self._show_reminder_popup)

    def _get_reminder_seconds(self) -> int:
        """获取提醒间隔秒数"""
        val = self._reminder_combo.get()
        if val == "自定义":
            try:
                return int(self._reminder_custom_entry.get()) * 60
            except:
                return 600  # 默认10分钟
        return {
            "5分钟": 300, "10分钟": 600, "20分钟": 1200,
            "30分钟": 1800, "1小时": 3600,
        }.get(val, 600)

    def _toggle_reminder(self):
        if self._reminder_var.get():
            self._start_reminder()

    def _on_reminder_change(self):
        if self._reminder_combo.get() == "自定义":
            self._reminder_custom_entry.pack(side="left", padx=(4, 0))
        else:
            self._reminder_custom_entry.pack_forget()

    def _show_reminder_popup(self):
        """弹出询问窗口"""
        if not self._reminder_var.get():
            return

        interval_min = self._get_reminder_seconds() // 60
        win = ctk.CTkToplevel(self)
        win.title("行为记录")
        win.geometry("420x320")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        win.transient(self)
        win.grab_set()
        win.focus_force()

        # 居中
        self.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - 420) // 2
        py = self.winfo_y() + (self.winfo_height() - 320) // 2
        win.geometry(f"+{px}+{py}")

        # 内容
        frame = ctk.CTkFrame(win, fg_color=BG_CARD)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frame, text=f"过去 {interval_min} 分钟你在做什么？",
                     font=("Microsoft YaHei", 16, "bold"), text_color=ACCENT_CYAN).pack(pady=(16, 4))
        ctk.CTkLabel(frame, text="点击下方按钮记录你的活动，帮助训练模型",
                     font=("Microsoft YaHei", 10), text_color=TEXT_DIM).pack(pady=(0, 12))

        # 活动按钮
        acts = self._get_activity_list()
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=6)
        for i, (aid, aname) in enumerate(acts):
            r, c_pos = divmod(i, 4)
            btn = ctk.CTkButton(btn_frame, text=aname, width=80, height=30,
                                font=("Microsoft YaHei", 10),
                                fg_color=ACTIVITY_COLORS.get(aid, "#8892b0"),
                                hover_color=BG_CARD_HOVER, text_color="#ffffff",
                                command=lambda a=aid, w=win: self._reminder_done(w, a))
            btn.grid(row=r, column=c_pos, padx=3, pady=3)

        # 自定义输入
        ctk.CTkLabel(frame, text="或自定义:", font=size_sm(),
                     text_color=TEXT_SECONDARY).pack(pady=(6, 0))
        entry_frame = ctk.CTkFrame(frame, fg_color="transparent")
        entry_frame.pack(fill="x", padx=20)
        custom_entry = ctk.CTkEntry(entry_frame, placeholder_text="例如: 开会、看视频...",
                                     font=size_sm(), fg_color=BG_SECONDARY,
                                     border_color=BORDER_COLOR)
        custom_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(entry_frame, text="确定", width=50,
                      font=size_sm(), fg_color=ACCENT_CYAN, text_color="#080808",
                      command=lambda: self._reminder_done(win, custom_entry.get() or "other")
                      ).pack(side="right")

        # 跳过
        skip_frame = ctk.CTkFrame(frame, fg_color="transparent")
        skip_frame.pack(pady=(6, 0))
        ctk.CTkButton(skip_frame, text="跳过", width=60, height=22,
                      font=("Microsoft YaHei", 9), fg_color="transparent",
                      text_color=TEXT_DIM, hover=False,
                      command=lambda: self._reminder_skip(win)).pack()

    def _reminder_done(self, win, label: str):
        """标记并关闭弹窗"""
        from storage.db import insert_label, get_labeled_count
        import time
        now = time.time()
        window_start = int(now / 300) * 300
        insert_label(window_start, label)
        cnt = get_labeled_count()
        self._labeled_count.configure(text=f"已标注: {cnt}")
        self._label_feedback.configure(text=f"✅ {label}", text_color=ACCENT_GREEN)
        self.after(3000, lambda: self._label_feedback.configure(text=""))
        win.destroy()
        # 安排下一次
        self._start_reminder()

    def _reminder_skip(self, win):
        win.destroy()
        self._start_reminder()
