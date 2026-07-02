#!/usr/bin/env python3
"""TG AI Chat Bot — 多 Bot 动态管理，实时生效。"""

import asyncio
import uvicorn

from core.config import core_config
from core.llm import llm_manager
from core.bot_manager import bot_manager, set_main_loop
from plugins.registry import plugin_registry
from storage.database import get_setting_list, migrate_database, get_plugin_configs
from utils.logger import logger
from utils.helpers import check_wcwidth
from web.auth import _init_secret_key


async def init_system():
    await _init_secret_key()
    await migrate_database()
    check_wcwidth()
    await core_config.refresh()
    await llm_manager.init()
    # 优先从 plugin_configs 表读取（唯一数据源），兼容旧 enabled_plugins 设置
    plugins = await get_plugin_configs()
    if plugins:
        enabled = [p["name"] for p in plugins if p["enabled"]]
    else:
        # 首次启动/旧库迁移：默认全部启用
        enabled = await get_setting_list("enabled_plugins", ["web_search", "url_summary", "weather", "calculator", "translate", "image_understand", "code_runner", "image_gen"])
    plugin_registry.set_enabled(enabled)
    logger.info(f"系统就绪 — 主模型: {llm_manager.primary}, 插件: {enabled}")


async def main():
    await init_system()

    # 启动所有 Bot
    await bot_manager.start_all()
    if bot_manager.running_count == 0:
        logger.warning("暂无活跃 Bot，Web 面板可实时添加/管理")

    # 在同一事件循环启动 FastAPI（非独立线程）
    config = uvicorn.Config("web.api:app", host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    loop = asyncio.get_event_loop()
    set_main_loop(loop)

    logger.info("Web 管理面板: http://0.0.0.0:8000")
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
