"""Telegram 消息路由分发。"""

import time
from collections import defaultdict

from telegram import Update
from telegram.ext import ContextTypes

from bot.filters import is_group_chat
from bot.settings import get_bot_setting
from storage.database import is_blacklisted
from utils.logger import logger

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.conversation import handle_conversation

    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text.strip()

    if not user or not chat:
        return

    user_id = user.id
    chat_id = str(chat.id)

    if await is_blacklisted(user_id):
        logger.info(f"黑名单用户 {user_id}，已忽略")
        return

    # 频率限制
    if not await check_rate_limit(context, user_id, chat_id):
        return

    if is_group_chat(chat):
        await handle_group_message(update, context, chat_id, user_id, text)
    else:
        await handle_conversation(update, context, chat_id, user_id, text)


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                chat_id: str, user_id: int, text: str):
    from bot.conversation import handle_conversation

    bot_token = context.bot.token
    bot_username = context.bot.username
    reply_mode = await get_bot_setting(bot_token, "group_reply_mode", "mentioned")

    if reply_mode == "off":
        return

    if reply_mode == "all":
        await handle_conversation(update, context, chat_id, user_id, text)
        return

    if reply_mode == "mentioned":
        mentioned = f"@{bot_username}" in text if bot_username else False
        is_reply_to_bot = False
        if update.message.reply_to_message:
            replied_to = update.message.reply_to_message.from_user
            if replied_to and replied_to.id == context.bot.id:
                is_reply_to_bot = True

        if mentioned or is_reply_to_bot:
            if mentioned and bot_username:
                text = text.replace(f"@{bot_username}", "").strip()
            if not text:
                text = "[用户 @了你，但没有输入具体内容，请自然地回应]"
            await handle_conversation(update, context, chat_id, user_id, text)


async def check_rate_limit(context, user_id: int, chat_id: str) -> bool:
    """频率限制：同一用户每对话每分钟最多 N 条，0=不限制。"""
    bot_token = context.bot.token
    limit_str = await get_bot_setting(bot_token, "rate_limit", "0")
    try:
        limit = int(limit_str)
    except (ValueError, TypeError):
        limit = 0

    if limit <= 0:
        return True

    key = f"{user_id}:{chat_id}"
    now = time.time()
    _rate_limit_store[key] = [t for t in _rate_limit_store.get(key, []) if now - t < 60]
    if len(_rate_limit_store[key]) >= limit:
        return False
    _rate_limit_store[key].append(now)
    return True
