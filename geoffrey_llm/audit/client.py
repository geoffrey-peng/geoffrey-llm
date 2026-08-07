"""审计客户端:队列 + 后台线程批量投递,fire-and-forget 绝不阻塞业务。

设计原则:
- 配置不全时进入 no-op 模式(至多告警一次),应用可无条件内置审计调用
- emit 永不抛异常;发送失败只丢弃 + 限频告警,不做磁盘持久化
- 投递走后台 daemon 线程,业务线程只负责入队(非阻塞 put)
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import threading
import time
import urllib.request
import uuid
from typing import Any, Dict, Optional

from .errors import AuditConfigError

logger = logging.getLogger("geoffrey_llm.audit")

# 测试打桩点:替换此函数即可拦截 HTTP 发送
_urlopen = urllib.request.urlopen

# 已知顶层字段;其余 kwargs 会并入 metadata
_KNOWN_FIELDS = (
    "action",
    "actor_type",
    "actor_id",
    "actor_name",
    "resource_type",
    "resource_id",
    "resource_name",
    "method",
    "path",
    "status_code",
    "success",
    "latency_ms",
    "client_ip",
    "user_agent",
    "risk_level",
)

# 客户端脱敏规则,与服务端保持一致:键名命中子串或后缀 → '***'
_SENSITIVE_SUBSTRINGS = (
    "password",
    "token",
    "secret",
    "authorization",
    "cookie",
    "api_key",
    "credential",
    "session",
)
_SENSITIVE_SUFFIXES = ("_token", "_secret", "_key", "_password", "_credential")

_WARN_INTERVAL = 60.0  # 同类告警最少间隔秒数
_TRUE = ("1", "true", "yes")
_FALSE = ("0", "false", "no")


def _is_sensitive_key(key: Any) -> bool:
    k = str(key).lower()
    return any(s in k for s in _SENSITIVE_SUBSTRINGS) or any(
        k.endswith(s) for s in _SENSITIVE_SUFFIXES
    )


def mask_sensitive(value: Any) -> Any:
    """递归脱敏:敏感键的值替换为 '***'。"""
    if isinstance(value, dict):
        return {
            k: ("***" if _is_sensitive_key(k) else mask_sensitive(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(v) for v in value]
    return value


def _env_flag(name: str) -> Optional[bool]:
    raw = os.environ.get(name, "").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    return None


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


class AuditClient:
    """统一审计服务客户端。

    参数缺省时从环境变量读取:``AUDIT_ENDPOINT``、``AUDIT_APP``、
    ``AUDIT_KEY``、``AUDIT_ENABLED``、``AUDIT_TIMEOUT_SECONDS``(默认 2.0)、
    ``AUDIT_BATCH_SIZE``(默认 20)、``AUDIT_FLUSH_INTERVAL``(默认 1.0 秒)、
    ``AUDIT_QUEUE_SIZE``(默认 1000)。

    endpoint/app/key 不全时为 no-op 模式:所有调用静默成功,至多告警一次。
    ``strict=True`` 时配置不全直接抛 :class:`AuditConfigError`。
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        app: Optional[str] = None,
        key: Optional[str] = None,
        enabled: Optional[bool] = None,
        timeout: Optional[float] = None,
        batch_size: Optional[int] = None,
        flush_interval: Optional[float] = None,
        queue_size: Optional[int] = None,
        strict: bool = False,
    ) -> None:
        self._endpoint = (endpoint or os.environ.get("AUDIT_ENDPOINT", "")).strip()
        self._app = (app or os.environ.get("AUDIT_APP", "")).strip()
        self._key = (key or os.environ.get("AUDIT_KEY", "")).strip()
        self._timeout = timeout if timeout is not None else _env_float("AUDIT_TIMEOUT_SECONDS", 2.0)
        self._batch_size = max(1, batch_size if batch_size is not None else _env_int("AUDIT_BATCH_SIZE", 20))
        self._flush_interval = max(0.05, flush_interval if flush_interval is not None else _env_float("AUDIT_FLUSH_INTERVAL", 1.0))

        if enabled is None:
            enabled = _env_flag("AUDIT_ENABLED")
        complete = bool(self._endpoint and self._app and self._key)
        if enabled is None:
            enabled = complete

        if not complete:
            if strict:
                raise AuditConfigError(
                    "审计客户端配置不全:endpoint/app/key 必须同时提供"
                    "(或设置 AUDIT_ENDPOINT/AUDIT_APP/AUDIT_KEY 环境变量)"
                )
            enabled = False

        self.enabled = bool(enabled)
        self._queue: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue(
            maxsize=max(1, queue_size if queue_size is not None else _env_int("AUDIT_QUEUE_SIZE", 1000))
        )
        self._stats_lock = threading.Lock()
        self._sent = 0
        self._dropped = 0
        self._failed = 0
        self._pending = 0  # 已出队、尚未发送完成的事件数(flush 用)
        self._warned_at: Dict[str, float] = {}
        self._noop_warned = False
        self._closed = False
        self._worker_thread: Optional[threading.Thread] = None

        if self.enabled:
            self._worker_thread = threading.Thread(
                target=self._worker, name="geoffrey-audit-sender", daemon=True
            )
            self._worker_thread.start()
            atexit.register(self._atexit_flush)
        else:
            self._warn_noop_once()

    # ------------------------------------------------------------------ emit

    def emit(
        self,
        event_type: str,
        action: Optional[str] = None,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[str] = None,
        event_id: Optional[str] = None,
        **fields: Any,
    ) -> bool:
        """投递一条审计事件(非阻塞)。永不抛异常;返回是否成功入队。

        ``fields`` 中的已知字段(action/actor_*/resource_*/method/path/…)
        直接进入事件顶层;未知键并入 ``metadata``。
        """
        try:
            if not self.enabled or self._closed:
                self._warn_noop_once()
                return False

            payload: Dict[str, Any] = {
                "event_id": event_id or str(uuid.uuid4()),
                "app": self._app,
                "event_type": event_type,
                "occurred_at": occurred_at
                or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            if action is not None:
                payload["action"] = action

            extra: Dict[str, Any] = {}
            for name, value in fields.items():
                if value is None:
                    continue
                if name in _KNOWN_FIELDS:
                    payload[name] = value
                else:
                    extra[name] = value

            merged_meta = dict(metadata or {})
            merged_meta.update(extra)
            if merged_meta:
                payload["metadata"] = mask_sensitive(merged_meta)

            try:
                self._queue.put_nowait(payload)
                return True
            except queue.Full:
                with self._stats_lock:
                    self._dropped += 1
                self._warn_rate_limited(
                    "queue_full",
                    "AUDIT_QUEUE_FULL 审计队列已满,事件被丢弃(app=%s)" % self._app,
                )
                return False
        except Exception:  # 审计绝不影响业务
            logger.debug("audit emit failed", exc_info=True)
            return False

    # ----------------------------------------------------------------- flush

    def _drained(self) -> bool:
        return self._queue.qsize() == 0 and self._pending == 0

    def flush(self, timeout: float = 5.0) -> bool:
        """尽力等待队列排空且批次全部发送完成。超时返回 False。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._drained():
                time.sleep(0.01)  # 二次确认,覆盖出队与计数之间的窗口
                if self._drained():
                    return True
            time.sleep(0.01)
        return self._drained()

    def close(self) -> None:
        """排空队列并停止 worker。close 后 emit 变为 no-op。"""
        if not self.enabled:
            self._closed = True
            return
        self.flush(timeout=self._timeout + 1.0)
        self._closed = True

    def _atexit_flush(self) -> None:
        if not self._closed:
            self.close()

    # ----------------------------------------------------------------- stats

    def stats(self) -> Dict[str, int]:
        with self._stats_lock:
            return {
                "queued": self._queue.qsize(),
                "sent": self._sent,
                "dropped": self._dropped,
                "failed": self._failed,
            }

    # ---------------------------------------------------------------- worker

    def _worker(self) -> None:
        while True:
            try:
                if self._closed and self._queue.empty():
                    return
                try:
                    first = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                batch = [first]
                with self._stats_lock:
                    self._pending += 1  # 出队即计数,flush 不留窗口
                deadline = time.monotonic() + self._flush_interval
                while len(batch) < self._batch_size:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        item = self._queue.get(timeout=remaining)
                    except queue.Empty:
                        break
                    batch.append(item)
                    with self._stats_lock:
                        self._pending += 1
                try:
                    self._send_batch(batch)
                finally:
                    with self._stats_lock:
                        self._pending -= len(batch)
            except Exception:  # worker 永不退出
                logger.debug("audit worker error", exc_info=True)
                time.sleep(0.1)

    def _send_batch(self, batch: "list[Dict[str, Any]]") -> None:
        url = self._endpoint.rstrip("/") + "/batch"
        body = json.dumps({"events": batch}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Audit-App": self._app,
                "X-Audit-Key": self._key,
            },
        )
        try:
            with _urlopen(req, timeout=self._timeout) as resp:
                resp.read()
            with self._stats_lock:
                self._sent += len(batch)
        except Exception as exc:
            with self._stats_lock:
                self._failed += len(batch)
            self._warn_rate_limited(
                "send_fail",
                "AUDIT_SEND_FAIL endpoint=%s err=%s" % (url, type(exc).__name__),
            )

    # --------------------------------------------------------------- warnings

    def _warn_noop_once(self) -> None:
        if not self._noop_warned:
            self._noop_warned = True
            logger.warning(
                "审计客户端未配置或已禁用(AUDIT_ENDPOINT/AUDIT_APP/AUDIT_KEY),"
                "审计调用将不生效"
            )

    def _warn_rate_limited(self, key: str, message: str) -> None:
        now = time.monotonic()
        with self._stats_lock:
            last = self._warned_at.get(key, 0.0)
            if now - last < _WARN_INTERVAL:
                return
            self._warned_at[key] = now
        logger.warning(message)


# ------------------------------------------------------------------ singleton

_default_client: Optional[AuditClient] = None
_default_lock = threading.Lock()


def get_client() -> AuditClient:
    """获取默认单例(首次调用时从环境变量惰性构建)。"""
    global _default_client
    with _default_lock:
        if _default_client is None:
            _default_client = AuditClient()
        return _default_client


def configure(**kwargs: Any) -> AuditClient:
    """用显式参数重建默认单例(旧客户端会被 flush + 关闭)。"""
    global _default_client
    with _default_lock:
        if _default_client is not None:
            _default_client.close()
        _default_client = AuditClient(**kwargs)
        return _default_client
