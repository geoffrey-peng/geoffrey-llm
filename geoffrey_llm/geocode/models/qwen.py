"""
Qwen (DashScope/Alibaba Cloud) provider for geocode.

Uses DashScope API for Qwen models.
"""

import os
from typing import Any, AsyncIterator, Optional

import httpx

from geoffrey_llm.geocode.models.base import BaseModel, ModelConfig, ModelResponse


class QwenProvider(BaseModel):
    """
    Alibaba Cloud DashScope (Qwen) API provider.

    API documentation: https://help.aliyun.com/document_detail/2433048.html
    - Base URL: https://dashscope.aliyuncs.com/api/v1
    - Model names: qwen-turbo, qwen-plus, qwen-max, etc.
    """

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
    DEFAULT_MODEL = "qwen-plus"

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.api_key = config.api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        self.model = config.model_name or self.DEFAULT_MODEL

        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable or api_key config is required")

    @property
    def provider_name(self) -> str:
        return "qwen"

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ModelResponse:
        """Send a chat completion request to DashScope API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        # DashScope uses "messages" key
        payload: dict[str, Any] = {
            "model": self.model,
            "input": {
                "messages": messages,
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            },
        }

        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.base_url}/services/aigc/text-generation/generation",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Parse DashScope response format
        output = data.get("output", {})
        content = output.get("text", "")
        usage = data.get("usage", {})
        finish_reason = output.get("finish_reason", "stop")

        return ModelResponse(
            content=content,
            usage=usage,
            finish_reason=finish_reason,
        )

    async def stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response tokens from DashScope API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "input": {
                "messages": messages,
            },
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "incremental_output": True,  # Enable streaming
            },
        }

        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/services/aigc/text-generation/generation",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            output = data.get("output", {})
                            if "text" in output:
                                yield output["text"]
                            if data.get("usage"):
                                # Store usage from last chunk
                                pass
                        except json.JSONDecodeError:
                            continue
