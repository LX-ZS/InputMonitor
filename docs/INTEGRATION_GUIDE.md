# 接入说明：如何把补充包合并到现有项目

## 1. 复制文件

把下面三个目录复制到你的 InputMonitor 项目根目录：

```text
assets/icons/
themes/
ui/
```

## 2. 安装依赖

如果你原项目已经使用 CustomTkinter，一般不用重复安装。否则：

```bash
pip install -r requirements-ui.txt
```

## 3. 在主 UI 初始化处加入主题控制

示例：

```python
from ui.style_tokens import get_palette
from ui.acrylic_widgets import ThemeController

self.theme_controller = ThemeController(self.root, initial="dark")
```

## 4. 增加黑白切换按钮

```python
def toggle_theme(self):
    mode = self.theme_controller.toggle()
    self.apply_theme(mode)
```

## 5. 替换卡片样式

原来类似：

```python
card = ctk.CTkFrame(parent, fg_color="#111827")
```

可替换为：

```python
from ui.acrylic_widgets import AcrylicCard

card = AcrylicCard(parent, mode=self.theme_controller.mode)
```

## 6. 替换指标卡片

```python
from ui.acrylic_widgets import MetricCard

click_card = MetricCard(parent, title="点击", value=str(raw_clicks), icon="🖱")
```

实时更新时只调用：

```python
click_card.update_value(str(raw_clicks))
```

这不会影响你原来的 raw_clicks 统计逻辑。

## 7. 图标使用建议

CustomTkinter 原生对 SVG 支持有限。建议两种方式：

### 方案 A：保留 SVG 作为设计源文件
打包时用 Pillow 或 Inkscape 转成 PNG/ICO。

### 方案 B：按钮先使用文字/emoji，后续再接 PNG
本补充包的 demo 就采用这种方案，保证最少依赖和可运行。

## 8. 打包时需要加入资源目录

PyInstaller 示例：

```python
datas=[
    ("assets", "assets"),
    ("themes", "themes"),
]
```

或在 `.spec` 里加入对应目录。

## 9. 不要改的逻辑

根据 `WORKFLOW.md`，以下逻辑已经稳定，不建议为了美化而改动：

- pynput 全局钩子
- 5 秒批量写 SQLite
- 5 分钟窗口聚合
- 规则分类优先级
- 人工标签覆盖规则分类
- 托盘隐藏和单实例保护
- 默认不记录坐标的隐私逻辑
