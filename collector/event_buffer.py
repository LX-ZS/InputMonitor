"""
线程安全的事件缓冲区
- 监听线程写入事件
- 定时器线程批量刷入 SQLite
"""

import threading
import time
from collections import deque
from typing import Callable

from config import FLUSH_INTERVAL_SEC


class EventBuffer:
    """线程安全的事件缓冲区，支持批量 Flush"""

    def __init__(self, flush_callback: Callable[[list[dict]], int]):
        self._queue: deque[dict] = deque()
        self._lock = threading.Lock()
        self._flush_cb = flush_callback
        self._timer: threading.Timer | None = None
        self._running = False

    def push(self, event: dict):
        """向缓冲区添加一条事件（线程安全）"""
        with self._lock:
            self._queue.append(event)

    def start(self):
        """启动定时 Flush"""
        self._running = True
        self._tick()

    def stop(self):
        """停止定器并做最后一次 Flush"""
        self._running = False
        if self._timer:
            self._timer.cancel()
        self._flush()

    def _tick(self):
        if not self._running:
            return
        self._flush()
        self._timer = threading.Timer(FLUSH_INTERVAL_SEC, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _flush(self):
        """取出所有积压事件，批量写入"""
        with self._lock:
            batch = list(self._queue)
            self._queue.clear()
        if batch:
            try:
                self._flush_cb(batch)
            except Exception as e:
                # 静默失败 —— 采集不应打断 UI
                pass
