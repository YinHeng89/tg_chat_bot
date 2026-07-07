"""定时提醒插件 — 用户通过自然语言创建待办/提醒。"""

from datetime import datetime, timedelta
from typing import Optional

from plugins.base import BasePlugin
from storage.database import add_task
from utils.helpers import get_now
from utils.logger import logger


class ReminderPlugin(BasePlugin):
    """根据用户自然语言创建定时提醒任务。"""

    @property
    def name(self) -> str:
        return "reminder"

    @property
    def description(self) -> str:
        return (
            "【必须调用】当用户要求在未来某个时间点提醒他某件事时，创建定时提醒任务。"
            "触发词包括但不限于：「提醒」「闹钟」「待办」「记一下」「别忘了」「稍后提醒」"
            "「X分钟后」「明天X点」「下周X」「定时」等。"
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
                        "title": {
                            "type": "string",
                            "description": "提醒的标题/内容，简洁明了地概括要提醒什么"
                        },
                        "delay_minutes": {
                            "type": "number",
                            "description": "多少分钟后提醒。如用户说「30分钟后提醒我」，此值为30。仅当用户给出了相对时间时填写"
                        },
                        "fire_at": {
                            "type": "string",
                            "description": "绝对提醒时间，ISO 格式（YYYY-MM-DD HH:MM:SS）。如用户说「明天下午3点提醒我开会」则转换为具体时间。仅当用户给出绝对时间时填写"
                        },
                        "repeat": {
                            "type": "string",
                            "description": "重复规则。'daily'=每天 / 'weekly'=每周 / 'hourly'=每小时 / 不填=单次"
                        }
                    },
                    "required": ["title"]
                }
            }
        }

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        title = params.get("title", "").strip()
        if not title:
            return "请提供提醒的内容。"

        context = context or {}
        bot_id = context.get("bot_id", 0)
        chat_id = context.get("chat_id", "")
        user_id = context.get("user_id", 0)

        if not chat_id:
            return "无法获取当前会话信息，请稍后重试。"

        # 解析时间
        fire_at = params.get("fire_at", "").strip() if isinstance(params.get("fire_at"), str) else ""
        delay_minutes = params.get("delay_minutes")

        # AI 可能传字符串数字，统一转 float
        if delay_minutes is not None:
            try:
                delay_minutes = float(delay_minutes)
            except (ValueError, TypeError):
                delay_minutes = None

        if delay_minutes and delay_minutes > 0:
            fire_at = (get_now() + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        elif fire_at:
            # 尝试规范化 AI 返回的时间格式
            fire_at = _normalize_datetime(fire_at)
        else:
            return "请提供提醒时间，例如「30分钟后」或「明天下午3点」。"

        if not fire_at:
            return "无法解析提醒时间，请换个方式描述时间。"

        # 校验时间不能是过去
        try:
            fire_dt = datetime.strptime(fire_at, "%Y-%m-%d %H:%M:%S")
            if fire_dt <= get_now():
                return f"提醒时间「{fire_at}」已过期，请设置一个未来的时间。"
        except ValueError:
            return f"时间格式不正确（{fire_at}），请重试。"

        repeat = params.get("repeat", "").strip().lower()

        task_id = await add_task(
            bot_id=bot_id,
            chat_id=chat_id,
            user_id=user_id,
            title=title,
            fire_at=fire_at,
            repeat_rule=repeat,
        )

        if not task_id:
            return "创建提醒失败，请稍后重试。"

        repeat_text = {"daily": "每天", "weekly": "每周", "hourly": "每小时"}.get(repeat, "")
        repeat_suffix = f"，{repeat_text}重复" if repeat_text else ""

        logger.info(f"reminder: user={user_id} chat={chat_id} 「{title}」→ {fire_at} {repeat or '单次'} (任务#{task_id})")
        return f"已创建提醒：{fire_at}「{title}」{repeat_suffix}，到点我会通知你。"


def _normalize_datetime(s: str) -> str:
    """尝试将各种 AI 返回的日期时间格式统一为 YYYY-MM-DD HH:MM:SS。"""
    if not s:
        return ""
    s = s.strip()
    # 常见变体
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y年%m月%d日 %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    # 如果只有日期没有时间，默认 09:00
    date_only = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]
    for fmt in date_only:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d 09:00:00")
        except ValueError:
            continue
    return ""
