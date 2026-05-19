#!/usr/bin/env python3
"""
InputMonitor — 基于输入行为推断用户活动状态
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

LOCK_FILE = os.path.join(PROJECT_ROOT, ".instance.lock")


SIGNAL_FILE = os.path.join(PROJECT_ROOT, ".show.signal")


def check_single_instance() -> bool:
    """检测是否已有实例在运行，有则写信号文件并返回 False"""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old_pid = int(f.read().strip())
            if os.name == "nt":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x400, False, old_pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    # 写显示信号 → 让已运行的实例把自己显示出来
                    with open(SIGNAL_FILE, "w") as sf:
                        sf.write("show")
                    return False
            else:
                import signal
                os.kill(old_pid, 0)
                with open(SIGNAL_FILE, "w") as sf:
                    sf.write("show")
                return False
        except (ValueError, OSError, IOError):
            pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def cleanup_lock():
    """退出时清理锁文件和信号文件"""
    for p in [LOCK_FILE, SIGNAL_FILE]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except:
                pass


def main():
    if not check_single_instance():
        print("! InputMonitor already running, switched to existing window")
        sys.exit(0)

    try:
        import pynput
        import customtkinter
    except ImportError as e:
        print(f"缺少依赖：{e.name}")
        cleanup_lock()
        sys.exit(1)

    try:
        from ui.app import InputMonitorApp
        app = InputMonitorApp()
        # 注册退出清理
        app.protocol("WM_DELETE_WINDOW", lambda: (cleanup_lock(), app.withdraw()))
        # 在 _quit_app 中也清理
        app._cleanup_lock = cleanup_lock
        app.mainloop()
    finally:
        cleanup_lock()


if __name__ == "__main__":
    main()
