"""
InputMonitor UI 美化示例。

运行：
    python examples/inputmonitor_ui_demo.py

说明：
    这是独立可运行的界面示例，用于展示主题切换、亚克力卡片和统一按钮风格。
    它不包含真实采集逻辑，不会读写你的数据库。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import customtkinter as ctk
except Exception:
    raise SystemExit("缺少 customtkinter，请先运行：pip install customtkinter")

from ui.style_tokens import get_palette, SPACING, FONT, ACTIVITY_COLORS
from ui.acrylic_widgets import ThemeController, MetricCard, AcrylicCard, NavButton, ActivityPill


class InputMonitorDemo(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.theme = ThemeController(self, "dark")
        self.title("InputMonitor - Acrylic UI Demo")
        self.geometry("1120x720")
        self.minsize(980, 640)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.main = ctk.CTkFrame(self, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.main.grid_rowconfigure(2, weight=1)

        self._build_sidebar()
        self._build_dashboard()
        self.apply_mode()

    def _build_sidebar(self):
        self.logo = ctk.CTkLabel(self.sidebar, text="InputMonitor", font=(FONT["family"], 24, "bold"))
        self.logo.pack(anchor="w", padx=20, pady=(24, 18))

        self.nav_dashboard = NavButton(self.sidebar, "  仪表盘", selected=True)
        self.nav_timeline = NavButton(self.sidebar, "  时间线")
        self.nav_settings = NavButton(self.sidebar, "  设置")
        self.nav_dashboard.pack(fill="x", padx=14, pady=4)
        self.nav_timeline.pack(fill="x", padx=14, pady=4)
        self.nav_settings.pack(fill="x", padx=14, pady=4)

        self.theme_btn = ctk.CTkButton(
            self.sidebar,
            text="切换黑 / 白主题",
            command=self.toggle_theme,
            height=40,
            corner_radius=14,
        )
        self.theme_btn.pack(side="bottom", fill="x", padx=14, pady=18)

    def _build_dashboard(self):
        self.header = ctk.CTkLabel(
            self.main,
            text="今日活动概览",
            font=(FONT["family"], 28, "bold"),
            anchor="w",
        )
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(24, 8))

        self.status = ctk.CTkLabel(
            self.main,
            text="● 采集中    隐私坐标：关闭    刷新：5s",
            font=(FONT["family"], 13),
            anchor="e",
        )
        self.status.grid(row=0, column=2, columnspan=2, sticky="ew", padx=24, pady=(24, 8))

        self.cards = [
            MetricCard(self.main, "点击", "1,248", "🖱", accent=ACTIVITY_COLORS["browsing"]),
            MetricCard(self.main, "按键", "8,732", "⌨", accent=ACTIVITY_COLORS["coding"]),
            MetricCard(self.main, "活跃时间", "4h 26m", "⏱", accent=ACTIVITY_COLORS["chat"]),
            MetricCard(self.main, "当前状态", "编码", "◇", accent=ACTIVITY_COLORS["coding"]),
        ]

        for i, card in enumerate(self.cards):
            card.grid(row=1, column=i, sticky="nsew", padx=(24 if i == 0 else 8, 24 if i == 3 else 8), pady=16)

        self.timeline = AcrylicCard(self.main)
        self.timeline.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=(24, 8), pady=(0, 24))
        self.timeline.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.timeline,
            text="时间线",
            font=(FONT["family"], 18, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 8))

        for time, activity, width in [
            ("09:00 - 09:30", "coding", 0.92),
            ("09:30 - 10:00", "browsing", 0.72),
            ("10:00 - 10:30", "writing", 0.84),
            ("10:30 - 11:00", "chat", 0.58),
            ("11:00 - 11:30", "reading", 0.48),
        ]:
            row = ctk.CTkFrame(self.timeline, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=7)
            ctk.CTkLabel(row, text=time, width=120, anchor="w").pack(side="left")
            bar_bg = ctk.CTkFrame(row, height=18, corner_radius=999)
            bar_bg.pack(side="left", fill="x", expand=True, padx=8)
            bar = ctk.CTkFrame(bar_bg, height=18, width=int(520 * width), corner_radius=999, fg_color=ACTIVITY_COLORS[activity])
            bar.place(x=0, y=0)
            ctk.CTkLabel(row, text=activity, width=80, anchor="e").pack(side="right")

        self.side = AcrylicCard(self.main)
        self.side.grid(row=2, column=3, sticky="nsew", padx=(8, 24), pady=(0, 24))

        ctk.CTkLabel(
            self.side,
            text="快速标注",
            font=(FONT["family"], 18, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 10))

        for activity in ["coding", "writing", "chat", "browsing", "reading", "gaming", "idle", "mixed"]:
            ActivityPill(self.side, activity, text=activity).pack(fill="x", padx=20, pady=5)

    def toggle_theme(self):
        self.theme.toggle()
        self.apply_mode()

    def apply_mode(self):
        mode = self.theme.mode
        p = get_palette(mode)
        self.configure(fg_color=p["bg"])
        self.sidebar.configure(fg_color=p["bg_soft"])
        self.main.configure(fg_color=p["bg"])
        self.logo.configure(text_color=p["text"])
        self.header.configure(text_color=p["text"])
        self.status.configure(text_color=p["success"])
        self.theme_btn.configure(fg_color=p["accent"], hover_color=p["accent_2"])

        for nav in [self.nav_dashboard, self.nav_timeline, self.nav_settings]:
            nav.set_mode(mode)

        for card in self.cards:
            card.set_mode(mode)

        self.timeline.set_mode(mode)
        self.side.set_mode(mode)


if __name__ == "__main__":
    app = InputMonitorDemo()
    app.mainloop()
