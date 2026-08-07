"""统一审计服务 SDK:fire-and-forget 接入 audit.geoffrey-peng.cc。

零额外依赖(纯标准库),装基础包即可用:
    pip install geoffrey-llm

三种接入方式,对业务代码侵入最小:

1. 装饰器——业务动作审计::

    from geoffrey_llm.audit import audit_event

    @audit_event(action="post.delete", actor_from="username")
    def delete_post(username, post_id): ...

2. 中间件——Web 请求自动审计(FastAPI/Flask 各一行)::

    from geoffrey_llm.audit import AuditASGIMiddleware, AuditWSGIMiddleware
    app = AuditASGIMiddleware(app)                    # ASGI
    app.wsgi_app = AuditWSGIMiddleware(app.wsgi_app)  # Flask

3. 手动发送::

    from geoffrey_llm.audit import audit
    audit("share.create", "share.create", resource_id=str(share_id))

配置走环境变量:``AUDIT_ENDPOINT`` / ``AUDIT_APP`` / ``AUDIT_KEY``
(密钥在审计 UI 的「应用」页创建)。未配置时所有调用静默 no-op,
发送失败只告警不阻塞——审计故障绝不影响业务。
"""

from typing import Any, Optional

from .client import AuditClient, configure, get_client
from .decorator import audit_event
from .errors import AuditConfigError
from .middleware import AuditASGIMiddleware, AuditWSGIMiddleware

__all__ = [
    "AuditClient",
    "AuditConfigError",
    "AuditASGIMiddleware",
    "AuditWSGIMiddleware",
    "audit",
    "audit_event",
    "configure",
    "get_client",
]


def audit(
    event_type: str,
    action: Optional[str] = None,
    *,
    metadata: Optional[dict] = None,
    **fields: Any,
) -> bool:
    """向默认客户端投递一条审计事件(等价于 ``get_client().emit(...)``)。"""
    return get_client().emit(event_type, action, metadata=metadata, **fields)
