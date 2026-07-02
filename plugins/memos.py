"""Memos 连接器 — 查询、写入、编辑 Memos 备忘录。"""

import os
from typing import Optional
import httpx

from plugins.base import BasePlugin
from utils.logger import logger


class MemosPlugin(BasePlugin):
    """Memos 备忘录连接器。

    支持操作：
      - 列出/搜索 memos
      - 创建新 memo
      - 更新已有 memo
      - 删除 memo
      - 获取单个 memo 详情
    """

    def __init__(self):
        self._base_url = os.getenv("MEMOS_API_URL", "").rstrip("/")
        self._api_key = os.getenv("MEMOS_API_KEY", "")

    @property
    def name(self) -> str:
        return "memos"

    @property
    def description(self) -> str:
        return "查询、创建、编辑和删除 Memos 备忘录（个人笔记/知识库）"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return "memos"

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        action = params.get("action", "list")
        query = params.get("query", "") or params.get("content", "")
        memo_id = params.get("memo_id", "")
        visibility = params.get("visibility", "PRIVATE")

        if not self._base_url or not self._api_key:
            return "Memos 服务未配置，请检查 MEMOS_API_URL 和 MEMOS_API_KEY 环境变量"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if action == "list" or action == "search":
                    return await self._list_memos(client, query)
                elif action == "create":
                    return await self._create_memo(client, query, visibility)
                elif action == "update":
                    return await self._update_memo(client, memo_id, query, visibility)
                elif action == "delete":
                    return await self._delete_memo(client, memo_id)
                elif action == "get":
                    return await self._get_memo(client, memo_id)
                else:
                    return f"不支持的操作: {action}，可用操作: list, search, create, update, delete, get"
        except httpx.ConnectError:
            return "无法连接到 Memos 服务，请检查网络和服务地址"
        except httpx.TimeoutException:
            return "Memos 服务请求超时"
        except Exception as e:
            logger.error(f"Memos 操作失败: {e}")
            return f"Memos 操作失败: {e}"

    async def _list_memos(self, client: httpx.AsyncClient, query: str = "") -> str:
        """列出或搜索 memos。"""
        params = {"pageSize": 20}
        if query:
            # 使用 CEL 表达式搜索内容
            params["filter"] = f'content.contains("{query}")'

        resp = await client.get(
            f"{self._base_url}/api/v1/memos",
            headers=self._headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

        memos = data.get("memos", [])
        if not memos:
            return "暂无备忘录" if not query else f"未找到包含 '{query}' 的备忘录"

        lines = [f"📋 备忘录列表（共 {len(memos)} 条）:\n"]
        for i, m in enumerate(memos[:15], 1):
            content = (m.get("content") or m.get("snippet", ""))[:100]
            content = content.replace("\n", " ").strip()
            name = m.get("name", "")  # 格式: memos/xxx
            memo_id = name.split("/")[-1] if "/" in name else name
            pinned = "📌 " if m.get("pinned") else ""
            visibility = m.get("visibility", "PRIVATE")
            vis_label = {"PUBLIC": "公开", "PROTECTED": "保护", "PRIVATE": "私密"}.get(visibility, visibility)
            create_time = m.get("createTime", "")[:16].replace("T", " ")
            lines.append(f"{i}. [{vis_label}] {pinned}{content}")
            lines.append(f"   ID: {memo_id} | {create_time}")
            lines.append("")

        if len(memos) > 15:
            lines.append(f"... 还有 {len(memos) - 15} 条未显示，可使用更精确的关键词搜索")
        return "\n".join(lines)

    async def _create_memo(self, client: httpx.AsyncClient, content: str, visibility: str = "PRIVATE") -> str:
        """创建新的 memo。"""
        if not content:
            return "请提供备忘录内容"

        body = {
            "content": content,
            "visibility": visibility.upper(),
        }

        resp = await client.post(
            f"{self._base_url}/api/v1/memos",
            headers=self._headers,
            json=body,
        )
        resp.raise_for_status()
        memo = resp.json()
        name = memo.get("name", "")
        memo_id = name.split("/")[-1] if "/" in name else name
        return f"✅ 备忘录已创建 (ID: {memo_id})\n内容: {content[:200]}"

    @staticmethod
    def _extract_id(memo_id: str) -> str:
        """从任意格式中提取纯 memo ID（去掉 memos/ 前缀等）。"""
        if memo_id.startswith("memos/"):
            memo_id = memo_id.split("/", 1)[1]
        # 如果 AI 传了完整 URL，只取最后一段
        if "/" in memo_id:
            memo_id = memo_id.rsplit("/", 1)[-1]
        return memo_id

    async def _update_memo(self, client: httpx.AsyncClient, memo_id: str, content: str, visibility: str = "") -> str:
        """更新已有 memo。"""
        if not memo_id:
            return "请提供要更新的备忘录 ID"
        if not content and not visibility:
            return "请提供要更新的内容或可见性"

        pure_id = self._extract_id(memo_id)

        body = {}
        update_mask = []
        if content:
            body["content"] = content
            update_mask.append("content")
        if visibility:
            body["visibility"] = visibility.upper()
            update_mask.append("visibility")

        resp = await client.patch(
            f"{self._base_url}/api/v1/memos/{pure_id}",
            headers=self._headers,
            json=body,
            params={"updateMask": ",".join(update_mask)},
        )
        resp.raise_for_status()
        return f"✅ 备忘录 {pure_id} 已更新"

    async def _delete_memo(self, client: httpx.AsyncClient, memo_id: str) -> str:
        """删除 memo。"""
        if not memo_id:
            return "请提供要删除的备忘录 ID"

        pure_id = self._extract_id(memo_id)

        resp = await client.delete(
            f"{self._base_url}/api/v1/memos/{pure_id}",
            headers=self._headers,
        )
        resp.raise_for_status()
        return f"✅ 备忘录 {pure_id} 已删除"

    async def _get_memo(self, client: httpx.AsyncClient, memo_id: str) -> str:
        """获取单个 memo 详情。"""
        if not memo_id:
            return "请提供备忘录 ID"

        pure_id = self._extract_id(memo_id)

        resp = await client.get(
            f"{self._base_url}/api/v1/memos/{pure_id}",
            headers=self._headers,
        )
        resp.raise_for_status()
        memo = resp.json()

        content = memo.get("content", "")
        visibility = memo.get("visibility", "PRIVATE")
        vis_label = {"PUBLIC": "公开", "PROTECTED": "保护", "PRIVATE": "私密"}.get(visibility, visibility)
        create_time = memo.get("createTime", "")[:16].replace("T", " ")
        update_time = memo.get("updateTime", "")[:16].replace("T", " ")
        pinned = "📌 已置顶" if memo.get("pinned") else ""

        lines = [
            f"📝 备忘录详情",
            f"ID: {pure_id}",
            f"可见性: {vis_label}  {pinned}",
            f"创建: {create_time}",
            f"更新: {update_time}",
            f"",
            f"内容:",
            content,
        ]
        return "\n".join(lines)

    def get_tool_definition(self) -> dict:
        """返回 OpenAI Function Calling 格式的工具定义。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "search", "create", "update", "delete", "get"],
                            "description": "操作类型: list(列出最近备忘录), search(关键词搜索), create(创建备忘录), update(更新备忘录), delete(删除备忘录), get(查看备忘录详情)",
                        },
                        "query": {
                            "type": "string",
                            "description": "对于 list/search: 搜索关键词；对于 create: 备忘录内容；对于 update: 要更新的内容",
                        },
                        "memo_id": {
                            "type": "string",
                            "description": "备忘录 ID，用于 update/delete/get 操作",
                        },
                        "visibility": {
                            "type": "string",
                            "enum": ["PRIVATE", "PROTECTED", "PUBLIC"],
                            "description": "可见性: PRIVATE(仅自己), PROTECTED(登录用户), PUBLIC(所有人)，默认 PRIVATE",
                        },
                    },
                    "required": ["action"],
                },
            },
        }
