"""图片理解连接器 — 多模态分析图片内容。"""

from typing import Optional

from plugins.base import BasePlugin


class ImageUnderstandPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "image_understand"

    @property
    def description(self) -> str:
        return "分析图片内容，识别物体、场景、文字等"

    @property
    def auto_trigger(self) -> bool:
        return False  # 图片理解由 bot/conversation.py 的 handle_photo 直接处理

    @property
    def manual_command(self) -> str:
        return ""

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        # 图片理解需要 LLM 多模态能力
        # 由 bot/conversation.py 中的图片处理逻辑调用
        return "[图片分析] 此功能需要在对话中发送图片触发"
