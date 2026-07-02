"""天气查询连接器 — 使用 wttr.in 免费 API。"""

from typing import Optional
import httpx

from plugins.base import BasePlugin


class WeatherPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "查询指定城市的天气信息"

    @property
    def auto_trigger(self) -> bool:
        return True

    @property
    def manual_command(self) -> str:
        return "weather"

    async def execute(self, params: dict, context: Optional[dict] = None) -> str:
        city = params.get("query", "") or params.get("city", "")
        if not city:
            return "请提供城市名称，例如: /weather 北京"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://wttr.in/{city}?format=%C+%t+%h+%w&lang=zh"
                )
                response.raise_for_status()
                weather_text = response.text.strip()

            if not weather_text or "Unknown" in weather_text:
                return f"未找到城市 '{city}' 的天气信息"

            return f"{city} 当前天气: {weather_text}"

        except Exception as e:
            return f"天气查询失败: {e}"
