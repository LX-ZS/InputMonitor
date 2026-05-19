"""
CustomTkinter acrylic-style reusable widgets for InputMonitor.

这些组件只负责视觉，不处理采集、分类、数据库逻辑。
"""

from __future__ import annotations

try:
    import customtkinter as ctk
except Exception as exc:  # pragma: no cover
    raise RuntimeError("需要安装 customtkinter：pip install customtkinter") from exc

from .style_tokens import get_palette, RADIUS, SPACING, FONT, activity_color


class ThemeController:
    def __init__(self, root, initial: str = "dark"):
        self.root = root
        self.mode = initial if initial in ("dark", "light") else "dark"
        ctk.set_appearance_mode("Dark" if self.mode == "dark" else "Light")

    def toggle(self) -> str:
        self.mode = "light" if self.mode == "dark" else "dark"
        ctk.set_appearance_mode("Dark" if self.mode == "dark" else "Light")
        return self.mode

    @property
    def palette(self) -> dict:
        return get_palette(self.mode)


class AcrylicCard(ctk.CTkFrame):
    def __init__(self, master, mode: str = "dark", **kwargs):
        p = get_palette(mode)
        super().__init__(
            master,
            fg_color=p["card"],
            border_color=p["border"],
            border_width=1,
            corner_radius=RADIUS["lg"],
            **kwargs,
        )
        self.mode = mode

    def set_mode(self, mode: str):
        self.mode = mode
        p = get_palette(mode)
        self.configure(fg_color=p["card"], border_color=p["border"])


class MetricCard(AcrylicCard):
    def __init__(self, master, title: str, value: str, icon: str = "", mode: str = "dark", accent: str | None = None):
        super().__init__(master, mode=mode)
        p = get_palette(mode)
        self.accent = accent or p["accent"]

        self.icon_label = ctk.CTkLabel(
            self,
            text=icon,
            font=(FONT["family"], 22),
            text_color=self.accent,
        )
        self.icon_label.grid(row=0, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["lg"], 0))

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=(FONT["family"], FONT["small"]),
            text_color=p["muted"],
        )
        self.title_label.grid(row=1, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["sm"], 0))

        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=(FONT["family"], FONT["metric"], "bold"),
            text_color=p["text"],
        )
        self.value_label.grid(row=2, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["lg"]))

    def update_value(self, value: str):
        self.value_label.configure(text=value)

    def set_mode(self, mode: str):
        super().set_mode(mode)
        p = get_palette(mode)
        self.title_label.configure(text_color=p["muted"])
        self.value_label.configure(text_color=p["text"])


class NavButton(ctk.CTkButton):
    def __init__(self, master, text: str, command=None, mode: str = "dark", selected: bool = False):
        p = get_palette(mode)
        super().__init__(
            master,
            text=text,
            command=command,
            height=42,
            corner_radius=RADIUS["md"],
            fg_color=p["accent"] if selected else "transparent",
            hover_color=p["card_hover"],
            text_color="#FFFFFF" if selected else p["text"],
            anchor="w",
        )
        self.mode = mode
        self.selected = selected

    def set_selected(self, selected: bool):
        self.selected = selected
        p = get_palette(self.mode)
        self.configure(
            fg_color=p["accent"] if selected else "transparent",
            text_color="#FFFFFF" if selected else p["text"],
        )

    def set_mode(self, mode: str):
        self.mode = mode
        p = get_palette(mode)
        self.configure(
            fg_color=p["accent"] if self.selected else "transparent",
            hover_color=p["card_hover"],
            text_color="#FFFFFF" if self.selected else p["text"],
        )


class ActivityPill(ctk.CTkButton):
    def __init__(self, master, activity: str, text: str | None = None, command=None):
        color = activity_color(activity)
        super().__init__(
            master,
            text=text or activity,
            command=command,
            height=34,
            corner_radius=RADIUS["pill"],
            fg_color=color,
            hover_color=color,
            text_color="#FFFFFF",
        )
        self.activity = activity
