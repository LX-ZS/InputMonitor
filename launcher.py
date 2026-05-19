import sys, os, subprocess
# 走 main.py 的入口（含单实例检查）
root = os.path.dirname(os.path.abspath(__file__))
subprocess.run([sys.executable, os.path.join(root, "main.py")])
