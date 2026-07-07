"""Bot 设置读取工具 — 共享模块，避免重复。"""

import json
from storage.database import get_setting, get_db


async def get_bot_setting(bot_token: str, key: str, default: str = "") -> str:
    """根据 Bot Token 查 per-bot 设置，空则 fallback 全局。"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM bots WHERE bot_token = ?", (bot_token,))
        row = await cursor.fetchone()
    finally:
        await db.close()
    if not row:
        return await get_setting(key, default)
    bot_id = row[0]
    val = await get_setting(f"{bot_id}:{key}", "")
    return val if val else await get_setting(key, default)


async def get_bot_setting_int(bot_token: str, key: str, default: int = 0) -> int:
    val = await get_bot_setting(bot_token, key, str(default))
    return int(val) if val else default


async def get_bot_structured(bot_token: str) -> dict:
    """获取 Bot 的结构化配置：soul、identity、user_context、system_prompt。"""
    soul_raw = await get_bot_setting(bot_token, "soul", "[]")
    try:
        soul = json.loads(soul_raw)
    except json.JSONDecodeError:
        soul = []

    identity = await get_bot_setting(bot_token, "identity", "")
    user_context = await get_bot_setting(bot_token, "user_context", "")
    system_prompt = await get_bot_setting(bot_token, "bot_system_prompt", "")

    return {"soul": soul, "identity": identity, "user_context": user_context, "system_prompt": system_prompt}


def build_agent_prompt(structured: dict) -> str:
    """从结构化字段构建 Agent Prompt（SOUL + IDENTITY + USER + 能力 + 自定义）。"""
    parts = []
    soul = structured.get("soul", [])
    identity = structured.get("identity", "")
    user_context = structured.get("user_context", "")
    custom = structured.get("system_prompt", "")

    if soul:
        trait_labels = {
            "friendly": "友好", "professional": "专业", "humorous": "幽默",
            "concise": "简洁", "detailed": "详细", "warm": "温暖",
            "creative": "创意", "logical": "理性", "patient": "耐心", "enthusiastic": "热情",
        }
        traits_cn = [trait_labels.get(t, t) for t in soul]
        parts.append(f"性格特征: {', '.join(traits_cn)}。请用这些特征回复。")

    if identity:
        parts.append(f"身份: {identity}")

    if user_context:
        parts.append(f"关于用户: {user_context}")

    # 能力提示：让 LLM 主动利用提醒功能
    parts.append(
        "你可以帮用户创建定时提醒。"
        "当用户说「提醒我…」「X分钟后提醒…」「设个闹钟」「帮我记一下」等，"
        "请务必调用 reminder 工具来创建提醒，不要只口头回复。"
    )

    if custom:
        parts.append(custom)

    return "\n".join(parts)



async def get_bot_allowed_models(bot_token: str) -> list[int]:
    """获取 Bot 允许使用的模型 ID 列表（空列表=使用全局默认）。"""
    import json
    val = await get_bot_setting(bot_token, "allowed_models", "")
    if not val:
        return []
    try:
        ids = json.loads(val)
        return [int(i) for i in ids if str(i).isdigit()]
    except (json.JSONDecodeError, ValueError):
        return []
