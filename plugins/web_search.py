"""联网搜索连接器 — 使用 DuckDuckGo (ddgs) 免费搜索。"""

from typing import Optional
import httpx

from plugins.base import BasePlugin
from utils.logger import logger


class WebSearchPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "联网搜索，获取实时信息"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return "search"

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        query = params.get("query", "") or params.get("input", "")
        if not query:
            return "请提供搜索关键词"

        # 方式1: ddgs (新版)
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            if results:
                return self._format_results(query, results)
        except Exception as e1:
            logger.warning(f"ddgs 失败: {e1}")

        # 方式2: DuckDuckGo Instant Answer API (无需库)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com",
                    params={"q": query, "format": "json", "no_html": 1, "t": "tg_chat_bot"},
                    headers={"User-Agent": "TG-Chat-Bot/1.0"},
                )
                data = resp.json()
                abstract = data.get("AbstractText", "")
                related = data.get("RelatedTopics", [])
                if abstract:
                    parts = [f"关于 '{query}':\n{abstract}"]
                    for t in related[:3]:
                        if isinstance(t, dict) and t.get("Text"):
                            parts.append(f"- {t['Text'][:200]}")
                    return "\n".join(parts)
        except Exception as e2:
            logger.warning(f"DDG API 失败: {e2}")

        return f"搜索 '{query}' 暂时不可用，请稍后重试"

    def _format_results(self, query: str, results: list) -> str:
        parts = [f"关于 '{query}' 的搜索结果:\n"]
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "无标题")
            body = r.get("body", r.get("snippet", ""))[:200]
            href = r.get("href", r.get("link", ""))
            parts.append(f"{i}. {title}\n   {body}\n   {href}\n")
        return "\n".join(parts)
