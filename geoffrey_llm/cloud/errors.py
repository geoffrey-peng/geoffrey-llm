"""Cloud SDK errors."""

from ..common.errors import BackendError, ConfigError


class CloudError(BackendError):
    """云服务调用或适配错误。"""


class CloudConfigError(ConfigError):
    """云客户端配置或凭据配置错误。"""


class CloudSafetyError(CloudError):
    """云资源变更未通过安全策略。"""


class CloudDependencyError(CloudError):
    """所选云厂商的可选 SDK 尚未安装。"""
