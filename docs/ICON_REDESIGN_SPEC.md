# InputMonitor 图标重绘规范

## 总体风格

- 统一 24×24 视图盒
- 线宽 1.8
- 圆角端点
- 双色渐变
- 不使用复杂写实阴影
- 图标主体保持单色线条，关键节点使用渐变圆点或小块强调

## 图标清单

| 文件 | 用途 |
|---|---|
| app_logo.svg | 应用图标 |
| dashboard.svg | 仪表盘 |
| timeline.svg | 时间线 |
| settings.svg | 设置 |
| privacy.svg | 隐私 |
| tray.svg | 托盘 |
| mouse.svg | 鼠标 |
| keyboard.svg | 键盘 |
| scroll.svg | 滚动 |
| coding.svg | 编码 |
| writing.svg | 写作 |
| chat.svg | 聊天 |
| browsing.svg | 浏览 |
| reading.svg | 阅读 |
| gaming.svg | 游戏 |
| idle.svg | 空闲 |
| mixed.svg | 混合 |

## 设计原则

### 1. 不为每个按钮乱画不同风格图标
所有图标都保持：
- 同一线宽
- 同一圆角
- 同一色彩饱和度
- 同一留白比例

### 2. 活动类图标必须一眼可辨认
- coding：尖括号 + 光点
- writing：笔尖 + 横线
- chat：气泡 + 输入点
- browsing：地球/窗口
- reading：打开的书
- gaming：手柄
- idle：月亮/暂停
- mixed：交叠节点

### 3. 功能类图标更克制
功能图标不要太花，避免和活动颜色冲突。
