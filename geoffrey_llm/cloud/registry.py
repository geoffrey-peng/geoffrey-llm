"""Built-in cloud provider registry."""

from typing import Type

from ..common.registry import Registry
from .providers.base import BaseCloudProvider

_provider_registry: Registry[BaseCloudProvider] = Registry()
_initialized = False


def get_provider_registry() -> Registry[BaseCloudProvider]:
    global _initialized
    if not _initialized:
        from .providers.alibaba import AlibabaCloudProvider
        from .providers.aws import AwsCloudProvider
        from .providers.huawei import HuaweiCloudProvider
        from .providers.mock import MockCloudProvider
        from .providers.tencent import TencentCloudProvider
        _provider_registry.register("alibaba", AlibabaCloudProvider)
        _provider_registry.register("tencent", TencentCloudProvider)
        _provider_registry.register("huawei", HuaweiCloudProvider)
        _provider_registry.register("aws", AwsCloudProvider)
        _provider_registry.register("mock", MockCloudProvider)
        _initialized = True
    return _provider_registry


def register_provider(name: str, provider: Type[BaseCloudProvider]) -> None:
    get_provider_registry().register(name, provider)
