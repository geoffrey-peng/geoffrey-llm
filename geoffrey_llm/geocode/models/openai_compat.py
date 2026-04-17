"""
OpenAI-compatible API provider for geocode.

Supports any API that implements the OpenAI chat completions format.
This includes local models via Ollama, LM Studio, etc.
"""

import os
from typing import Any, AsyncIterator, Optional

import httpx

from geoffrey_llm.geocode.models.base import BaseModel, ModelConfig, ModelResponse


class OpenAICompatProvider(BaseModel):
    """
    OpenAI-compatible API provider.

    Useful for:
    - Local models via Ollama, LM Studio, LocalAI
    - Other OpenAI-compatible APIs (Groq, Together, etc.)
    - Custom proxy servers

    Usage:
        config = ModelConfig(
            model_name="llama3",
            api_key="ollama",  # Often not needed for local
            base_url="http://localhost:11434/v1",  # Ollama default
        )
        provider = OpenAICompatProvider(config)
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-3.5-turbo"

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.api_key = config.api_key or os.environ.get("OPENAI_API_KEY", "not-needed")
        self.model = config.model_name or self.DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ModelResponse:
        """Send a chat completion request to OpenAI-compatible API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }

        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"].get("content", "")
        usage = data.get("usage", {})
        finish_reason = data["choices"][0].get("finish_reason", "stop")

        tool_calls = None
        message = data["choices"][0]["message"]
        if "tool_calls" in message:
            tool_calls = message["tool_calls"]

        return ModelResponse(
            content=content,
            usage=usage,
            finish_reason=finish_reason,
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens from OpenAI-compatible API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        import json
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue
