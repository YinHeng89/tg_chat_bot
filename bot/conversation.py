"""对话逻辑编排 — bot_id 隔离，结构化上下文。"""

import base64
import json
from datetime import datetime
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.llm import llm_manager
from core.memory import memory_manager
from plugins.registry import plugin_registry
from storage.database import record_usage, get_db, compress_conversation, should_compress, get_model_configs
from bot.context import build_context, format_context
from bot.settings import get_bot_structured, get_bot_setting_int, build_agent_prompt, get_bot_allowed_models
from utils.helpers import extract_urls, truncate_text, md_to_html
from utils.logger import logger


async def _get_bot_id(bot_token: str) -> int:
    """从 bot_token 获取 bot_id。"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM bots WHERE bot_token = ?", (bot_token,))
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await db.close()


async def handle_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               chat_id: str, user_id: int, text: str):
    if not text.strip():
        return

    bot_token = context.bot.token
    bot_id = await _get_bot_id(bot_token)
    allowed_models = await get_bot_allowed_models(bot_token)

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception:
        pass  # typing 超时不阻塞对话

    try:
        # URL 自动摘要
        urls = extract_urls(text)
        if urls and plugin_registry.is_enabled("url_summary"):
            for url in urls[:2]:
                summary = await plugin_registry.execute("url_summary", {"query": url},
                    {"user_id": user_id, "chat_id": chat_id})
                if summary:
                    text = f"{text}\n\n[链接摘要 - {url}]\n{summary}"

        structured = await get_bot_structured(bot_token)
        system_prompt = build_agent_prompt(structured)
        max_history = await get_bot_setting_int(bot_token, "max_history", 20)

        # 注入结构化上下文 (<user> <chat> <reply_to> ...)
        ctx = await build_context(update, context)
        if ctx:
            ctx_text = format_context(ctx)
            if ctx_text:
                system_prompt = f"{system_prompt}\n\n{ctx_text}"
                # 把时间直接塞到用户消息前面（LLM 不会质疑对话里的时间）
                now = datetime.now()
                tz_name = now.astimezone().tzname() or ""
                text = f"[系统: 现在是{now.strftime('%Y年%m月%d日 %A %H:%M')}({tz_name})]\n{text}"

        # 群聊：每条消息前加上发送者名字，让 LLM 能区分谁说了什么
        chat_obj = update.effective_chat
        if chat_obj and chat_obj.type in ("group", "supergroup"):
            sender = update.effective_user
            sender_name = (f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                           or sender.username or str(user_id))
            text = f"[{sender_name}]: {text}"

        await memory_manager.add_user_message(bot_id, chat_id, user_id, text, max_history)
        messages = await memory_manager.get_context_messages(bot_id, chat_id, system_prompt, max_history)

        # 工具调用：如果启用了插件，传给 LLM 自动决策
        tools = plugin_registry.get_tool_definitions()
        if tools:
            async def tool_handler(name, args):
                # 将所有参数传给插件（cli 需要 command，web_search 需要 query 等）
                return await plugin_registry.execute(name, args, {"user_id": user_id, "chat_id": chat_id})
            result = await llm_manager.chat_with_tools(messages, tools, tool_handler, max_tokens=2000, allowed_model_ids=allowed_models)
        else:
            result = await llm_manager.chat(messages, max_tokens=2000, allowed_model_ids=allowed_models)

        reply = result.text or "抱歉，我没能生成有效的回复。"
        model_name = result.model or "unknown"
        await memory_manager.add_assistant_message(bot_id, chat_id, user_id, reply, model=model_name, max_history=max_history)
        await record_usage(chat_id, user_id, model_name, result.total_tokens)

        # 自动压缩：超过 30 条消息时，LLM 自动摘要旧消息
        if await should_compress(bot_id, chat_id, 30):
            try:
                summary_prompt = "请用一句话总结以下对话的关键信息（人物、话题、结论），不超过 100 字。"
                msgs = await memory_manager.get_context_messages(bot_id, chat_id, summary_prompt, 15)
                summary_result = await llm_manager.chat(msgs, max_tokens=200, allowed_model_ids=allowed_models)
                summary = summary_result.text if hasattr(summary_result, 'text') else str(summary_result)
                await compress_conversation(bot_id, chat_id, summary, keep_latest=8)
                logger.info(f"对话自动压缩完成: bot={bot_id} chat={chat_id}")
            except Exception as e:
                logger.warning(f"压缩失败: {e}")

        reply = truncate_text(reply, 4000)
        quote_mode = await get_bot_setting_int(bot_token, "reply_with_quote", 1)
        try:
            html_reply = md_to_html(reply)
            if quote_mode:
                await update.message.reply_text(html_reply, parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_message(chat_id=chat_id, text=html_reply, parse_mode=ParseMode.HTML)
        except Exception:
            if quote_mode:
                await update.message.reply_text(reply)
            else:
                await context.bot.send_message(chat_id=chat_id, text=reply)

    except Exception as e:
        err_msg = str(e)
        logger.error(f"对话处理失败 (chat={chat_id}): {err_msg}")
        # 根据真实状态判断错误原因
        if not llm_manager.backends:
            await update.message.reply_text("系统没有可用的模型，请先在管理后台配置并启用模型。")
        elif allowed_models:
            enabled_ids = {c["id"] for c in llm_manager.get_all() if c["enabled"]}
            if not set(allowed_models) & enabled_ids:
                await update.message.reply_text("这个 Bot 指定的模型都不在可用列表中，请管理员在设置中重新选择。")
            else:
                await update.message.reply_text(f"模型调用失败：{err_msg}")
        else:
            await update.message.reply_text(f"模型调用失败：{err_msg}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return

    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    chat_id = str(chat.id)
    user_id = user.id
    bot_token = context.bot.token
    bot_id = await _get_bot_id(bot_token)
    allowed_models = await get_bot_allowed_models(bot_token)

    # 图片专用模型路由：优先 Bot 指定 → 全局视觉模型 → 碰运气
    # 视觉能力完全由模型配置中的 capabilities.vision 手动控制
    all_cfgs = llm_manager.get_all()
    db_cfgs = {c["id"]: c for c in await get_model_configs()}

    def _model_supports_vision(cfg_id: int) -> bool:
        db_cfg = db_cfgs.get(cfg_id, {})
        try:
            caps = json.loads(db_cfg.get("capabilities") or "{}") if db_cfg.get("capabilities") else {}
            return bool(caps.get("vision", False))
        except Exception:
            return False

    vision_ids = [c["id"] for c in all_cfgs if _model_supports_vision(c["id"]) and c["enabled"]]
    text_ids = [c["id"] for c in all_cfgs if c["enabled"]]

    if allowed_models:
        photo_model_ids = [mid for mid in allowed_models if mid in vision_ids]
        if not photo_model_ids:
            # Bot 允许的模型都不支持视觉，再尝试全局视觉模型
            photo_model_ids = vision_ids[:1] if vision_ids else []
            if photo_model_ids:
                logger.info(f"图片处理: Bot 指定模型都不支持视觉，改用全局视觉模型")
    else:
        photo_model_ids = vision_ids[:1] if vision_ids else []

    if not photo_model_ids:
        logger.info("图片处理: 无可用视觉模型，转交给文字流程处理")
        caption = update.message.caption or ""
        if caption.strip():
            await handle_conversation(update, context, chat_id, user_id, caption)
        return

    if not plugin_registry.is_enabled("image_understand"):
        await update.message.reply_text("图片理解功能未启用。")
        return

    photo = update.message.photo[-1]
    caption = update.message.caption or "请描述这张图片的内容"

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        structured = await get_bot_structured(bot_token)
        system_prompt = build_agent_prompt(structured)
        max_history = await get_bot_setting_int(bot_token, "max_history", 20)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": caption},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}", "detail": "auto"}}
            ]}
        ]

        logger.info(f"图片处理: 发送图片，大小={len(image_base64)//1024}KB, caption=\"{caption[:50]}\", vision_models={photo_model_ids}")
        result = await llm_manager.chat(messages, max_tokens=2000, allowed_model_ids=photo_model_ids)

        reply = result.text or "抱歉，图片分析失败。"
        sender_name = (f"{user.first_name or ''} {user.last_name or ''}".strip()
                       or user.username or str(user_id))
        text_pfx = f"[{sender_name}]: " if chat.type in ("group", "supergroup") else ""
        await memory_manager.add_user_message(bot_id, chat_id, user_id, f"{text_pfx}[图片] {caption}", max_history)
        model_name = result.model or "unknown"
        await memory_manager.add_assistant_message(bot_id, chat_id, user_id, reply, model=model_name, max_history=max_history)
        await record_usage(chat_id, user_id, model_name, result.total_tokens)

        reply = truncate_text(reply, 4000)
        quote_mode = await get_bot_setting_int(bot_token, "reply_with_quote", 1)
        try:
            html_reply = md_to_html(reply)
            if quote_mode:
                await update.message.reply_text(html_reply, parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_message(chat_id=chat_id, text=html_reply, parse_mode=ParseMode.HTML)
        except Exception:
            if quote_mode:
                await update.message.reply_text(reply)
            else:
                await context.bot.send_message(chat_id=chat_id, text=reply)

    except Exception as e:
        err_msg = str(e)
        model_info = "unknown"
        try:
            cfgs = llm_manager.get_all()
            for c in cfgs:
                if c["id"] in photo_model_ids:
                    model_info = f"{c['name']}({c['model']})"; break
        except Exception: pass
        except Exception: pass
        logger.error(f"图片处理失败 [模型={model_info}]: {err_msg}")
        if not llm_manager.backends:
            await context.bot.send_message(chat_id=chat_id, text="系统没有可用的模型，请先在管理后台配置并启用模型。")
        elif allowed_models:
            enabled_ids = {c["id"] for c in llm_manager.get_all() if c["enabled"]}
            if not set(allowed_models) & enabled_ids:
                await context.bot.send_message(chat_id=chat_id, text="这个 Bot 指定的模型都不在可用列表中，请管理员在设置中重新选择。")
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"模型调用失败：{err_msg}")
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"模型调用失败：{err_msg}")
