"""SQLite 数据库操作层 — 所有设置通过数据库管理。"""

import json
import aiosqlite
from typing import Optional

from storage.models import CREATE_TABLES_SQL, Message, ModelConfig
from utils.logger import logger

DB_PATH = "data/bot.db"


async def get_db() -> aiosqlite.Connection:
    import os
    os.makedirs("data", exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.executescript(CREATE_TABLES_SQL)
    await db.commit()
    return db


async def migrate_database():
    """兼容旧库：添加新字段。"""
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("ALTER TABLE model_configs ADD COLUMN capabilities TEXT DEFAULT '{}'")
        await db.commit()
        logger.info("数据库迁移: model_configs 已添加 capabilities 列")
    except Exception:
        pass  # 列已存在
    finally:
        await db.close()


# ===== 会话管理 =====

async def get_conversation(bot_id: int, chat_id: str) -> list[Message]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT role, content, model, tokens FROM conversations WHERE bot_id = ? AND chat_id = ? ORDER BY id ASC",
            (bot_id, chat_id)
        )
        rows = await cursor.fetchall()
        return [Message(role=r[0], content=r[1], model=r[2], tokens=r[3]) for r in rows]
    finally:
        await db.close()


async def add_message(bot_id: int, chat_id: str, user_id: int, role: str, content: str,
                      model: str = "", tokens: int = 0, max_history: int = 20):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO conversations (bot_id, chat_id, user_id, role, content, model, tokens) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (bot_id, chat_id, user_id, role, content, model, tokens)
        )
        await db.commit()
        await db.execute("""
            DELETE FROM conversations WHERE id IN (
                SELECT id FROM conversations WHERE bot_id = ? AND chat_id = ? ORDER BY id ASC
                LIMIT MAX(0, (SELECT COUNT(*) FROM conversations WHERE bot_id = ? AND chat_id = ?) - ?)
            )
        """, (bot_id, chat_id, bot_id, chat_id, max_history * 2))
        await db.commit()
        await db.execute("""
            INSERT INTO sessions (bot_id, chat_id, user_id, model, message_count, total_tokens, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(bot_id, chat_id) DO UPDATE SET
                message_count = message_count + 1,
                total_tokens = total_tokens + ?,
                updated_at = CURRENT_TIMESTAMP
        """, (bot_id, chat_id, user_id, model, tokens, tokens))
        await db.commit()
    finally:
        await db.close()


async def compress_conversation(bot_id: int, chat_id: str, summary_text: str, keep_latest: int = 10):
    """压缩对话历史：删除旧消息，保留最近 N 条 + 一条摘要。"""
    db = await get_db()
    try:
        # 保留最近 keep_latest 条记录
        cursor = await db.execute(
            "SELECT id FROM conversations WHERE bot_id = ? AND chat_id = ? ORDER BY id DESC LIMIT 1 OFFSET ?",
            (bot_id, chat_id, keep_latest)
        )
        row = await cursor.fetchone()
        if row:
            await db.execute(
                "DELETE FROM conversations WHERE bot_id = ? AND chat_id = ? AND id <= ?",
                (bot_id, chat_id, row[0])
            )
            # 插入摘要（作为 system 消息，排在保留的消息之前）
            from datetime import datetime
            await db.execute(
                "INSERT INTO conversations (bot_id, chat_id, user_id, role, content, model, tokens, created_at) VALUES (?, ?, 0, 'system', ?, 'summary', ?, datetime('now', '-1 seconds'))",
                (bot_id, chat_id, summary_text, len(summary_text) // 2)
            )
            await db.commit()
            logger.info(f"对话压缩完成: bot={bot_id} chat={chat_id}, 保留 {keep_latest} 条 + 摘要")
    finally:
        await db.close()


async def should_compress(bot_id: int, chat_id: str, threshold: int = 30) -> bool:
    """检查是否需要压缩对话（消息数 > threshold 条）。"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM conversations WHERE bot_id = ? AND chat_id = ?",
            (bot_id, chat_id)
        )
        row = await cursor.fetchone()
        return (row[0] or 0) > threshold
    finally:
        await db.close()


async def clear_conversation(bot_id: int, chat_id: str):
    db = await get_db()
    try:
        await db.execute("DELETE FROM conversations WHERE bot_id = ? AND chat_id = ?", (bot_id, chat_id))
        await db.execute("DELETE FROM sessions WHERE bot_id = ? AND chat_id = ?", (bot_id, chat_id))
        await db.commit()
    finally:
        await db.close()


async def get_session_info(bot_id: int, chat_id: str) -> Optional[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE bot_id = ? AND chat_id = ?", (bot_id, chat_id))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


# ===== 统计 =====

async def record_usage(chat_id: str, user_id: int, model: str, tokens: int):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO stats (chat_id, user_id, model, tokens) VALUES (?, ?, ?, ?)",
            (chat_id, user_id, model, tokens)
        )
        await db.commit()
    finally:
        await db.close()


async def get_stats(days: int = 7) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT COUNT(*) as total_messages, COALESCE(SUM(tokens), 0) as total_tokens,
                   COUNT(DISTINCT user_id) as unique_users, COUNT(DISTINCT chat_id) as active_chats
            FROM stats WHERE created_at >= datetime('now', ? || ' days')
        """, (f"-{days}",))
        row = await cursor.fetchone()
        cursor2 = await db.execute("""
            SELECT model, COUNT(*) as count, COALESCE(SUM(tokens), 0) as tokens
            FROM stats WHERE created_at >= datetime('now', ? || ' days') GROUP BY model
        """, (f"-{days}",))
        by_model = [{"model": r[0], "count": r[1], "tokens": r[2]} for r in await cursor2.fetchall()]
        return {
            "total_messages": row[0] or 0,
            "total_tokens": row[1] or 0,
            "unique_users": row[2] or 0,
            "active_chats": row[3] or 0,
            "by_model": by_model,
            "period_days": days,
        }
    finally:
        await db.close()


# ===== 黑名单 =====

async def is_blacklisted(user_id: int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT 1 FROM blacklist WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None
    finally:
        await db.close()


async def add_blacklist(user_id: int, reason: str = ""):
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO blacklist (user_id, reason, added_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (user_id, reason)
        )
        await db.commit()
    finally:
        await db.close()


async def remove_blacklist(user_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
        await db.commit()
    finally:
        await db.close()


async def get_blacklist() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM blacklist ORDER BY added_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# ===== 全局设置 =====

async def get_setting(key: str, default: str = "") -> str:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default
    finally:
        await db.close()


async def set_setting(key: str, value) -> bool:
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    else:
        value = str(value)
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"更新设置失败 {key}: {e}")
        return False
    finally:
        await db.close()


async def get_all_settings() -> dict:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT key, value FROM bot_settings")
        rows = await cursor.fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        await db.close()


async def get_setting_bool(key: str, default: bool = False) -> bool:
    val = await get_setting(key, str(default).lower())
    return val.lower() == "true"


async def get_setting_int(key: str, default: int = 0) -> int:
    val = await get_setting(key, str(default))
    return int(val) if val else default


async def get_setting_list(key: str, default=None) -> list:
    val = await get_setting(key, "")
    if not val:
        return default or []
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        return [x.strip() for x in val.split(",") if x.strip()]


# ===== 机器人实例管理 =====

async def get_bots() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM bots ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_bot(bot_id: int) -> Optional[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def create_bot(name: str, bot_token: str) -> Optional[int]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO bots (name, bot_token) VALUES (?, ?)",
            (name, bot_token)
        )
        await db.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"创建 Bot 失败: {e}")
        return None
    finally:
        await db.close()


async def update_bot(bot_id: int, **kwargs) -> bool:
    db = await get_db()
    try:
        allowed = ["name", "bot_token", "is_active"]
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        fields = []
        vals = []
        for k, v in updates.items():
            fields.append(f"{k} = ?")
            vals.append(1 if k == "is_active" and v else (0 if k == "is_active" and not v else v))
        fields.append("updated_at = CURRENT_TIMESTAMP")
        await db.execute(
            f"UPDATE bots SET {', '.join(fields)} WHERE id = ?",
            vals + [bot_id]
        )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"更新 Bot {bot_id} 失败: {e}")
        return False
    finally:
        await db.close()


async def delete_bot(bot_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"删除 Bot {bot_id} 失败: {e}")
        return False
    finally:
        await db.close()


async def get_active_bot_tokens() -> list[str]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT bot_token FROM bots WHERE is_active = 1")
        rows = await cursor.fetchall()
        return [r[0] for r in rows if r[0]]
    finally:
        await db.close()


# ===== 模型配置 =====

async def get_model_configs() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM model_configs ORDER BY sort_order ASC, id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_model_config(model_id: int) -> Optional[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM model_configs WHERE id = ?", (model_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_model_config(model_id: int, **kwargs) -> bool:
    db = await get_db()
    try:
        allowed = ["name", "provider", "api_key", "base_url", "model_name", "is_enabled", "sort_order", "capabilities"]
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        fields = []
        vals = []
        for k, v in updates.items():
            fields.append(f"{k} = ?")
            vals.append(1 if k == "is_enabled" and v else (0 if k == "is_enabled" and not v else v))
        fields.append("updated_at = CURRENT_TIMESTAMP")
        await db.execute(
            f"UPDATE model_configs SET {', '.join(fields)} WHERE id = ?",
            vals + [model_id]
        )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"更新模型配置失败 #{model_id}: {e}")
        return False
    finally:
        await db.close()


async def add_model_config(name: str, provider: str = "openai") -> Optional[int]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT MAX(sort_order) FROM model_configs")
        row = await cursor.fetchone()
        next_order = (row[0] or 0) + 1
        cursor = await db.execute(
            "INSERT INTO model_configs (name, provider, sort_order) VALUES (?, ?, ?)",
            (name, provider, next_order)
        )
        await db.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"添加模型失败: {e}")
        return None
    finally:
        await db.close()


async def delete_model_config(model_id: int) -> bool:
    db = await get_db()
    try:
        await db.execute("DELETE FROM model_configs WHERE id = ?", (model_id,))
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"删除模型 #{model_id} 失败: {e}")
        return False
    finally:
        await db.close()


async def get_enabled_models() -> list[dict]:
    configs = await get_model_configs()
    return [c for c in configs if c["is_enabled"] and c["api_key"]]




# ===== 插件配置 =====

async def get_plugin_configs() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM plugin_configs ORDER BY name")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def set_plugin_enabled(name: str, enabled: bool) -> bool:
    db = await get_db()
    try:
        # 确保插件存在于 plugin_configs 表中（新插件首次启用时自动创建记录）
        await db.execute(
            "INSERT OR IGNORE INTO plugin_configs (name, enabled) VALUES (?, ?)",
            (name, 0)
        )
        await db.execute(
            "UPDATE plugin_configs SET enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
            (1 if enabled else 0, name)
        )
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"更新插件状态失败 {name}: {e}")
        return False
    finally:
        await db.close()
