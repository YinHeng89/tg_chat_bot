"""图片生成连接器 — 使用 OpenAI 兼容 API 生成图片。"""

from typing import Optional

from plugins.base import BasePlugin
from utils.logger import logger


class ImageGenPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "image_gen"

    @property
    def description(self) -> str:
        return "根据文本描述生成图片（需要支持图片生成的 API）"

    @property
    def auto_trigger(self) -> bool:
        return False

    @property
    def manual_command(self) -> str:
        return "draw"

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        prompt = params.get("query", "") or params.get("prompt", "")
        if not prompt:
            return "请提供图片描述，例如: /draw 一只橘猫在喝茶"

        from core.llm import llm_manager

        # 遍历启用的后端，找第一个有 api_key 的
        api_key = ""
        base_url = ""
        for cfg in llm_manager.get_all():
            if cfg.get("enabled") and cfg.get("api_key"):
                api_key = cfg["api_key"]
                base_url = cfg.get("base_url", "https://api.openai.com/v1")
                break

        if not api_key:
            return "图片生成需要至少一个模型配置了 API Key"

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            response = await client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            return f"[IMAGE:{image_url}]已生成图片: {prompt[:50]}..."

        except Exception as e:
            logger.error(f"图片生成失败: {e}")
            return f"图片生成失败: {e}"
