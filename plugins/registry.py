"""插件注册中心 — 管理所有连接器的注册、启用/禁用和调用。"""

from typing import Optional

from plugins.base import BasePlugin
from plugins.web_search import WebSearchPlugin
from plugins.url_summary import URLSummaryPlugin
from plugins.weather import WeatherPlugin
from plugins.calculator import CalculatorPlugin
from plugins.translate import TranslatePlugin
from plugins.image_understand import ImageUnderstandPlugin
from plugins.image_gen import ImageGenPlugin
from plugins.code_runner import CodeRunnerPlugin
from plugins.memos import MemosPlugin
from utils.logger import logger


class PluginRegistry:
    """连接器注册中心。"""

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._enabled: set[str] = set()
        self._register_builtin()

    def _register_builtin(self):
        """注册所有内置插件。"""
        builtins = [
            WebSearchPlugin(),
            URLSummaryPlugin(),
            WeatherPlugin(),
            CalculatorPlugin(),
            TranslatePlugin(),
            ImageUnderstandPlugin(),
            ImageGenPlugin(),
            CodeRunnerPlugin(),
            MemosPlugin(),
        ]
        for plugin in builtins:
            self._plugins[plugin.name] = plugin

    def set_enabled(self, names: list[str]):
        """设置启用的插件列表。"""
        self._enabled = set(names)

    def enable(self, name: str) -> bool:
        """启用插件。"""
        if name in self._plugins:
            self._enabled.add(name)
            return True
        return False

    def disable(self, name: str) -> bool:
        """禁用插件。"""
        self._enabled.discard(name)
        return True

    def is_enabled(self, name: str) -> bool:
        """检查插件是否启用。"""
        return name in self._enabled

    def get(self, name: str) -> Optional[BasePlugin]:
        """获取指定插件。"""
        return self._plugins.get(name)

    def get_all(self) -> list[dict]:
        """获取所有插件信息（含启用状态）。"""
        return [
            {
                "name": p.name,
                "description": p.description,
                "auto_trigger": p.auto_trigger,
                "manual_command": p.manual_command,
                "enabled": p.name in self._enabled,
            }
            for p in self._plugins.values()
        ]

    def get_enabled_plugins(self) -> list[BasePlugin]:
        """获取所有已启用的插件实例。"""
        return [p for name, p in self._plugins.items() if name in self._enabled]

    def get_tool_definitions(self) -> list[dict]:
        """获取已启用插件的 OpenAI Function Calling 工具定义。"""
        tools = []
        for name in self._enabled:
            plugin = self._plugins.get(name)
            if plugin and plugin.auto_trigger:
                tools.append(plugin.get_tool_definition())
        return tools

    async def execute(self, name: str, params: dict, context: Optional[dict] = None) -> str:
        """执行指定插件。"""
        plugin = self._plugins.get(name)
        if not plugin:
            return f"未找到连接器: {name}"
        if name not in self._enabled:
            return f"连接器 '{name}' 未启用"
        try:
            return await plugin.execute(params, context)
        except Exception as e:
            logger.error(f"插件 {name} 执行失败: {e}")
            return f"连接器执行出错: {e}"


# 全局单例
plugin_registry = PluginRegistry()
