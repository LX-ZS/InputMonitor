"""
SQLite 存储层
- 原始事件：批量写入，定期清理
- 特征窗口：供引擎分析
- 活动段：分类结果持久化
"""

import sqlite3
import threading
from datetime import datetime, date, timedelta
from typing import Optional
from pathlib import Path

from config import DB_PATH, RAW_EVENT_RETENTION_DAYS, AGG_RETENTION_DAYS


# ============ 线程安全的单例连接 ============
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """获取当前线程的数据库连接"""
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return _local.conn


# ============ 建表 ============

def init_db():
    """初始化数据库，创建表结构"""
    conn = _get_conn()

    conn.executescript("""
        -- 原始事件表
        CREATE TABLE IF NOT EXISTS raw_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          REAL    NOT NULL,       -- time.time() 浮点时间戳
            event_type  TEXT    NOT NULL,       -- mouse_click / mouse_move / mouse_scroll / key_down / key_up
            button      TEXT,                   -- Left / Right / Middle / letter / digit / modifier / nav / function / other
            x           INTEGER,               -- 鼠标坐标 (可选)
            y           INTEGER,
            session_id  TEXT NOT NULL DEFAULT ''
        );

        -- 特征窗口表（每 WINDOW_SIZE_SEC 一条）
        CREATE TABLE IF NOT EXISTS feature_windows (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            window_start    REAL    NOT NULL,   -- 窗口起始时间戳
            window_end      REAL    NOT NULL,   -- 窗口结束时间戳
            clicks_total    INTEGER DEFAULT 0,
            clicks_left     INTEGER DEFAULT 0,
            clicks_right    INTEGER DEFAULT 0,
            clicks_middle   INTEGER DEFAULT 0,
            scroll_distance INTEGER DEFAULT 0,
            key_presses     INTEGER DEFAULT 0,
            key_letter      INTEGER DEFAULT 0,
            key_modifier    INTEGER DEFAULT 0,
            key_nav         INTEGER DEFAULT 0,
            key_num         INTEGER DEFAULT 0,
            key_function    INTEGER DEFAULT 0,
            key_other       INTEGER DEFAULT 0,
            active_seconds  REAL    DEFAULT 0,
            UNIQUE(window_start)
        );

        -- 训练标注表（人工标签）
        CREATE TABLE IF NOT EXISTS training_labels (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            window_start    REAL    NOT NULL,
            label           TEXT    NOT NULL,
            created_at      TEXT    DEFAULT (datetime('now','localtime'))
        );

        -- 活动段表（分类结果）
        CREATE TABLE IF NOT EXISTS activity_segments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time      REAL    NOT NULL,
            end_time        REAL    NOT NULL,
            activity_type   TEXT    NOT NULL,   -- coding / writing / browsing / reading / gaming / idle / mixed
            confidence      REAL    DEFAULT 0.5
        );

        -- 自定义活动表
        CREATE TABLE IF NOT EXISTS custom_activities (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL UNIQUE,
            color   TEXT NOT NULL DEFAULT '#8892b0',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_raw_ts ON raw_events(ts);
        CREATE INDEX IF NOT EXISTS idx_raw_type ON raw_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_feature_ws ON feature_windows(window_start);
        CREATE INDEX IF NOT EXISTS idx_activity_start ON activity_segments(start_time);
    """)
    conn.commit()

    # 迁移：给 feature_windows 加新列（如果还没有）
    for col in ["key_wasd", "key_arrow", "key_backspace", "key_enter",
                 "key_space", "key_ctrl_cv", "key_shift_letter"]:
        try:
            conn.execute(f"ALTER TABLE feature_windows ADD COLUMN {col} INTEGER DEFAULT 0")
        except Exception:
            pass
    conn.commit()


# ============ 原始事件写入 ============

def insert_raw_events(events: list[dict]) -> int:
    """批量插入原始事件（线程安全）"""
    if not events:
        return 0
    conn = _get_conn()
    rows = [(
        e["ts"],
        e["event_type"],
        e.get("button"),
        e.get("x"),
        e.get("y"),
        e.get("session_id", ""),
    ) for e in events]
    conn.executemany(
        "INSERT INTO raw_events(ts, event_type, button, x, y, session_id) VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    return len(rows)


# ============ 特征窗口 ============

def upsert_feature_window(window: dict) -> int:
    """插入或更新一个特征窗口"""
    conn = _get_conn()
    conn.execute("""
        INSERT INTO feature_windows(
            window_start, window_end,
            clicks_total, clicks_left, clicks_right, clicks_middle,
            scroll_distance,
            key_presses, key_letter, key_modifier, key_nav, key_num, key_function, key_other,
            key_wasd, key_arrow, key_backspace, key_enter, key_space, key_ctrl_cv, key_shift_letter,
            active_seconds
        ) VALUES (
            :window_start, :window_end,
            :clicks_total, :clicks_left, :clicks_right, :clicks_middle,
            :scroll_distance,
            :key_presses, :key_letter, :key_modifier, :key_nav, :key_num, :key_function, :key_other,
            :key_wasd, :key_arrow, :key_backspace, :key_enter, :key_space, :key_ctrl_cv, :key_shift_letter,
            :active_seconds
        )
        ON CONFLICT(window_start) DO UPDATE SET
            window_end          = excluded.window_end,
            clicks_total        = excluded.clicks_total,
            clicks_left         = excluded.clicks_left,
            clicks_right        = excluded.clicks_right,
            clicks_middle       = excluded.clicks_middle,
            scroll_distance     = excluded.scroll_distance,
            key_presses         = excluded.key_presses,
            key_letter          = excluded.key_letter,
            key_modifier        = excluded.key_modifier,
            key_nav             = excluded.key_nav,
            key_num             = excluded.key_num,
            key_function        = excluded.key_function,
            key_other           = excluded.key_other,
            key_wasd            = excluded.key_wasd,
            key_arrow           = excluded.key_arrow,
            key_backspace       = excluded.key_backspace,
            key_enter           = excluded.key_enter,
            key_space           = excluded.key_space,
            key_ctrl_cv         = excluded.key_ctrl_cv,
            key_shift_letter    = excluded.key_shift_letter,
            active_seconds      = excluded.active_seconds
    """, window)
    conn.commit()
    return conn.total_changes


# ============ 实时原始计数 ============

def get_raw_counts() -> dict:
    """从原始事件表直接获取今日计数（实时，不等特征窗口）"""
    conn = _get_conn()
    today_start = _day_start()
    rows = conn.execute("""
        SELECT
            event_type,
            button,
            COUNT(*) AS cnt
        FROM raw_events
        WHERE ts >= ?
        GROUP BY event_type, button
    """, (today_start,)).fetchall()
    
    clicks = 0
    keys = 0
    for r in rows:
        if r[0] == "mouse_click":
            clicks += r[2]
        elif r[0] == "key_down":
            keys += r[2]
    return {"clicks": clicks, "keys": keys}


# ============ 活动段 ============

def insert_activity_segment(seg: dict) -> int:
    """插入一条活动分类结果"""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO activity_segments(start_time, end_time, activity_type, confidence) VALUES (?,?,?,?)",
        (seg["start_time"], seg["end_time"], seg["activity_type"], seg.get("confidence", 0.5)),
    )
    conn.commit()
    return conn.total_changes


# ============ 聚合查询 ============

def get_date_summary(dt: date) -> dict:
    """获取指定日期的汇总数据"""
    conn = _get_conn()
    day_start = datetime.combine(dt, datetime.min.time()).timestamp()
    day_end = day_start + 86400
    row = conn.execute("""
        SELECT
            COALESCE(SUM(clicks_total), 0)         AS total_clicks,
            COALESCE(SUM(clicks_left), 0)           AS left_clicks,
            COALESCE(SUM(clicks_right), 0)          AS right_clicks,
            COALESCE(SUM(key_presses), 0)           AS total_keys,
            COALESCE(SUM(key_letter), 0)            AS letter_keys,
            COALESCE(SUM(key_modifier), 0)          AS modifier_keys,
            COALESCE(SUM(key_nav), 0)               AS nav_keys,
            COALESCE(SUM(key_num), 0)               AS num_keys,
            COALESCE(SUM(scroll_distance), 0)       AS scroll_total,
            COALESCE(SUM(active_seconds), 0)        AS active_seconds
        FROM feature_windows
        WHERE window_start >= ? AND window_start < ?
    """, (day_start, day_end)).fetchone()
    return {
        "total_clicks":   row[0], "left_clicks": row[1], "right_clicks": row[2],
        "total_keys":     row[3], "letter_keys": row[4], "modifier_keys": row[5],
        "nav_keys":       row[6], "num_keys": row[7], "scroll_total": row[8],
        "active_seconds": row[9],
    }


def get_date_activity_segments(dt: date) -> list[dict]:
    """获取指定日期的活动段（用人工标签覆盖）"""
    conn = _get_conn()
    day_start = datetime.combine(dt, datetime.min.time()).timestamp()
    day_end = day_start + 86400
    rows = conn.execute("""
        SELECT * FROM activity_segments
        WHERE start_time >= ? AND start_time < ?
        ORDER BY start_time ASC
    """, (day_start, day_end)).fetchall()
    cols = [d[1] for d in conn.execute("PRAGMA table_info(activity_segments)").fetchall()]
    segs = [dict(zip(cols, r)) for r in rows]
    labels = conn.execute("""
        SELECT window_start, label FROM training_labels
        WHERE window_start >= ? AND window_start < ?
    """, (day_start, day_end)).fetchall()
    label_map = {r[0]: r[1] for r in labels}
    for s in segs:
        if s["start_time"] in label_map:
            s["activity_type"] = label_map[s["start_time"]]
    return segs


def get_today_summary() -> dict:
    """获取今日汇总数据"""
    conn = _get_conn()
    today_start = _day_start()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(clicks_total), 0)         AS total_clicks,
            COALESCE(SUM(clicks_left), 0)           AS left_clicks,
            COALESCE(SUM(clicks_right), 0)          AS right_clicks,
            COALESCE(SUM(key_presses), 0)           AS total_keys,
            COALESCE(SUM(key_letter), 0)            AS letter_keys,
            COALESCE(SUM(key_modifier), 0)          AS modifier_keys,
            COALESCE(SUM(key_nav), 0)               AS nav_keys,
            COALESCE(SUM(key_num), 0)               AS num_keys,
            COALESCE(SUM(scroll_distance), 0)       AS scroll_total,
            COALESCE(SUM(active_seconds), 0)        AS active_seconds
        FROM feature_windows
        WHERE window_start >= ?
    """, (today_start,)).fetchone()

    return {
        "total_clicks":   row[0],
        "left_clicks":    row[1],
        "right_clicks":   row[2],
        "total_keys":     row[3],
        "letter_keys":    row[4],
        "modifier_keys":  row[5],
        "nav_keys":       row[6],
        "num_keys":       row[7],
        "scroll_total":   row[8],
        "active_seconds": row[9],
    }


def get_today_windows() -> list[dict]:
    """获取今日所有特征窗口（按时间排序）"""
    conn = _get_conn()
    today_start = _day_start()
    rows = conn.execute("""
        SELECT * FROM feature_windows
        WHERE window_start >= ?
        ORDER BY window_start ASC
    """, (today_start,)).fetchall()
    cols = [d[1] for d in conn.execute("PRAGMA table_info(feature_windows)").fetchall()]
    return [dict(zip(cols, r)) for r in rows]


def get_today_activity_segments() -> list[dict]:
    """获取今日活动分类段（用人工标签覆盖规则分类）"""
    conn = _get_conn()
    today_start = _day_start()
    rows = conn.execute("""
        SELECT * FROM activity_segments
        WHERE start_time >= ?
        ORDER BY start_time ASC
    """, (today_start,)).fetchall()
    cols = [d[1] for d in conn.execute("PRAGMA table_info(activity_segments)").fetchall()]
    segs = [dict(zip(cols, r)) for r in rows]

    # 用 training_labels 覆盖：如果某个窗口有人工标签，替换 activity_type
    labels = conn.execute("""
        SELECT window_start, label FROM training_labels
        WHERE window_start >= ?
    """, (today_start,)).fetchall()
    label_map = {r[0]: r[1] for r in labels}
    for s in segs:
        if s["start_time"] in label_map:
            s["activity_type"] = label_map[s["start_time"]]
    return segs


def get_latest_activity_start() -> Optional[float]:
    """获取最后一个活动段的开始时间"""
    conn = _get_conn()
    row = conn.execute("""
        SELECT MAX(start_time) FROM activity_segments
    """).fetchone()
    return row[0] if row and row[0] else None


def get_latest_activity() -> Optional[str]:
    """获取最新活动段分类"""
    conn = _get_conn()
    row = conn.execute("""
        SELECT activity_type FROM activity_segments
        ORDER BY end_time DESC LIMIT 1
    """).fetchone()
    return row[0] if row else None


# ============ 维护 ============

def cleanup_old_data():
    """清理超过保留期的数据"""
    conn = _get_conn()
    now = datetime.now().timestamp()
    cutoff_raw = now - RAW_EVENT_RETENTION_DAYS * 86400
    cutoff_agg = now - AGG_RETENTION_DAYS * 86400
    conn.execute("DELETE FROM raw_events WHERE ts < ?", (cutoff_raw,))
    conn.execute("DELETE FROM feature_windows WHERE window_start < ?", (cutoff_agg,))
    conn.execute("DELETE FROM activity_segments WHERE start_time < ?", (cutoff_agg,))
    conn.commit()


# ============ 工具 ============

def _day_start() -> float:
    """今天 00:00:00 的时间戳"""
    return datetime.combine(date.today(), datetime.min.time()).timestamp()


def get_events_in_range(start_ts: float, end_ts: float) -> list[dict]:
    """获取时间范围内的原始事件"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT ts, event_type, button, x, y FROM raw_events WHERE ts >= ? AND ts < ? ORDER BY ts",
        (start_ts, end_ts),
    ).fetchall()
    return [
        {"ts": r[0], "event_type": r[1], "button": r[2], "x": r[3], "y": r[4]}
        for r in rows
    ]


# ============ 训练标注 ============

def insert_label(window_start: float, label: str) -> int:
    """插入人工标注标签"""
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO training_labels(window_start, label, created_at) VALUES (?, ?, datetime('now','localtime'))",
        (window_start, label)
    )
    conn.commit()
    return conn.total_changes

def get_unlabeled_windows(limit: int = 5) -> list[dict]:
    """获取最近未被标注的活动段"""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT a.start_time, a.end_time, a.activity_type, a.confidence
        FROM activity_segments a
        WHERE a.start_time NOT IN (SELECT window_start FROM training_labels)
        ORDER BY a.start_time DESC LIMIT ?
    """, (limit,)).fetchall()
    return [
        {"start_time": r[0], "end_time": r[1], "activity_type": r[2], "confidence": r[3]}
        for r in rows
    ]

def get_labeled_count() -> int:
    """已标注数量"""
    conn = _get_conn()
    return conn.execute("SELECT COUNT(*) FROM training_labels").fetchone()[0]


# ============ 自定义活动 ============

def get_custom_activities() -> list[dict]:
    """获取所有自定义活动"""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM custom_activities ORDER BY id").fetchall()
    cols = [d[1] for d in conn.execute("PRAGMA table_info(custom_activities)").fetchall()]
    return [dict(zip(cols, r)) for r in rows]

def add_custom_activity(name: str, color: str = "#8892b0") -> bool:
    """添加自定义活动"""
    conn = _get_conn()
    try:
        conn.execute("INSERT INTO custom_activities(name, color) VALUES (?,?)", (name, color))
        conn.commit()
        return True
    except Exception:
        return False

def remove_custom_activity(name: str) -> bool:
    """删除自定义活动"""
    conn = _get_conn()
    conn.execute("DELETE FROM custom_activities WHERE name=?", (name,))
    conn.commit()
    return conn.total_changes > 0
