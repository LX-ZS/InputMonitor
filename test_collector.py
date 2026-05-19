"""
测试采集器是否正常工作
双击运行，然后随便点几下鼠标、敲几个键
5 秒后自动显示结果
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage.db import init_db, get_raw_counts
from collector.listener import InputCollector

init_db()

# 记录当前计数
before = get_raw_counts()
print(f"测试前: {before['clicks']} 点击, {before['keys']} 按键")
print()
print("请在 5 秒内点击鼠标或敲键盘...")
print()

ic = InputCollector()
ic.start()

time.sleep(5)

ic.stop()

after = get_raw_counts()
new_clicks = after['clicks'] - before['clicks']
new_keys = after['keys'] - before['keys']

print(f"测试后: {after['clicks']} 点击, {after['keys']} 按键")
print(f"新增: {new_clicks} 次点击, {new_keys} 次按键")

if new_clicks > 0 or new_keys > 0:
    print("\n✅ 采集器正常工作！问题在 UI 刷新")
else:
    print("\n❌ 采集器没有收到事件（权限问题？以管理员身份运行试试）")

input("\n按回车退出...")
