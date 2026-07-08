"""Bot 管理器 — 动态启动/停止 Bot 实例，实时生效。"""

import asyncio
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters as tg_filters,
)

from bot.commands import handle_bot_command
from bot.conversation import handle_conversation, handle_photo
from bot.handler import handle_message
from storage.database import get_active_bot_tokens
from utils.logger import logger

# 主事件循环引用
_main_loop: asyncio.AbstractEventLoop = None


def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop


class BotManager:
    """管理多个 Bot 实例，支持热添加/删除/启停。"""

    def __init__(self):
        self._apps: dict[int, Application] = {}  # bot_id -> Application

    async def start_all(self):
        """启动所有活跃的 Bot。"""
        from storage.database import get_bots
        bots = await get_bots()
        for bot in bots:
            if bot["is_active"] and bot["bot_token"]:
                await self._start_one(bot["id"], bot["bot_token"])

    async def _start_one(self, bot_id: int, token: str):
        if bot_id in self._apps:
            return

        max_retries = 5
        backoff = 10  # 秒

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Bot #{bot_id} 重试启动 (第 {attempt}/{max_retries} 次)...")
                app = self._build_app(token)
                await app.initialize()
                await app.bot.delete_webhook(drop_pending_updates=True)
                await app.start()
                await app.updater.start_polling(
                    poll_interval=1.0,
                    timeout=30,
                    bootstrap_retries=-1,
                )
                info = await app.bot.get_me()
                self._apps[bot_id] = app
                suffix = f"（重试 {attempt} 次后成功）" if attempt > 0 else ""
                logger.info(f"Bot #{bot_id} @{info.username} 已上线{suffix}")
                return
            except Exception as e:
                err_str = str(e).lower()
                is_network = any(k in err_str for k in ("connecterror", "timeout", "network", "connection"))
                is_conflict = "conflict" in err_str

                if attempt < max_retries and (is_network or is_conflict):
                    if is_conflict:
                        logger.info(f"Bot #{bot_id} Conflict，{backoff}秒后重试...")
                    else:
                        logger.warning(f"Bot #{bot_id} 网络异常 ({type(e).__name__})，{backoff}秒后重试...")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)  # 指数退避，最多 60s
                    continue

                logger.warning(f"Bot #{bot_id} 启动失败: {e}")

    async def _stop_one(self, bot_id: int):
        app = self._apps.pop(bot_id, None)
        if app:
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
                logger.info(f"Bot #{bot_id} 已下线")
            except Exception as e:
                logger.error(f"Bot #{bot_id} 停止失败: {e}")

    def _build_app(self, token: str) -> Application:
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler(
            ["start", "help", "chat", "clear", "history", "status",
             "search", "weather", "translate", "calc", "draw", "news",
             "connectors", "connector", "admin", "switch_model",
             "list_models", "whitelist", "blacklist", "stats",
             "broadcast", "plugin"],
            handle_bot_command
        ))
        app.add_handler(MessageHandler(tg_filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, handle_message))
        return app

    async def shutdown_all(self):
        for bot_id in list(self._apps.keys()):
            await self._stop_one(bot_id)

    # ===== 供 Web API 调用的方法 =====

    def add_bot(self, bot_id: int, name: str, token: str):
        """在事件循环中启动新 Bot（可从任意线程调用）。"""
        if _main_loop:
            asyncio.run_coroutine_threadsafe(self._start_one(bot_id, token), _main_loop)
            logger.info(f"已调度启动 Bot #{bot_id} ({name})")

    def remove_bot(self, bot_id: int):
        """停止并移除 Bot（可从任意线程调用）。"""
        if _main_loop:
            asyncio.run_coroutine_threadsafe(self._stop_one(bot_id), _main_loop)
            logger.info(f"已调度停止 Bot #{bot_id}")

    def toggle_bot(self, bot_id: int, active: bool, token: str):
        """启用/禁用 Bot。"""
        if active:
            self.add_bot(bot_id, "", token)
        else:
            self.remove_bot(bot_id)

    @property
    def running_count(self) -> int:
        return len(self._apps)


bot_manager = BotManager()
