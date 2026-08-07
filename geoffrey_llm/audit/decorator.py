"""@audit_event 装饰器:一行接入业务动作审计。

用法::

    from geoffrey_llm.audit import audit_event

    @audit_event(action="user.login", event_type="auth", actor_from="username")
    def login(username, password):
        ...

自动记录耗时、成功/失败;异常时记录错误信息(risk_level=high)并**原样抛出**,
绝不吞业务异常。审计自身故障对被装饰函数完全透明。
同步与 async 函数均支持。
"""

from __future__ import annotations

import functools
import inspect
import logging
import time
from typing import Any, Callable, Optional, TypeVar

from .client import get_client

logger = logging.getLogger("geoffrey_llm.audit")

F = TypeVar("F", bound=Callable[..., Any])

_PRIMITIVES = (str, int, float, bool)


def audit_event(
    action: Optional[str] = None,
    event_type: str = "action",
    actor_from: Optional[str] = None,
    actor_id_from: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id_from: Optional[str] = None,
    resource_name_from: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> Callable[[F], F]:
    """装饰一个函数,每次调用自动投递审计事件。

    :param action: 动作名,默认取 ``func.__qualname__``
    :param event_type: 事件类型,默认 ``"action"``
    :param actor_from: 函数参数名,其值提升为 ``actor_name``
    :param actor_id_from: 函数参数名,其值提升为 ``actor_id``
    :param resource_type: 资源类型常量
    :param resource_id_from: 函数参数名,其值提升为 ``resource_id``
    :param resource_name_from: 函数参数名,其值提升为 ``resource_name``
    :param risk_level: 成功时的风险级别(失败时固定为 high)
    """

    def decorator(func: F) -> F:
        act = action or func.__qualname__
        lifting = (
            ("actor_name", actor_from),
            ("actor_id", actor_id_from),
            ("resource_id", resource_id_from),
            ("resource_name", resource_name_from),
        )

        def build_fields(args: tuple, kwargs: dict) -> dict:
            fields: dict = {}
            try:
                bound = inspect.signature(func).bind(*args, **kwargs)
                bound.apply_defaults()
                arguments = bound.arguments
            except TypeError:
                arguments = {}
            for field_name, param_name in lifting:
                if param_name and param_name in arguments:
                    value = arguments[param_name]
                    if value is not None:
                        fields[field_name] = (
                            value if isinstance(value, _PRIMITIVES) else str(value)
                        )
            if resource_type:
                fields["resource_type"] = resource_type
            return fields

        def do_emit(start: float, fields: dict, exc: Optional[BaseException] = None) -> None:
            try:
                emit_fields = dict(fields)
                emit_fields["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
                meta = None
                if exc is None:
                    emit_fields["success"] = True
                    if risk_level:
                        emit_fields["risk_level"] = risk_level
                else:
                    emit_fields["success"] = False
                    emit_fields["risk_level"] = "high"
                    meta = {
                        "error": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    }
                get_client().emit(event_type, act, metadata=meta, **emit_fields)
            except Exception:  # 审计绝不影响业务
                logger.debug("audit_event emit failed", exc_info=True)

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                fields = build_fields(args, kwargs)
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    do_emit(start, fields, exc)
                    raise
                do_emit(start, fields)
                return result

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            fields = build_fields(args, kwargs)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                do_emit(start, fields, exc)
                raise
            do_emit(start, fields)
            return result

        return sync_wrapper  # type: ignore[return-value]

    return decorator
