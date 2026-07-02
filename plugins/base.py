"""插件基类 — 所有连接器继承此基类。"""

from abc import ABC, abstractmethod
from typing import Optional


class BasePlugin(ABC):
    """连接器（插件）基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称，唯一标识。"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述。"""
        ...

    @property
    def auto_trigger(self) -> bool:
        """是否允许 AI 自动调用（默认 True）。"""
        return True

    @property
    def manual_command(self) -> str:
        """手动触发的命令名，空字符串表示不提供手动命令。"""
        return ""

    @abstractmethod
    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        """执行插件逻辑。

        Args:
            params: 调用参数，至少包含 "query" 或 "input" 键
            context: 上下文信息（user_id, chat_id, 消息原文等）

        Returns:
            插件执行结果字符串
        """
        ...

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
                        "query": {
                            "type": "string",
                            "description": "查询参数"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
