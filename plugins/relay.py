"""消息转发插件 — 根据用户描述将消息发送到目标群聊。"""

from typing import Optional

from plugins.base import BasePlugin
from storage.database import get_db
from utils.logger import logger


class RelayPlugin(BasePlugin):
    """根据群名匹配会话表中的群聊，并向目标群发送消息。"""

    @property
    def name(self) -> str:
        return "relay"

    @property
    def description(self) -> str:
        return (
            "将一条消息转发到用户指定的群聊中。"
            "当用户说「帮我把这段话发到XX群」「通知XX群…」「转发到XX群」时调用。"
            "参数 group_name 为群里提到的关键词/群名称，message 为要发送的内容。"
        )

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return ""

    def get_tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "group_name": {
                            "type": "string",
                            "description": "目标群聊的关键词或名称，用户提到的群名"
                        },
                        "message": {
                            "type": "string",
                            "description": "要发送到群里的消息内容"
                        }
                    },
                    "required": ["group_name", "message"]
                }
            }
        }

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        group_name = params.get("group_name", "").strip()
        message = params.get("message", "").strip()

        if not group_name or not message:
            return "请提供目标群名称和要发送的消息内容。"

        context = context or {}
        bot = context.get("bot")
        user_id = context.get("user_id")
        bot_id = context.get("bot_id")

        if not bot:
            return "系统错误：无法获取 Bot 实例。"

        # 1. 从会话表中查找该用户参与过的群聊
        db = await get_db()
        try:
            if bot_id:
                cursor = await db.execute(
                    "SELECT DISTINCT chat_id FROM sessions WHERE bot_id = ? AND user_id = ? AND chat_id LIKE '-%'",
                    (bot_id, user_id)
                )
            else:
                cursor = await db.execute(
                    "SELECT DISTINCT chat_id FROM sessions WHERE user_id = ? AND chat_id LIKE '-%'",
                    (user_id,)
                )
            rows = await cursor.fetchall()
        finally:
            await db.close()

        if not rows:
            return (
                "没有找到你参与过的群聊。请确保：\n"
                "1. 你已在目标群中发送过消息（Bot 需要记录过该群会话）\n"
                "2. Bot 已被添加到该群中"
            )

        # 2. 根据群名关键词匹配目标群
        matched_chat_id = None
        matched_title = None
        candidates = []

        for row in rows:
            chat_id = str(row[0])
            try:
                chat = await bot.get_chat(chat_id)
                title = chat.title or chat_id
                candidates.append((chat_id, title))

                # 精确匹配优先
                if group_name.lower() == title.lower():
                    matched_chat_id = chat_id
                    matched_title = title
                    break
                # 模糊匹配
                if group_name.lower() in title.lower():
                    if not matched_chat_id:
                        matched_chat_id = chat_id
                        matched_title = title
            except Exception as e:
                logger.debug(f"获取群 {chat_id} 信息失败: {e}")
                continue

        if not matched_chat_id:
            if candidates:
                names = "、".join([t for _, t in candidates])
                return f"没有找到名为「{group_name}」的群。你参与过的群有：{names}。请用更准确的关键词重试。"
            return f"没有找到名为「{group_name}」的群。请确认群名是否正确。"

        # 3. 发送消息
        try:
            await bot.send_message(chat_id=matched_chat_id, text=message)
            logger.info(f"relay: user={user_id} → 群「{matched_title}」({matched_chat_id}) 消息已发送")
            return f"已成功将消息发送到群「{matched_title}」。"
        except Exception as e:
            logger.error(f"relay 发送失败: {e}")
            return f"发送到群「{matched_title}」失败：{e}。请确认 Bot 仍在群中且具有发送消息权限。"
