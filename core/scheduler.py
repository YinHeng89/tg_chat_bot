"""定时任务调度器 — 待办提醒 + Bark 心跳。"""

import asyncio
import httpx
from datetime import datetime, timedelta

from core.bot_manager import bot_manager
from core.llm import llm_manager
from storage.database import (
    get_due_tasks, mark_task_done, reschedule_task, mark_task_skipped,
    get_stats, get_setting_bool, get_setting,
)
from utils.helpers import get_now, get_now_str
from utils.logger import logger


async def start_scheduler(tick_seconds: int = 30):
    """启动调度器主循环（挂载在主事件循环上）。"""
    logger.info(f"调度器已启动（轮询间隔 {tick_seconds}s）")

    # 启动时补发宽限期内的过期任务
    await _catchup_missed_tasks()

    # 首次心跳
    if await get_setting_bool("heartbeat_enabled", False):
        await _send_heartbeat()

    while True:
        try:
            await _tick()
            await _heartbeat_tick()
        except Exception as e:
            logger.error(f"调度器 tick 异常: {e}")

        await asyncio.sleep(tick_seconds)


async def _catchup_missed_tasks(grace_minutes: int = 5):
    """服务重启后补发宽限期内的到期任务。"""
    from storage.database import get_catchup_tasks
    tasks = await get_catchup_tasks(grace_minutes)
    if not tasks:
        return
    logger.info(f"补发宽限期内到期任务: {len(tasks)} 个")
    for task in tasks:
        await _fire_task(task, on_restart=True)


async def _tick():
    """每轮 tick：查找到期任务并触发。"""
    now_str = get_now_str()
    tasks = await get_due_tasks(now_str)
    if not tasks:
        return
    for task in tasks:
        await _fire_task(task)


async def _fire_task(task: dict, on_restart: bool = False):
    """触发单个任务：尝试用指定 Bot 发消息，失败则换任意在线 Bot。"""
    task_id = task["id"]
    bot_id = task.get("bot_id", 0)
    chat_id = task.get("chat_id", "")
    title = task.get("title", "无内容")
    repeat_rule = task.get("repeat_rule", "")
    fire_at = task.get("fire_at", "")
    created_at = task.get("created_at", "")

    if not chat_id:
        logger.warning(f"任务 #{task_id}: 缺少 chat_id，标记跳过")
        await mark_task_skipped(task_id)
        return

    # 找到可用的 Bot：优先用任务关联的 bot，否则尝试所有在线 bot
    app = bot_manager._apps.get(bot_id)
    if not app:
        if bot_id != 0:
            logger.debug(f"任务 #{task_id}: Bot #{bot_id} 不在线，尝试其他 Bot")
        if bot_manager._apps:
            app = next(iter(bot_manager._apps.values()))
            for bid, a in bot_manager._apps.items():
                if a is app:
                    bot_id = bid
                    break
        if not app:
            logger.warning(f"任务 #{task_id}: 无在线 Bot，标记跳过")
            await mark_task_skipped(task_id)
            return

    # AI 生成提醒文案，失败则用简单模板兜底
    text = await _ai_reminder_text(title, fire_at, created_at, repeat_rule, on_restart)

    try:
        await app.bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"任务 #{task_id} 已触发: [{chat_id}] {title} (Bot #{bot_id})")
    except Exception as e:
        logger.error(f"发送任务 #{task_id} 提醒失败: {e}")
        await mark_task_skipped(task_id)
        return

    # 处理重复任务
    if repeat_rule:
        next_fire = _calc_next_fire(repeat_rule)
        if next_fire:
            await reschedule_task(task_id, next_fire)
            logger.info(f"重复任务 #{task_id} 下次触发: {next_fire}")
            return

    await mark_task_done(task_id)


async def _ai_reminder_text(title: str, fire_at: str, created_at: str,
                             repeat_rule: str, on_restart: bool) -> str:
    """让 AI 根据任务内容生成自然温馨的提醒文案。"""
    repeat_map = {"daily": "每天", "weekly": "每周", "hourly": "每小时"}
    repeat_text = repeat_map.get(repeat_rule, "")
    now = get_now()

    prompt = f"""你是用户的贴心助手。用户之前设置了以下提醒，现在时间到了，请你提醒用户。

提醒内容：{title}
创建时间：{created_at or '未知'}
计划触发：{fire_at or '未知'}
当前时间：{now.strftime('%Y-%m-%d %H:%M')}
重复规则：{repeat_text or '单次提醒'}
{'注意：这是服务重启后补发的过期提醒，请温和说明。' if on_restart else ''}

要求：
- 用温暖自然的口语提醒用户，不要死板地说「提醒您…」
- 保持核心提醒内容不变
- 根据内容类型适当加入关怀、鼓励或小幽默
- 比如「吃药」可以关心身体，「下班」可以恭喜结束一天，「开会」提醒做好准备
- 2-3句话即可，简洁有温度
- 如果内容是用户自己写的自然语言（如「要下班了」），就直接用它的语气发挥"""

    try:
        messages = [{"role": "user", "content": prompt}]
        result = await llm_manager.chat(messages, max_tokens=200)
        text = (result.text or "").strip()
        if text:
            logger.info(f"AI 提醒文案生成成功 ({len(text)} 字)")
            return text
    except Exception as e:
        logger.warning(f"AI 提醒文案生成失败，使用兜底文案: {e}")

    # 兜底：简单模板
    return f"⏰ {title}"


def _calc_next_fire(repeat_rule: str) -> str:
    """根据重复规则计算下次触发时间（返回 ISO 格式本地时间）。"""
    now = get_now()
    rule = repeat_rule.lower().strip()
    if rule == "daily":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    if rule == "hourly":
        return (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    if rule == "weekly":
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M:%S")
    # 尝试解析 "every N minutes/hours/days" 格式
    import re
    m = re.match(r"every\s+(\d+)\s*(minute|minutes|hour|hours|day|days)", rule)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if "hour" in unit:
            delta = timedelta(hours=n)
        elif "day" in unit:
            delta = timedelta(days=n)
        else:
            delta = timedelta(minutes=n)
        return (now + delta).strftime("%Y-%m-%d %H:%M:%S")
    return ""


# ===== Bark 心跳 =====

_heartbeat_last: str = ""


async def _heartbeat_tick():
    """检查是否需要发送心跳。"""
    enabled = await get_setting_bool("heartbeat_enabled", False)
    if not enabled:
        return

    interval = int(await get_setting("heartbeat_interval", "30"))  # 分钟
    now = get_now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    global _heartbeat_last
    if _heartbeat_last == now_str[: len(now_str) - 1]:  # 同一分钟内不重复
        return

    if _heartbeat_last:
        try:
            last_dt = datetime.strptime(_heartbeat_last, "%Y-%m-%d %H:%M")
            if (now - last_dt).total_seconds() < interval * 60:
                return
        except ValueError:
            pass

    _heartbeat_last = now_str
    await _send_heartbeat()


async def _send_heartbeat():
    """通过 Bark 推送心跳通知（自动识别官方/自建服务）。"""
    raw = await get_setting("heartbeat_bark_key", "")
    if not raw:
        logger.debug("心跳未配置 Bark 推送地址，跳过")
        return

    raw = raw.strip()
    if raw.startswith("http"):
        # 自建服务完整 URL：https://bark.example.com/KEY
        url_parts = raw.split("//", 1)[-1].split("/")
        bark_key = url_parts[-1] if url_parts[-1] else ""
        server = raw.rsplit("/", 1)[0]
        api_url = f"{server}/push" if not server.endswith("/push") else server
    else:
        # 官方服务：纯设备 Key
        bark_key = raw
        api_url = "https://api.day.app/push"

    stats = await get_stats(days=1)
    now = get_now()
    title = f"💓 Bot 存活 — {bot_manager.running_count} 实例运行中"
    body = (
        f"时间: {now.strftime('%H:%M:%S')}\n"
        f"近24h: {stats['total_messages']} 条消息 / {stats['unique_users']} 个用户\n"
        f"群聊: {stats['active_chats']} | Token: {stats['total_tokens']}"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(api_url, json={
                "device_key": bark_key.strip(),
                "title": title,
                "body": body,
                "group": "TG Bot",
            })
            if resp.status_code == 200:
                logger.info("心跳已推送到 Bark")
            else:
                err_text = resp.text[:200] if len(resp.text) > 200 else resp.text
                logger.warning(f"Bark 推送失败: {resp.status_code} {err_text}")
    except Exception as e:
        logger.warning(f"Bark 推送异常: {e}")
