"""会话记忆管理 — bot_id + chat_id 隔离，不串台。"""

from storage.database import get_conversation, add_message, clear_conversation
from storage.models import Message
from utils.logger import logger


class MemoryManager:
    async def get_history(self, bot_id: int, chat_id: str) -> list[Message]:
        return await get_conversation(bot_id, chat_id)

    async def add_user_message(self, bot_id: int, chat_id: str, user_id: int, content: str,
                               max_history: int = 20, chat_title: str = ""):
        await add_message(bot_id, chat_id, user_id, "user", content,
                          max_history=max_history, chat_title=chat_title)

    async def add_assistant_message(self, bot_id: int, chat_id: str, user_id: int, content: str,
                                     model: str = "", tokens: int = 0, max_history: int = 20):
        await add_message(bot_id, chat_id, user_id, "assistant", content,
                          model=model, tokens=tokens, max_history=max_history)

    async def clear(self, bot_id: int, chat_id: str):
        await clear_conversation(bot_id, chat_id)
        logger.info(f"已清空会话 bot={bot_id} chat={chat_id}")

    async def get_context_messages(self, bot_id: int, chat_id: str, system_prompt: str = "",
                                    max_history: int = 20) -> list[dict]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        history = await self.get_history(bot_id, chat_id)
        recent = history[-(max_history * 2):]
        for msg in recent:
            messages.append({"role": msg.role, "content": msg.content})
        return messages


memory_manager = MemoryManager()
