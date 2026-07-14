"""Azure OpenAI (and mock) LLM clients with token usage capture."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from sales_ivr.models.session import LLMUsage
from sales_ivr.runtime import get_config


@dataclass
class ChatMessage:
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def to_openai(self) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": self.role}
        if self.content is not None:
            msg["content"] = self.content
        if self.tool_calls is not None:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            msg["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            msg["name"] = self.name
        return msg


@dataclass
class LLMResult:
    content: str | None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: LLMUsage | None = None
    finish_reason: str | None = None


class BaseLLMClient:
    def chat(
        self,
        *,
        agent_name: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> LLMResult:
        raise NotImplementedError


class AzureOpenAIClient(BaseLLMClient):
    def __init__(self) -> None:
        from openai import AzureOpenAI

        config = get_config().llm
        api_key = os.environ.get(config.api_key_env)
        endpoint = os.environ.get(config.endpoint_env)
        if not api_key or not endpoint:
            raise RuntimeError(
                f"Set {config.api_key_env} and {config.endpoint_env} for Azure OpenAI. "
                "See README for setup steps."
            )
        self._deployment = config.deployment
        self._deployment_capable = config.deployment_capable or config.deployment
        self._temperature = config.temperature
        self._max_tokens = config.max_tokens
        self._client = AzureOpenAI(
            api_key=api_key,
            api_version=config.api_version,
            azure_endpoint=endpoint.rstrip("/"),
        )

    def chat(
        self,
        *,
        agent_name: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> LLMResult:
        deployment = model or self._deployment
        kwargs: dict[str, Any] = {
            "model": deployment,
            "messages": [m.to_openai() for m in messages],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if response_format:
            kwargs["response_format"] = response_format

        started = time.perf_counter()
        response = self._client.chat.completions.create(**kwargs)
        latency_ms = int((time.perf_counter() - started) * 1000)

        choice = response.choices[0]
        message = choice.message
        tool_calls: list[dict[str, Any]] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

        usage = None
        if response.usage:
            usage = LLMUsage(
                agent_name=agent_name,
                model=deployment,
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
                total_tokens=response.usage.total_tokens or 0,
                latency_ms=latency_ms,
                tool_calls=len(tool_calls),
                finish_reason=choice.finish_reason,
            )
        else:
            usage = LLMUsage(
                agent_name=agent_name,
                model=deployment,
                latency_ms=latency_ms,
                tool_calls=len(tool_calls),
                finish_reason=choice.finish_reason,
            )

        return LLMResult(
            content=message.content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.finish_reason,
        )


class MockLLMClient(BaseLLMClient):
    """Deterministic offline client for unit tests (no network)."""

    def __init__(self, responder: Callable[..., LLMResult] | None = None) -> None:
        self._responder = responder

    def chat(
        self,
        *,
        agent_name: str,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> LLMResult:
        if self._responder:
            return self._responder(
                agent_name=agent_name,
                messages=messages,
                tools=tools,
                response_format=response_format,
                model=model,
            )
        # Default: empty final JSON object — tests should inject responders
        usage = LLMUsage(
            agent_name=agent_name,
            model=model or "mock",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=1,
        )
        return LLMResult(content="{}", usage=usage, finish_reason="stop")


_client: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    global _client
    if _client is not None:
        return _client
    provider = get_config().llm.provider.lower()
    if provider == "mock":
        from sales_ivr.llm.mock_responders import default_mock_responder

        _client = MockLLMClient(responder=default_mock_responder)
    elif provider == "azure":
        _client = AzureOpenAIClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    return _client


def set_llm_client(client: BaseLLMClient | None) -> None:
    global _client
    _client = client


def reset_llm_client() -> None:
    set_llm_client(None)


def parse_json_content(content: str | None) -> dict[str, Any]:
    if not content:
        return {}
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
