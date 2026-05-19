"""
pynput 全局输入监听
- 鼠标：点击（左/右/中）、滚动
- 键盘：按键分类记录（不记录具体字符，只记录类别）
"""

import time
import threading

from pynput import mouse, keyboard

from collector.event_buffer import EventBuffer
from storage.db import insert_raw_events
from config import RECORD_MOUSE_COORDS


# ============ 按键分类 ============

_KEY_CATEGORY_MAP: dict = {
    # 字母 —— 通过 KeyCode 的 char 属性判断
    # 修饰键
    keyboard.Key.alt:       "modifier",
    keyboard.Key.alt_l:     "modifier",
    keyboard.Key.alt_r:     "modifier",
    keyboard.Key.alt_gr:    "modifier",
    keyboard.Key.ctrl:      "modifier",
    keyboard.Key.ctrl_l:    "modifier",
    keyboard.Key.ctrl_r:    "modifier",
    keyboard.Key.shift:     "modifier",
    keyboard.Key.shift_l:   "modifier",
    keyboard.Key.shift_r:   "modifier",
    keyboard.Key.cmd:       "modifier",
    keyboard.Key.cmd_l:     "modifier",
    keyboard.Key.cmd_r:     "modifier",
    # 导航键
    keyboard.Key.up:        "nav",
    keyboard.Key.down:      "nav",
    keyboard.Key.left:      "nav",
    keyboard.Key.right:     "nav",
    keyboard.Key.home:      "nav",
    keyboard.Key.end:       "nav",
    keyboard.Key.page_up:   "nav",
    keyboard.Key.page_down: "nav",
    # 功能键
    keyboard.Key.f1:  "function",
    keyboard.Key.f2:  "function",
    keyboard.Key.f3:  "function",
    keyboard.Key.f4:  "function",
    keyboard.Key.f5:  "function",
    keyboard.Key.f6:  "function",
    keyboard.Key.f7:  "function",
    keyboard.Key.f8:  "function",
    keyboard.Key.f9:  "function",
    keyboard.Key.f10: "function",
    keyboard.Key.f11: "function",
    keyboard.Key.f12: "function",
    keyboard.Key.f13: "function",
    keyboard.Key.f14: "function",
    keyboard.Key.f15: "function",
    keyboard.Key.f16: "function",
    keyboard.Key.f17: "function",
    keyboard.Key.f18: "function",
    keyboard.Key.f19: "function",
    keyboard.Key.f20: "function",
    keyboard.Key.f21: "function",
    keyboard.Key.f22: "function",
    keyboard.Key.f23: "function",
    keyboard.Key.f24: "function",
    # 数字小键盘（部分系统映射为单独按键）
    keyboard.Key.num_lock:  "other",
}


def _classify_key(key) -> str:
    """将按键分类为：letter / digit / modifier / nav / function / other"""
    # 修饰键 / 导航键等在映射表中的
    if isinstance(key, keyboard.Key):
        return _KEY_CATEGORY_MAP.get(key, "other")

    # KeyCode（带 char 属性）
    if hasattr(key, "char") and key.char is not None:
        ch = key.char
        if ch.isascii() and ch.isalpha():
            return "letter"
        if ch.isascii() and ch.isdigit():
            return "digit"
        # 空格、标点等归为 other
        return "other"

    return "other"


# ============ 采集控制器 ============

class InputCollector:
    """管理输入监听器的生命周期"""

    def __init__(self):
        self.buffer = EventBuffer(flush_callback=insert_raw_events)
        self._mouse_listener: mouse.Listener | None = None
        self._keyboard_listener: keyboard.Listener | None = None
        self._running = False

    # ---- 鼠标回调 ----

    def _on_click(self, x, y, button, pressed):
        if not pressed:
            return
        btn_name = getattr(button, "name", str(button))
        ev = {
            "ts": time.time(),
            "event_type": "mouse_click",
            "button": btn_name,
        }
        if RECORD_MOUSE_COORDS:
            ev["x"] = x
            ev["y"] = y
        self.buffer.push(ev)

    def _on_scroll(self, x, y, dx, dy):
        ev = {
            "ts": time.time(),
            "event_type": "mouse_scroll",
            "button": "scroll",
        }
        if RECORD_MOUSE_COORDS:
            ev["x"] = x
            ev["y"] = y
        self.buffer.push(ev)

    def _on_move(self, x, y):
        if not RECORD_MOUSE_COORDS:
            return
        ev = {
            "ts": time.time(),
            "event_type": "mouse_move",
            "x": x,
            "y": y,
        }
        self.buffer.push(ev)

    # ---- 键盘回调 ----

    def _on_press(self, key):
        category = _classify_key(key)
        char = ""
        if hasattr(key, "char") and key.char is not None:
            char = key.char.lower()
        elif isinstance(key, keyboard.Key):
            char = key.name  # up, down, backspace, enter, space, ctrl, etc.

        ev = {
            "ts": time.time(),
            "event_type": "key_down",
            "button": category,
            "key_char": char,
        }
        self.buffer.push(ev)

    # ---- 生命周期 ----

    def start(self):
        """启动所有监听器"""
        if self._running:
            return
        self._running = True
        self.buffer.start()

        # 鼠标监听
        self._mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll,
            on_move=self._on_move,
        )
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

        # 键盘监听
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_press,
        )
        self._keyboard_listener.daemon = True
        self._keyboard_listener.start()

    def stop(self):
        """停止所有监听器"""
        self._running = False
        self.buffer.stop()
        if self._mouse_listener and self._mouse_listener.running:
            self._mouse_listener.stop()
        if self._keyboard_listener and self._keyboard_listener.running:
            self._keyboard_listener.stop()

    @property
    def running(self) -> bool:
        return self._running
