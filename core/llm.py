"""LLM 抽象层 — 主模型 + 备用模型，返回 (文本, prompt_tokens, completion_tokens)。"""

import json
import httpx
from abc import ABC, abstractmethod

from openai import AsyncOpenAI
from utils.logger import logger
from storage.database import get_enabled_models


class ChatResult:
    """LLM 调用结果。"""
    def __init__(self, text: str, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.text = text
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BaseLLMBackend(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], model: str = "", **kwargs) -> ChatResult:
        ...


class OpenAICompatibleBackend(BaseLLMBackend):
    def __init__(self, api_key: str, base_url: str, default_model: str, name: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model
        self._name = name

    async def chat(self, messages: list[dict], model: str = "", **kwargs) -> ChatResult:
        model = model or self.default_model
        params = {
            "model": model, "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2000),
        }
        tools = kwargs.get("tools")
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]
        text = choice.message.content or ""
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = []
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append({"id": tc.id, "name": tc.function.name, "args": args})
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        result = ChatResult(text, prompt_tokens, completion_tokens)
        result.tool_calls = tool_calls
        result.message = choice.message  # needed for tool call response
        return result


class AnthropicBackend(BaseLLMBackend):
    def __init__(self, api_key: str, default_model: str, name: str):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.default_model = default_model
        self._name = name

    def _convert_content(self, content):
        """将 OpenAI 格式的 content 转为 Anthropic 格式（主要处理 image_url → image）。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            converted = []
            for part in content:
                if isinstance(part, str):
                    converted.append({"type": "text", "text": part})
                elif isinstance(part, dict):
                    if part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            # data:image/jpeg;base64,xxxx
                            header, b64 = url.split(",", 1)
                            media_type = header.split(":")[1].split(";")[0] if ":" in header else "image/jpeg"
                            converted.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": media_type, "data": b64}
                            })
                        else:
                            # URL 图片：仍用 image_url 但 Anthropic 不支持，转文本提示
                            converted.append({"type": "text", "text": f"[图片链接: {url}]"})
                    else:
                        converted.append(part)
                else:
                    converted.append({"type": "text", "text": str(part)})
            return converted
        return content

    async def chat(self, messages: list[dict], model: str = "", **kwargs) -> ChatResult:
        import anthropic
        model = model or self.default_model
        system_msg = ""
        user_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                # 转换多模态内容（OpenAI → Anthropic）
                content = self._convert_content(msg.get("content", ""))
                user_msgs.append({"role": msg["role"], "content": content})
        resp = await self.client.messages.create(
            model=model, max_tokens=kwargs.get("max_tokens", 2000),
            system=system_msg if system_msg else anthropic.NOT_GIVEN,
            messages=user_msgs,
        )
        text = resp.content[0].text
        usage = resp.usage
        prompt_tokens = usage.input_tokens if usage else 0
        completion_tokens = usage.output_tokens if usage else 0
        return ChatResult(text, prompt_tokens, completion_tokens)


class OllamaBackend(BaseLLMBackend):
    def __init__(self, host: str, default_model: str, name: str):
        self.host = host.rstrip("/")
        self.default_model = default_model
        self._name = name

    async def chat(self, messages: list[dict], model: str = "", **kwargs) -> ChatResult:
        model = model or self.default_model
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.host}/api/chat", json={
                "model": model, "messages": messages, "stream": False,
            })
            resp.raise_for_status()
            data = resp.json()
            text = data.get("message", {}).get("content", "")
            prompt_tokens = data.get("prompt_eval_count", 0) or 0
            completion_tokens = data.get("eval_count", 0) or 0
            return ChatResult(text, prompt_tokens, completion_tokens)


def _create_backend(config: dict):
    provider = config["provider"]
    api_key = config["api_key"]
    base_url = config.get("base_url", "")
    model = config["model_name"]
    name = config["name"]
    if provider == "anthropic":
        return AnthropicBackend(api_key, model, name)
    elif provider == "ollama":
        return OllamaBackend(base_url or "http://localhost:11434", model, name)
    else:
        return OpenAICompatibleBackend(api_key, base_url, model, name)


class LLMManager:
    def __init__(self):
        self.backends: list[BaseLLMBackend] = []
        self._configs: list[dict] = []

    async def init(self):
        self.backends.clear()
        configs = await get_enabled_models()
        configs.sort(key=lambda c: c["sort_order"] or 999)
        # 把主模型排到最前面
        from storage.database import get_setting
        primary_id_str = await get_setting("primary_model_id", "")
        primary_model_id = int(primary_id_str) if primary_id_str and primary_id_str.isdigit() else None
        if primary_model_id:
            idx = next((i for i, c in enumerate(configs) if c["id"] == primary_model_id), None)
            if idx and idx > 0:
                configs.insert(0, configs.pop(idx))
        self._configs = configs
        for c in self._configs:
            backend = _create_backend(c)
            if backend:
                self.backends.append(backend)
        if self.backends:
            logger.info(f"LLM: 主={self.backends[0]._name}, 备用={[b._name for b in self.backends[1:]]}")
        else:
            logger.warning("无可用模型，请在管理面板配置")

    async def reload(self):
        await self.init()

    @property
    def primary(self) -> str | None:
        return self._configs[0]["name"] if self._configs else None

    def get_all(self) -> list[dict]:
        return [
            {"id": c["id"], "name": c["name"], "provider": c["provider"],
             "model": c["model_name"], "enabled": bool(c["is_enabled"]),
             "has_key": bool(c["api_key"])}
            for c in self._configs
        ]

    def _get_backends_for_ids(self, allowed_ids: list[int] | None) -> list[tuple]:
        """根据允许的模型 ID 列表，返回对应的 (backend, config) 列表。
        如果 allowed_ids 为空/None，返回全部。"""
        if not allowed_ids:
            return list(zip(self.backends, self._configs))
        id_set = set(allowed_ids)
        return [(b, c) for b, c in zip(self.backends, self._configs) if c["id"] in id_set]

    async def chat(self, messages: list[dict], allowed_model_ids: list[int] = None, **kwargs) -> ChatResult:
        if not self.backends:
            raise RuntimeError("没有可用的 LLM 后端")
        backends = self._get_backends_for_ids(allowed_model_ids)
        if not backends:
            raise RuntimeError("Bot 未分配可用模型")
        errors = []
        for i, (backend, config) in enumerate(backends):
            try:
                result = await backend.chat(messages, **kwargs)
                logger.info(f"LLM 调用: {config['name']}({config['model_name']}) | prompt={result.prompt_tokens} completion={result.completion_tokens} total={result.total_tokens}")
                if i > 0:
                    logger.info(f"主模型不可用，fallback 到 {backend._name}")
                return result
            except Exception as e:
                errors.append(f"{backend._name}: {e}")
                logger.warning(f"LLM {backend._name} 失败: {e}")
                if i < len(backends) - 1:
                    logger.info(f"尝试备用: {backends[i+1][0]._name}...")
        raise RuntimeError(f"所有模型均失败: {'; '.join(errors)}")

    async def chat_with_tools(self, messages: list[dict], tools: list[dict],
                               tool_handler, max_rounds: int = 3,
                               allowed_model_ids: list[int] = None, **kwargs) -> ChatResult:
        """带工具调用的对话：LLM 可自动决定调用工具，最多 max_rounds 轮。"""
        if not self.backends:
            return await self.chat(messages, allowed_model_ids=allowed_model_ids, **kwargs)

        for _ in range(max_rounds):
            result = await self.chat(messages, tools=tools, allowed_model_ids=allowed_model_ids, **kwargs)
            if not result.tool_calls:
                return result

            # 添加 assistant 消息（含 tool_calls）
            messages.append(result.message)

            # 执行每个工具调用
            for tc in result.tool_calls:
                tool_name = tc["name"]
                try:
                    tool_result = await tool_handler(tool_name, tc["args"])
                    logger.info(f"工具调用: {tool_name} → {str(tool_result)[:100]}")
                except Exception as e:
                    tool_result = f"错误: {e}"
                    logger.error(f"工具 {tool_name} 失败: {e}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(tool_result),
                })

        # 最后一轮不传 tools
        result = await self.chat(messages, allowed_model_ids=allowed_model_ids, **kwargs)
        return result


llm_manager = LLMManager()
