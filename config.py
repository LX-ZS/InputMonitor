"""
InputMonitor 配置
所有可调参数集中在此，方便定制
"""

from pathlib import Path

# ========== 路径 ==========
DB_DIR = Path.home() / ".inputmonitor"
DB_PATH = DB_DIR / "data.db"

# ========== 数据采集 ==========
# 是否记录鼠标坐标（隐私敏感选项 —— 默认关闭）
RECORD_MOUSE_COORDS = False

# 事件缓冲写入间隔（秒）
FLUSH_INTERVAL_SEC = 5

# ========== 特征聚合 ==========
# 特征窗口大小（秒）—— 每 N 秒生成一个特征向量
WINDOW_SIZE_SEC = 5 * 60  # 5 分钟

# ========== 空闲判定 ==========
# 连续无操作超过此秒数判定为空闲
IDLE_THRESHOLD_SEC = 120  # 2 分钟

# ========== 分类阈值 ==========
# 以下数值均为每窗口（5分钟）的阈值
TYPING_WPM_HIGH = 4           # 高速打字（20+字母/分钟）
TYPING_WPM_MED = 3            # 中速打字（15+字母/分钟）
MODIFIER_RATIO_HIGH = 0.10    # 修饰键占比≥10% → 编码特征
CLICK_RATE_GAMING = 120       # 每分钟点击 > 此值 → 游戏
CLICK_RATE_LOW = 8            # 每分钟点击 < 此值 → 低交互
SCROLL_HIGH = 300             # 5 分钟滚动量 > 此值 → 浏览
CLICK_RATE_BROWSING_MIN = 3   # 浏览场景最低点击
CLICK_RATE_BROWSING_MAX = 45  # 浏览场景最高点击
DRAG_RATIO_HIGH = 0.08        # 拖拽事件占比高（设计特征）

# ========== 数据保留 ==========
# 原始事件保留天数（超过自动清理）
RAW_EVENT_RETENTION_DAYS = 7
# 聚合数据保留天数
AGG_RETENTION_DAYS = 365

# ========== UI ==========
WINDOW_TITLE = "InputMonitor — 行为感知"
WINDOW_SIZE = (960, 680)
UPDATE_INTERVAL_MS = 2000  # UI 刷新间隔（毫秒）
