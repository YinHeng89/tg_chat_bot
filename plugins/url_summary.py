"""URL 内容提取与总结连接器。"""

import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from plugins.base import BasePlugin


class URLSummaryPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "url_summary"

    @property
    def description(self) -> str:
        return "提取并总结网页 URL 的内容"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return ""

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        url = params.get("query", "") or params.get("url", "")
        if not url:
            return "请提供 URL 地址"

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; TGChatBot/1.0)"
                }
                response = await client.get(url, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 移除 script/style 标签
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title else "无标题"

            # 提取正文
            text = soup.get_text(separator="\n", strip=True)
            # 清理多余空行
            text = re.sub(r'\n{3,}', '\n\n', text)
            # 截取前 3000 字
            if len(text) > 3000:
                text = text[:3000] + "\n... (内容过长已截断)"

            return f"页面标题: {title}\n\n内容摘要:\n{text}"

        except httpx.HTTPError as e:
            return f"无法访问该页面: {e}"
        except Exception as e:
            return f"提取内容失败: {e}"
