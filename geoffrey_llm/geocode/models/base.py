"""
Base model interface for geocode.

All model providers (kimi, deepseek, qwen, etc.) implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class ModelResponse:
    """Response from a model chat completion."""

    content: str
    usage: dict = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    })
    finish_reason: str = "stop"
    tool_calls: Optional[list[dict]] = None  # For tool call responses


@dataclass
class ModelConfig:
    """Provider-agnostic model configuration."""

    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class BaseModel(ABC):
    """
    Abstract base class for all model providers.

    Each provider (kimi, deepseek, qwen, openai-compat) implements:
    - chat(): Send a chat completion request
    - stream(): Stream response tokens
    """

    def __init__(self, config: ModelConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            tools: Optional list of tool definitions
            **kwargs: Additional provider-specific arguments

        Returns:
            ModelResponse with content and usage info
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response tokens.

        Args:
            messages: List of message dicts
            tools: Optional list of tool definitions
            **kwargs: Additional provider-specific arguments

        Yields:
            String tokens as they arrive
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'kimi', 'deepseek')."""
        pass


class ModelRegistry:
    """
    Registry for model providers.

    Usage:
        registry = ModelRegistry()
        registry.register("kimi", KimiProvider)
        registry.register("deepseek", DeepSeekProvider)

        provider = registry.create("kimi", ModelConfig(...))
    """

    def __init__(self):
        self._providers: dict[str, type[BaseModel]] = {}

    def register(self, name: str, provider_class: type[BaseModel]) -> None:
        """Register a provider class."""
        self._providers[name] = provider_class

    def create(self, name: str, config: ModelConfig) -> BaseModel:
        """Create a provider instance by name."""
        if name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(f"Unknown provider: {name}. Available: {available}")
        return self._providers[name](config)

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())


# Global registry instance
_default_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get the global model registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ModelRegistry()
        # Register built-in providers lazily
        from geoffrey_llm.geocode.models.kimi import KimiProvider
        from geoffrey_llm.geocode.models.deepseek import DeepSeekProvider
        from geoffrey_llm.geocode.models.qwen import QwenProvider
        from geoffrey_llm.geocode.models.openai_compat import OpenAICompatProvider

        _default_registry.register("kimi", KimiProvider)
        _default_registry.register("deepseek", DeepSeekProvider)
        _default_registry.register("qwen", QwenProvider)
        _default_registry.register("openai", OpenAICompatProvider)
    return _default_registry
