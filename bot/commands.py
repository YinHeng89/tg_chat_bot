"""命令处理系统 — 所有 / 命令的实现。"""

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import core_config
from core.llm import llm_manager
from core.memory import memory_manager
from plugins.registry import plugin_registry
from storage.database import (
    get_stats,
    get_session_info, add_blacklist, remove_blacklist, get_blacklist,
)
from utils.helpers import parse_command_args
from utils.logger import logger


async def handle_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """命令入口，解析命令并分发。"""
    text = update.message.text
    command, args = parse_command_args(text)

    user = update.effective_user
    chat = update.effective_chat
    chat_id = str(chat.id)

    # 确保核心配置已加载
    admin_ids = await core_config.get("admin_ids", [])
    is_admin = str(user.id) in [str(a) for a in admin_ids]

    logger.info(f"收到命令 /{command} (user={user.id}, is_admin={is_admin})")

    # 命令路由
    command_map = {
        "start": cmd_start,
        "help": cmd_help,
        "chat": cmd_chat,
        "clear": cmd_clear,
        "history": cmd_history,
        "status": cmd_status,
        "search": cmd_search,
        "weather": cmd_weather,
        "translate": cmd_translate,
        "calc": cmd_calc,
        "draw": cmd_draw,
        "news": cmd_news,
        "connectors": cmd_connectors,
        "connector": cmd_connector,
        "admin": cmd_admin,
        "switch_model": cmd_switch_model,
        "list_models": cmd_list_models,
        "whitelist": cmd_whitelist,
        "blacklist": cmd_blacklist,
        "stats": cmd_stats,
        "broadcast": cmd_broadcast,
        "plugin": cmd_plugin,
    }

    handler = command_map.get(command)
    if handler:
        if command in ("admin", "switch_model", "list_models", "whitelist",
                       "blacklist", "stats", "broadcast", "plugin"):
            if not is_admin:
                await update.message.reply_text("此命令仅管理员可用。")
                return
        await handler(update, context, args, chat_id)
    else:
        # 未知命令，尝试作为对话处理
        from bot.conversation import handle_conversation
        await handle_conversation(update, context, chat_id, user.id, update.message.text)


# ===== 通用命令 =====

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    args: str, chat_id: str):
    """启动机器人。"""
    bot_name = context.bot.first_name or "AI 助手"
    welcome = (
        f"你好！我是 {bot_name}，一个智能聊天机器人。\n\n"
        f"我可以:\n"
        f"  - 和你聊天对话（支持上下文记忆）\n"
        f"  - 联网搜索实时信息\n"
        f"  - 读取/总结网页链接\n"
        f"  - 查询天气\n"
        f"  - 翻译多语言\n"
        f"  - 数学计算\n"
        f"  - 分析图片内容\n\n"
        f"发送 /help 查看所有功能"
    )
    await update.message.reply_text(welcome)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   args: str, chat_id: str):
    """查看帮助。"""
    help_text = (
        "*通用命令*\n"
        "/start - 启动机器人\n"
        "/help - 查看帮助\n"
        "/chat <内容> - 在群聊中对话\n"
        "/clear - 清空当前对话上下文\n"
        "/history - 查看当前对话历史\n"
        "/status - 查看机器人状态\n\n"
        "*连接器命令*\n"
        "/search <关键词> - 联网搜索\n"
        "/weather <城市> - 查询天气\n"
        "/translate <内容> - 翻译\n"
        "/calc <表达式> - 计算\n"
        "/draw <描述> - 生成图片\n"
        "/news - 最新新闻\n"
        "/connectors - 查看所有连接器\n"
    )
    is_admin = await _is_admin(update)
    if is_admin:
        help_text += (
            "\n*管理员命令*\n"
            "/admin - 管理面板\n"
            "/switch_model <模型> - 切换模型\n"
            "/list_models - 列出可用模型\n"
            "/stats - 使用统计\n"
            "/blacklist add/remove <ID> - 黑名单管理\n"
            "/broadcast <消息> - 广播消息\n"
        )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   args: str, chat_id: str):
    """群聊中指定对话。"""
    if not args:
        await update.message.reply_text("请提供对话内容，例如: /chat 今天天气怎么样")
        return
    from bot.conversation import handle_conversation
    await handle_conversation(update, context, chat_id, update.effective_user.id, args)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    args: str, chat_id: str):
    """清空当前对话上下文。"""
    from bot.conversation import _get_bot_id
    bot_id = await _get_bot_id(context.bot.token)
    await memory_manager.clear(bot_id, chat_id)
    await update.message.reply_text("当前对话上下文已清空。")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      args: str, chat_id: str):
    """查看当前对话历史。"""
    from bot.conversation import _get_bot_id
    bot_id = await _get_bot_id(context.bot.token)
    messages = await memory_manager.get_history(bot_id, chat_id)
    if not messages:
        await update.message.reply_text("当前没有对话历史。")
        return

    parts = ["*当前对话历史:*\n"]
    for i, msg in enumerate(messages[-10:], 1):
        role_tag = "用户" if msg.role == "user" else "AI"
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        parts.append(f"{i}. [{role_tag}] {content}")

    await update.message.reply_text("\n".join(parts), parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     args: str, chat_id: str):
    """查看机器人状态。"""
    from bot.conversation import _get_bot_id
    bot_id = await _get_bot_id(context.bot.token)
    session = await get_session_info(bot_id, chat_id)
    plugins = plugin_registry.get_all()
    enabled_count = sum(1 for p in plugins if p["enabled"])
    models = llm_manager.get_all()
    active_models = [m["name"] for m in models if m["enabled"] and m["has_key"]]

    bot_name = context.bot.first_name or "AI 助手"
    status_text = (
        f"*{bot_name} 状态*\n\n"
        f"主模型: {llm_manager.primary or '无'}\n"
        f"可用模型: {', '.join(active_models) if active_models else '无'}\n"
        f"启用插件: {enabled_count}/{len(plugins)}\n"
    )
    if session:
        status_text += (
            f"当前对话: {session.get('message_count', 0)} 条消息\n"
            f"Token 消耗: {session.get('total_tokens', 0)}\n"
        )
    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)


# ===== 连接器命令 =====

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     args: str, chat_id: str):
    """联网搜索。"""
    if not args:
        await update.message.reply_text("请提供搜索关键词，例如: /search Python教程")
        return
    await update.message.reply_text("正在搜索...")
    result = await plugin_registry.execute("web_search", {"query": args})
    await update.message.reply_text(result)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      args: str, chat_id: str):
    """天气查询。"""
    if not args:
        await update.message.reply_text("请提供城市名称，例如: /weather 北京")
        return
    result = await plugin_registry.execute("weather", {"query": args})
    await update.message.reply_text(result)


async def cmd_translate(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        args: str, chat_id: str):
    """翻译。"""
    if not args:
        await update.message.reply_text("请提供翻译内容，例如: /translate Hello world")
        return
    result = await plugin_registry.execute("translate", {
        "query": args,
        "target": "中文"
    }, {"llm_manager": llm_manager})
    await update.message.reply_text(result)


async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   args: str, chat_id: str):
    """计算。"""
    if not args:
        await update.message.reply_text("请提供表达式，例如: /calc 1024 * 768")
        return
    result = await plugin_registry.execute("calculator", {"query": args})
    await update.message.reply_text(result)


async def cmd_draw(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   args: str, chat_id: str):
    """图片生成。"""
    if not args:
        await update.message.reply_text("请提供图片描述，例如: /draw 一只橘猫在喝茶")
        return
    await update.message.reply_text("正在生成图片...")
    result = await plugin_registry.execute("image_gen", {
        "query": args,
    }, {"llm_manager": llm_manager})
    if result.startswith("[IMAGE:"):
        # 提取图片 URL 并发送
        import re
        match = re.search(r'\[IMAGE:(.*?)\]', result)
        if match:
            image_url = match.group(1)
            await update.message.reply_photo(photo=image_url, caption=args[:200])
            return
    await update.message.reply_text(result)


async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   args: str, chat_id: str):
    """获取新闻。"""
    await update.message.reply_text("新闻功能开发中...")


async def cmd_connectors(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         args: str, chat_id: str):
    """查看所有连接器状态。"""
    plugins = plugin_registry.get_all()
    if not plugins:
        await update.message.reply_text("没有可用的连接器。")
        return

    parts = ["*连接器状态:*\n"]
    for p in plugins:
        status_tag = "[ON]" if p["enabled"] else "[OFF]"
        cmd = f" /{p['manual_command']}" if p["manual_command"] else ""
        parts.append(f"{status_tag} *{p['name']}*{cmd} - {p['description']}")

    await update.message.reply_text("\n".join(parts), parse_mode=ParseMode.MARKDOWN)


async def cmd_connector(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        args: str, chat_id: str):
    """启用/禁用连接器。/connector enable/disable <name>"""
    parts = args.split()
    if len(parts) < 2:
        await update.message.reply_text("用法: /connector enable/disable <名称>")
        return

    action = parts[0].lower()
    name = parts[1]

    if action == "enable":
        if plugin_registry.enable(name):
            await update.message.reply_text(f"连接器 '{name}' 已启用。")
        else:
            await update.message.reply_text(f"未找到连接器 '{name}'。")
    elif action == "disable":
        plugin_registry.disable(name)
        await update.message.reply_text(f"连接器 '{name}' 已禁用。")
    else:
        await update.message.reply_text("用法: /connector enable/disable <名称>")


# ===== 管理员命令 =====

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    args: str, chat_id: str):
    """管理员面板。"""
    stats = await get_stats(7)
    admin_text = (
        "*管理员面板*\n\n"
        f"最近 7 天:\n"
        f"  消息数: {stats['total_messages']}\n"
        f"  Token: {stats['total_tokens']}\n"
        f"  活跃用户: {stats['unique_users']}\n"
        f"  活跃会话: {stats['active_chats']}\n\n"
        f"命令:\n"
        f"  /switch_model <模型> - 切换模型\n"
        f"  /list_models - 列出可用模型\n"
        f"  /stats - 详细统计\n"
        f"  /blacklist add/remove <ID> - 黑名单管理\n"
        f"  /plugin enable/disable <名称> - 插件管理\n"
    )
    await update.message.reply_text(admin_text, parse_mode=ParseMode.MARKDOWN)


async def cmd_switch_model(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           args: str, chat_id: str):
    """切换 LLM 模型。"""
    if not args:
        await update.message.reply_text("请指定模型名称，例如: /switch_model gpt-4o")
        return

    await core_config.set("default_llm", args)
    await update.message.reply_text(f"默认模型已切换为: {args}")


async def cmd_list_models(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          args: str, chat_id: str):
    """列出可用模型。"""
    models = llm_manager.get_all()
    if not models:
        await update.message.reply_text("没有可用的模型。")
        return

    parts = ["*模型列表:*\n"]
    for i, m in enumerate(models):
        role = "[主]" if i == 0 else "[备用]"
        key_status = " (已配置)" if m["has_key"] else " (未配置Key)"
        enabled_status = " (ON)" if m["enabled"] else " (OFF)"
        parts.append(f"  {role} {m['name']} [{m['provider']}] - {m['model']}{key_status}{enabled_status}")

    await update.message.reply_text("\n".join(parts), parse_mode=ParseMode.MARKDOWN)


async def cmd_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        args: str, chat_id: str):
    """管理白名单。"""
    await update.message.reply_text("白名单管理请通过 Web 管理面板操作。")


async def cmd_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        args: str, chat_id: str):
    """管理黑名单。"""
    parts = args.split()
    if len(parts) < 2:
        await update.message.reply_text("用法: /blacklist add/remove <用户ID>")
        return

    action = parts[0].lower()
    try:
        user_id = int(parts[1])
    except ValueError:
        await update.message.reply_text("用户 ID 必须是数字。")
        return

    if action == "add":
        reason = " ".join(parts[2:]) if len(parts) > 2 else ""
        await add_blacklist(user_id, reason)
        await update.message.reply_text(f"用户 {user_id} 已加入黑名单。")
    elif action == "remove":
        await remove_blacklist(user_id)
        await update.message.reply_text(f"用户 {user_id} 已从黑名单移除。")
    else:
        await update.message.reply_text("用法: /blacklist add/remove <用户ID>")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    args: str, chat_id: str):
    """查看使用统计。"""
    days = 7
    if args:
        try:
            days = int(args)
        except ValueError:
            pass

    stats = await get_stats(days)
    text = f"*最近 {days} 天统计:*\n\n"
    text += f"总消息数: {stats['total_messages']}\n"
    text += f"总 Token: {stats['total_tokens']}\n"
    text += f"独立用户: {stats['unique_users']}\n"
    text += f"活跃会话: {stats['active_chats']}\n"

    if stats["by_model"]:
        text += "\n*按模型统计:*\n"
        for m in stats["by_model"]:
            text += f"  {m['model']}: {m['count']} 次, {m['tokens']} tokens\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        args: str, chat_id: str):
    """管理员广播消息。"""
    if not args:
        await update.message.reply_text("请提供广播内容。")
        return
    await update.message.reply_text(f"广播功能开发中...\n消息: {args[:200]}")


async def cmd_plugin(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     args: str, chat_id: str):
    """插件管理（管理员）。"""
    await cmd_connector(update, context, args, chat_id)


async def _is_admin(update: Update) -> bool:
    """检查当前用户是否为管理员。"""
    user = update.effective_user
    if not user:
        return False
    admin_ids = await core_config.get("admin_ids", [])
    return str(user.id) in [str(a) for a in admin_ids]
