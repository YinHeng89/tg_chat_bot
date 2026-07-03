"""核心运行时配置 — 从 SQLite 加载，通过 Web 面板热更新。"""

from storage.database import (
    get_setting, get_setting_bool, get_setting_int, get_setting_list,
    get_all_settings, set_setting,
)


class CoreConfig:
    """单例运行时配置，提供便捷的属性访问。"""

    def __init__(self):
        self._cache: dict = {}

    async def refresh(self):
        self._cache = await get_all_settings()

    async def get(self, key: str, default=None):
        if key in self._cache:
            return self._cache.get(key, default)
        # Fallback to DB
        val = await get_setting(key, str(default) if default else "")
        if val:
            self._cache[key] = val
        return val if val else default

    async def set(self, key: str, value) -> bool:
        result = await set_setting(key, value)
        if result:
            self._cache[key] = str(value)
        return result

    async def get_bool(self, key: str, default=False) -> bool:
        return await get_setting_bool(key, default)

    async def get_int(self, key: str, default=0) -> int:
        return await get_setting_int(key, default)

    async def get_list(self, key: str, default=None) -> list:
        return await get_setting_list(key, default)

    # ===== 便捷属性 =====

    @property
    async def system_prompt(self) -> str:
        return await self.get("bot_system_prompt", "你是一个有帮助的 AI 助手。")

    @property
    async def bot_name(self) -> str:
        return await self.get("bot_name", "AI 助手")

    @property
    async def group_reply_mode(self) -> str:
        return await self.get("group_reply_mode", "mentioned")

    @property
    async def group_auto_reply(self) -> bool:
        return await self.get_bool("group_auto_reply", True)

    @property
    async def enabled_plugins(self) -> list:
        return await self.get_list("enabled_plugins", [])

    @property
    async def admin_ids(self) -> list:
        ids = await self.get_list("admin_ids", [])
        return [int(i) for i in ids if i]

    async def get_all_dict(self) -> dict:
        """导出所有设置（供 Web API 使用）。"""
        await self.refresh()
        return dict(self._cache)


core_config = CoreConfig()
