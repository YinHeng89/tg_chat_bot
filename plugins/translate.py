"""翻译连接器 — 使用 LLM 进行翻译。"""

from typing import Optional

from plugins.base import BasePlugin


class TranslatePlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "translate"

    @property
    def description(self) -> str:
        return "多语言翻译助手，自动检测语言并翻译为中文"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return "translate"

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        text = params.get("query", "") or params.get("text", "")
        target_lang = params.get("target", "中文")

        if not text:
            return "请提供需要翻译的内容，例如: /translate Hello world"

        prompt = (
            f"请将以下内容翻译为{target_lang}，只返回翻译结果，不要添加任何解释:\n\n{text}"
        )

        try:
            from core.llm import llm_manager
            messages = [{"role": "user", "content": prompt}]
            result = await llm_manager.chat(messages, max_tokens=2000)
            return result.text if hasattr(result, 'text') else str(result)
        except Exception as e:
            return f"翻译失败: {e}"
