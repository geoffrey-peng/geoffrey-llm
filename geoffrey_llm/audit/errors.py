"""审计 SDK 异常。"""

from geoffrey_llm.common.errors import GeoffreyError


class AuditConfigError(GeoffreyError):
    """审计客户端配置错误。

    仅在显式 ``strict=True`` 构造且配置不全时抛出;
    默认情况下 SDK 对缺失配置采取告警 + no-op,绝不影响业务。
    """
