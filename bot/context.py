"""Telegram 上下文提取器 — 结构化注入。"""

from telegram import Update
from telegram.error import TelegramError


async def build_context(update, context) -> dict:
    """提取完整上下文，输出结构化 dict。"""
    msg = update.message
    if not msg:
        return {}

    chat = update.effective_chat
    user = update.effective_user
    ctx = {"platform": "telegram"}

    # ===== 聊天环境 =====
    if chat:
        ctx["chat"] = {
            "id": str(chat.id),
            "type": chat.type,
            "title": chat.title or chat.username or "私聊",
            "is_group": chat.type in ("group", "supergroup"),
        }
        # 群人数
        if ctx["chat"]["is_group"]:
            try:
                ctx["chat"]["member_count"] = await context.bot.get_chat_member_count(chat.id)
            except TelegramError:
                ctx["chat"]["member_count"] = None

    # ===== 当前用户 =====
    if user:
        ctx["user"] = {
            "id": user.id,
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "username": user.username or "",
        }
        if chat and ctx["chat"]["is_group"]:
            try:
                member = await context.bot.get_chat_member(chat.id, user.id)
                ctx["user"]["is_admin"] = member.status in ("administrator", "creator")
            except TelegramError:
                ctx["user"]["is_admin"] = None

    # ===== 群管理员 =====
    if chat and ctx["chat"]["is_group"]:
        try:
            admins = await context.bot.get_chat_administrators(chat.id)
            ctx["chat"]["admins"] = [
                a.user.first_name or a.user.username or str(a.user.id)
                for a in admins[:10]
            ]
        except TelegramError:
            ctx["chat"]["admins"] = []

    # ===== 回复上下文 =====
    if msg.reply_to_message:
        reply = msg.reply_to_message
        ru = reply.from_user
        ctx["reply"] = {
            "text": reply.text or reply.caption or "[非文本]",
        }
        if ru:
            ctx["reply"]["user"] = f"{ru.first_name or ''} {ru.last_name or ''}".strip() or ru.username or str(ru.id)

    # ===== 提及 =====
    bot_username = context.bot.username
    if msg.text and bot_username:
        ctx["mentioned"] = f"@{bot_username}" in msg.text

    return ctx


def format_context(ctx: dict) -> str:
    """结构化上下文 → 紧凑文本，注入 System Prompt 尾部。"""
    if not ctx:
        return ""

    lines = []

    chat = ctx.get("chat", {})
    user = ctx.get("user", {})
    reply = ctx.get("reply", {})

    # 环境
    type_label = {"private": "私聊", "group": "群聊", "supergroup": "群聊", "channel": "频道"}.get(chat.get("type", ""), chat.get("type", ""))
    lines.append(f"<chat type={chat.get('type')} title=\"{chat.get('title', '')}\">{type_label}: {chat.get('title', '')}")
    if chat.get("member_count"):
        lines[-1] += f", {chat['member_count']}人"
    if chat.get("admins"):
        lines[-1] += f", 管理员:{','.join(chat['admins'][:5])}"
    lines[-1] += "</chat>"

    # 用户
    if user.get("name"):
        user_line = f"<user name=\"{user['name']}\""
        if user.get("username"):
            user_line += f" username=\"{user['username']}\""
        if user.get("is_admin"):
            user_line += " role=\"admin\""
        user_line += "/>"
        lines.append(user_line)

    # 回复
    if reply.get("text"):
        r_user = reply.get("user", "")
        lines.append(f"<reply_to user=\"{r_user}\">{(reply['text'] or '')[:100]}</reply_to>")

    # 提及
    if ctx.get("mentioned"):
        lines.append("<mentioned/>")

    return "\n".join(lines)
