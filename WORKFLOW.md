# InputMonitor 开发工作流总结

## 项目定位
基于鼠标/键盘输入行为推断用户活动状态的 Windows 桌面工具。
技术栈：Python + pynput（采集）+ CustomTkinter（UI）+ SQLite（存储）

---

## 功能清单

### 采集层
- [x] 全局鼠标钩子（点击、滚动）
- [x] 全局键盘钩子（分类：letter/digit/modifier/nav/function/other）
- [x] 特定按键追踪（WASD、方向键、退格、回车、空格、Ctrl+C/V）
- [x] 线程安全缓冲 + 定时批量写入 SQLite（每 5 秒）
- [x] 可选鼠标坐标记录（默认关闭，隐私开关）

### 特征引擎
- [x] 5 分钟窗口特征聚合
- [x] 活跃时间计算（减去空闲间隙）
- [x] 特征字段：clicks, keys, scroll, wasd, arrow, backspace, enter, space, ctrl_cv

### 分类器（规则引擎）
- [x] 8 种活动：编码/写作/聊天/浏览/阅读/游戏/空闲/混合
- [x] 规则优先级：游戏(WASD) > 编码(退格+修饰键) > 聊天(回车多) > 写作(空格多) > 浏览(滚动) > 阅读 > 空闲
- [x] 置信度打分 0.4-0.9

### UI（CustomTkinter）
- [x] 深色科技风配色（#0a0e1a 背景、#00d4ff 青色强调）
- [x] 仪表盘：4 指标卡片 + 时间线 + 活动分布
- [x] 快速标注栏（7 预定义 + 自定义活动按钮）
- [x] 定时弹窗询问（5/10/20/30 分钟可选）
- [x] 时间线视图（按天查看历史、日期导航）
- [x] 设置页：采集控制、隐私、数据管理、自定义活动、刷新间隔、开机自启、定时提醒

### 系统托盘
- [x] pystray 托盘图标
- [x] 关闭窗口→隐藏到托盘（不退出）
- [x] 右键菜单：显示/隐藏/退出
- [x] 单实例保护（锁文件 + 信号文件唤醒）

### 数据存储
- [x] SQLite（WAL 模式，线程安全）
- [x] 表：raw_events / feature_windows / activity_segments / training_labels / custom_activities
- [x] 自动清理旧数据（原始事件 7 天，聚合 1 年）
- [x] 人工标签覆盖规则分类（时间线和分布优先展示标注）

### 自定义活动
- [x] 设置页添加/删除
- [x] 标注栏即时同步（+ 按钮内联添加）
- [x] 定时弹窗同步
- [x] 时间线/分布同步

### 打包
- [x] PyInstaller 打包为独立 EXE（73.8 MB）
- [x] 自定义图标
- [x] 开机自启优先指向 EXE

---

## 踩坑记录

### 1. 沙箱文件系统隔离（最大坑）
**现象：** 所有 `write_file` 写入的文件用户桌面看不到。
**原因：** Reasonix 沙箱和真实桌面是两个隔离的文件系统。
**解决：** 用 `run_command` 执行 Python 或 PowerShell 命令直接操作真实文件系统路径。

### 2. Features 导错模块
**现象：** `ImportError: cannot import name 'Features'`
**原因：** `_process_one_window` 从 `engine.features` 导入了 `Features`，但它实际在 `engine.classifier` 里。
**解决：** 改 `from engine.classifier import Features`

### 3. PRAGMA 列名索引错误
**现象：** `KeyError: 'start_time'`
**原因：** `PRAGMA table_info` 返回的元组中 `d[0]` 是列序号（CID），`d[1]` 才是列名。
**解决：** `d[0]` → `d[1]`

### 4. CustomTkinter place() 参数限制
**现象：** `ValueError: width/height in place()`
**原因：** CTk 5.2+ 不允许 `place(width=..., height=...)`，必须在构造函数传。
**解决：** 宽高移到 `CTkFrame(..., width=..., height=...)`

### 5. 显示逻辑错误
**现象：** 数字卡住不更新。
**原因：** 代码用了 `summary if summary > 0 else raw`，一旦特征窗口建立就只显示聚合值（每 5 分钟更新），不再显示实时计数。
**解决：** 永远用 `raw_clicks` / `raw_keys` 实时计数显示。

### 6. 定时弹窗的 Python 作用域 Bug
**现象：** `UnboundLocalError: cannot access local variable 'datetime'`
**原因：** `try` 块内有 `from datetime import datetime`，Python 将其视为整个函数的局部变量。`except` 块引用 `datetime` 时，因 `try` 未执行到该行导致未绑定。
**解决：** 去掉局部 import，用模块级 `from datetime import datetime`

### 7. Unicode 编码问题
**现象：** `UnicodeEncodeError: 'gbk' codec can't encode character`
**原因：** Windows 控制台 GBK 编码无法显示 ⚠ 等 Unicode 字符。
**解决：** `main.py` 中改用纯 ASCII 字符串。

### 8. key_wasd 字段缺失
**现象：** `sqlite3.ProgrammingError: You did not supply a value for binding parameter :key_wasd`
**原因：** `features.py` 中空窗口字典没有加新字段，恢复旧风格时遗漏。
**解决：** 空窗口也要传 `key_wasd=0, key_arrow=0, ...`

### 9. 采集器在后台进程不工作
**现象：** `run_background` 启动的进程 pynput 收不到事件。
**原因：** 后台进程在非交互式会话中运行，pynput 钩子需要用户桌面会话。
**解决：** 用户必须自己双击运行（launcher.py 或 start.bat 或快捷方式）。

---

## 关键设计决策

### 为什么不用机器学习？
初期用规则引擎，数据量够大 + 有标注后切换。

### 为什么用 5 分钟窗口？
太短（1 分钟）噪音大，太长（30 分钟）粒度粗。5 分钟是行为识别的最佳平衡点。

### 为什么用 lock 文件而不是互斥体？
兼容性更好，跨 Python 版本和打包环境都稳定。配合 signal 文件实现"唤出隐藏窗口"。

### 为什么默认不记录坐标？
隐私。只在用户主动开启后才记录鼠标移动和点击位置。

---

## 启动方式

```bash
# 开发模式
python main.py

# 启动器（推荐）
python launcher.py

# 打包后
dist\InputMonitor\InputMonitor.exe

# 桌面快捷方式
C:\Users\Administrator\Desktop\InputMonitor.lnk
```

## 打包命令

```bash
python build.py
# 输出到 dist\InputMonitor\InputMonitor.exe
```
