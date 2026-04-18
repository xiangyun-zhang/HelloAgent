import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "history.db")


def _get_conn():
    """获取数据库连接，如果不存在则自动创建"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # 让 sqlite 返回字典格式的数据，方便后续处理
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL, -- 'user', 'assistant', 'tool', 'system'
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_message(session_id: str, role: str, content: str):
    """保存一条消息到数据库"""
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        conn.commit()


def get_history_list(limit: int = 5) -> list[str]:
    """获取最近几次会话的摘要，用于 /history 命令展示"""
    with _get_conn() as conn:
        cursor = conn.execute("""
            SELECT session_id, MIN(timestamp) as start_time, COUNT(*) as msg_count 
            FROM chat_history 
            GROUP BY session_id 
            ORDER BY start_time DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            # 获取该会话的第一句话作为摘要
            first_msg = conn.execute(
                "SELECT content FROM chat_history WHERE session_id = ? AND role = 'user' ORDER BY id ASC LIMIT 1",
                (row["session_id"],)
            ).fetchone()
            summary = first_msg["content"][:30] + "..." if first_msg else "无内容"
            result.append(
                f"[{row['start_time']}] 会话 {row['session_id'][:8]}... | 共{row['msg_count']}条 | 首句: {summary}")
        return result


def load_global_recent_messages(limit: int = 20) -> list[dict]:
    """跨所有会话加载最近的 N 条消息，用于启动时恢复上下文"""
    with _get_conn() as conn:
        cursor = conn.execute(
            "SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def clear_all_history():
    """清空所有聊天记录"""
    with _get_conn() as conn:
        conn.execute("DELETE FROM chat_history")
        conn.commit()
