"""HTTP 请求自动审计中间件:ASGI(FastAPI/Starlette)与 WSGI(Flask)。

纯协议鸭子类型实现,不 import 任何 Web 框架,一行接入::

    # FastAPI / Starlette
    from geoffrey_llm.audit import AuditASGIMiddleware
    app = AuditASGIMiddleware(app)

    # Flask(任意 WSGI 应用)
    from geoffrey_llm.audit import AuditWSGIMiddleware
    app.wsgi_app = AuditWSGIMiddleware(app.wsgi_app)

自动记录 method/path/status_code/latency_ms/client_ip/user_agent;
健康检查等路径默认跳过;审计故障对请求处理完全透明。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Iterable, Optional, Sequence, Tuple

from .client import get_client

logger = logging.getLogger("geoffrey_llm.audit")

DEFAULT_SKIP_PATHS: Tuple[str, ...] = ("/healthz", "/readyz", "/favicon.ico")


def _emit_http(event_type: str, method: str, path: str, status: int,
               start: float, client_ip: Optional[str], user_agent: Optional[str]) -> None:
    try:
        get_client().emit(
            event_type,
            "%s %s" % (method.lower(), path.split("?", 1)[0]) if method else None,
            method=method,
            path=path,
            status_code=status,
            success=status < 400,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
            client_ip=client_ip,
            user_agent=user_agent,
            risk_level="low" if status < 400 else "medium",
        )
    except Exception:  # 审计绝不影响业务
        logger.debug("audit middleware emit failed", exc_info=True)


class AuditASGIMiddleware:
    """ASGI 中间件:自动审计每个 HTTP 请求。"""

    def __init__(
        self,
        app: Any,
        event_type: str = "http_access",
        skip_paths: Sequence[str] = DEFAULT_SKIP_PATHS,
    ) -> None:
        self.app = app
        self.event_type = event_type
        self.skip_paths = tuple(skip_paths)

    def _skip(self, path: str) -> bool:
        return any(path == p or path.startswith(p + "/") for p in self.skip_paths)

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope.get("type") != "http" or self._skip(scope.get("path", "")):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in scope.get("headers", [])}
        forwarded = headers.get("x-forwarded-for", "")
        client = scope.get("client") or ()
        client_ip = (forwarded.split(",")[0].strip() if forwarded
                     else (client[0] if client else None))
        user_agent = headers.get("user-agent")

        status_box = {"status": 500}

        async def send_wrapper(message: dict) -> None:
            if message.get("type") == "http.response.start":
                status_box["status"] = message.get("status", 500)
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            _emit_http(self.event_type, method, path, 500, start, client_ip, user_agent)
            raise
        _emit_http(self.event_type, method, path, status_box["status"],
                   start, client_ip, user_agent)


class AuditWSGIMiddleware:
    """WSGI 中间件:自动审计每个 HTTP 请求(Flask 用法见模块 docstring)。"""

    def __init__(
        self,
        app: Any,
        event_type: str = "http_access",
        skip_paths: Sequence[str] = DEFAULT_SKIP_PATHS,
    ) -> None:
        self.app = app
        self.event_type = event_type
        self.skip_paths = tuple(skip_paths)

    def _skip(self, path: str) -> bool:
        return any(path == p or path.startswith(p + "/") for p in self.skip_paths)

    def __call__(self, environ: dict, start_response: Callable) -> Iterable[bytes]:
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "")
        if self._skip(path):
            return self.app(environ, start_response)

        forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
        client_ip = (forwarded.split(",")[0].strip() if forwarded
                     else environ.get("REMOTE_ADDR") or None)
        user_agent = environ.get("HTTP_USER_AGENT") or None

        status_box = {"status": 500}

        def auditing_start_response(status: str, headers: list, exc_info: Any = None):
            try:
                status_box["status"] = int(status.split(" ", 1)[0])
            except (ValueError, AttributeError, IndexError):
                pass
            return start_response(status, headers, exc_info)

        start = time.perf_counter()
        try:
            result = self.app(environ, auditing_start_response)
        except Exception:
            _emit_http(self.event_type, method, path, 500, start, client_ip, user_agent)
            raise
        _emit_http(self.event_type, method, path, status_box["status"],
                   start, client_ip, user_agent)
        return result
