"""
InputMonitor 打包脚本
运行: python build.py
输出: dist/InputMonitor/
"""

import os, sys, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist", "InputMonitor")

for d in ["build", "dist"]:
    p = os.path.join(ROOT, d)
    if os.path.exists(p):
        shutil.rmtree(p, ignore_errors=True)

# 收集所有 .py 文件作为 data（确保打包全部模块）
py_files = []
for dp, dn, fn in os.walk(ROOT):
    # 跳过 dist, build, __pycache__, .git, icons_feather, icons_png
    if any(x in dp for x in ["dist", "build", "__pycache__", ".git", "icons_feather"]):
        continue
    rel = os.path.relpath(dp, ROOT)
    for f in fn:
        if f.endswith(".py"):
            py_files.append(f"{os.path.join(rel, f)}{os.pathsep}{rel}/")

# 图标文件
icon_files = []
icon_dir = os.path.join(ROOT, "ui", "icons_png")
if os.path.isdir(icon_dir):
    for f in os.listdir(icon_dir):
        if f.endswith(".png"):
            icon_files.append(f"{os.path.join(icon_dir, f)}{os.pathsep}{'ui/icons_png/'}")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onedir",
    "--name", "InputMonitor",
    "--noconsole",
    "--icon", os.path.join(ROOT, "app_icon.png"),
    "--clean",
    "--distpath", os.path.join(ROOT, "dist"),
    "--workpath", os.path.join(ROOT, "build"),
    "--specpath", ROOT,
    # 显式引入所有模块
    "--hidden-import", "pynput.keyboard._win32",
    "--hidden-import", "pynput.mouse._win32",
    "--hidden-import", "pynput.keyboard",
    "--hidden-import", "pynput.mouse",
    "--hidden-import", "customtkinter",
    "--hidden-import", "PIL.Image",
    "--hidden-import", "PIL.ImageDraw",
    "--hidden-import", "PIL.ImageTk",
    "--hidden-import", "pystray._win32",
    "--hidden-import", "pystray",
    "--hidden-import", "queue",
    "--hidden-import", "threading",
    "--hidden-import", "collections",
    "--hidden-import", "storage.db",
    "--hidden-import", "engine.features",
    "--hidden-import", "engine.classifier",
    "--hidden-import", "collector.listener",
    "--hidden-import", "collector.event_buffer",
    "--hidden-import", "ui.styles",
    "--hidden-import", "ui.app",
] + [f"--add-data={f}" for f in py_files + icon_files] + [
    os.path.join(ROOT, "main.py"),
]

os.chdir(ROOT)
print("Building InputMonitor...")
print(f"Python files to bundle: {len(py_files)}")
print(f"Icon files: {len(icon_files)}")
ret = os.system(" ".join(cmd))

if ret == 0:
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(DIST) for f in fn)
    print(f"\n✅ 打包完成: {DIST}")
    print(f"   总大小: {size / 1024 / 1024:.1f} MB")
    print(f"   入口: {os.path.join(DIST, 'InputMonitor.exe')}")
else:
    print(f"\n❌ 打包失败 (code {ret})")
