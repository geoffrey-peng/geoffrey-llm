"""geoffrey_llm.audit 单元测试:桩掉 _urlopen,全程离线。"""

import asyncio
import json
import logging
import re
import threading
import uuid

import pytest

from geoffrey_llm.audit import (
    AuditASGIMiddleware,
    AuditClient,
    AuditConfigError,
    AuditWSGIMiddleware,
    audit_event,
    configure,
)
from geoffrey_llm.audit import client as client_mod

AUDIT_ENV_VARS = (
    "AUDIT_ENDPOINT",
    "AUDIT_APP",
    "AUDIT_KEY",
    "AUDIT_ENABLED",
    "AUDIT_TIMEOUT_SECONDS",
    "AUDIT_BATCH_SIZE",
    "AUDIT_FLUSH_INTERVAL",
    "AUDIT_QUEUE_SIZE",
)

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class FakeResponse:
    def read(self):
        return b'{"ok": true}'

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def clean_env(monkeypatch):
    for name in AUDIT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture
def captured(monkeypatch, clean_env):
    """桩掉 _urlopen,返回捕获到的请求列表(每项含 url/headers/events)。"""
    requests = []

    def fake_urlopen(req, timeout=None):
        requests.append(
            {
                "url": req.full_url,
                "headers": {k.lower(): v for k, v in req.headers.items()},
                "events": json.loads(req.data)["events"],
            }
        )
        return FakeResponse()

    monkeypatch.setattr(client_mod, "_urlopen", fake_urlopen)
    return requests


@pytest.fixture
def reset_singleton(clean_env):
    """测试后把默认单例重置为 no-op,避免串扰。"""
    yield
    configure()  # 无参 → 从(已清空的)env 构建 no-op 客户端


def make_client(**kwargs):
    kwargs.setdefault("endpoint", "https://audit.test/api/v1/events")
    kwargs.setdefault("app", "testapp")
    kwargs.setdefault("key", "test-key-123456")
    kwargs.setdefault("flush_interval", 0.05)
    return AuditClient(**kwargs)


def all_events(captured):
    return [e for req in captured for e in req["events"]]


# ------------------------------------------------------------------- client


def test_unconfigured_is_noop(clean_env, caplog):
    with caplog.at_level(logging.WARNING, logger="geoffrey_llm.audit"):
        client = AuditClient()
        assert client.enabled is False
        assert client.emit("test", "x") is False
        client.emit("test", "y")  # 第二次不应再告警
    warnings = [r for r in caplog.records if "未配置" in r.getMessage()]
    assert len(warnings) == 1
    assert client.stats() == {"queued": 0, "sent": 0, "dropped": 0, "failed": 0}


def test_emit_builds_full_payload(captured):
    client = make_client()
    assert client.emit(
        "auth", "user.login", actor_name="geoffrey", note="extra-goes-to-metadata"
    )
    assert client.flush(3.0)
    client.close()

    assert len(captured) == 1
    req = captured[0]
    assert req["url"] == "https://audit.test/api/v1/events/batch"
    assert req["headers"]["x-audit-app"] == "testapp"
    assert req["headers"]["x-audit-key"] == "test-key-123456"

    (event,) = req["events"]
    assert UUID_RE.match(event["event_id"])
    assert event["app"] == "testapp"
    assert event["event_type"] == "auth"
    assert event["action"] == "user.login"
    assert event["actor_name"] == "geoffrey"
    assert TIME_RE.match(event["occurred_at"])
    assert event["metadata"] == {"note": "extra-goes-to-metadata"}


def test_batching_splits_by_size_and_flush(captured):
    client = make_client(batch_size=20)
    for i in range(20):
        client.emit("t", "a%d" % i)
    assert client.flush(3.0)
    for i in range(5):
        client.emit("t", "b%d" % i)
    assert client.flush(3.0)
    client.close()

    assert [len(r["events"]) for r in captured] == [20, 5]
    assert client.stats()["sent"] == 25


def test_metadata_masking(captured):
    client = make_client()
    client.emit(
        "t",
        "x",
        metadata={
            "password": "p@ss",
            "note": "keep",
            "nested": {"api_key": "ak", "title": "ok"},
            "items": [{"session_id": "s1"}, {"name": "n"}],
        },
    )
    assert client.flush(3.0)
    client.close()

    meta = all_events(captured)[0]["metadata"]
    assert meta["password"] == "***"
    assert meta["note"] == "keep"
    assert meta["nested"] == {"api_key": "***", "title": "ok"}
    assert meta["items"] == [{"session_id": "***"}, {"name": "n"}]


def test_queue_full_drops_without_raising(captured):
    release = threading.Event()
    blocked = threading.Event()

    def blocking_urlopen(req, timeout=None):
        blocked.set()
        release.wait(5.0)
        return FakeResponse()

    import geoffrey_llm.audit.client as _mod

    original = _mod._urlopen
    _mod._urlopen = blocking_urlopen
    try:
        client = make_client(queue_size=5, batch_size=100, flush_interval=0.1)
        for i in range(20):
            client.emit("t", "e%d" % i)  # 不能抛异常
        assert blocked.wait(3.0)  # worker 确实开始发送(卡住)
        stats = client.stats()
        assert stats["dropped"] > 0
    finally:
        release.set()
        _mod._urlopen = original
    client.close()


def test_strict_missing_config_raises(clean_env):
    with pytest.raises(AuditConfigError):
        AuditClient(strict=True)


def test_send_failure_counts_and_does_not_raise(monkeypatch, clean_env):
    def failing_urlopen(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(client_mod, "_urlopen", failing_urlopen)
    client = make_client()
    client.emit("t", "x")
    assert client.flush(3.0)
    client.close()
    stats = client.stats()
    assert stats["failed"] == 1
    assert stats["sent"] == 0


# ---------------------------------------------------------------- decorator


def test_decorator_sync_success(captured, reset_singleton):
    configure(
        endpoint="https://audit.test/api/v1/events",
        app="testapp",
        key="k",
        flush_interval=0.05,
    )

    @audit_event(action="math.double", event_type="compute")
    def double(x):
        return x * 2

    assert double(21) == 42
    client = client_mod.get_client()
    assert client.flush(3.0)

    event = all_events(captured)[0]
    assert event["action"] == "math.double"
    assert event["event_type"] == "compute"
    assert event["success"] is True
    assert event["latency_ms"] >= 0


def test_decorator_exception_reraises_and_records(captured, reset_singleton):
    configure(
        endpoint="https://audit.test/api/v1/events",
        app="testapp",
        key="k",
        flush_interval=0.05,
    )

    @audit_event(action="boom")
    def failing():
        raise ValueError("boom message")

    with pytest.raises(ValueError, match="boom message"):
        failing()

    client = client_mod.get_client()
    assert client.flush(3.0)
    event = all_events(captured)[0]
    assert event["success"] is False
    assert event["risk_level"] == "high"
    assert event["metadata"]["error"] == "ValueError"
    assert event["metadata"]["error_message"] == "boom message"


def test_decorator_async(captured, reset_singleton):
    configure(
        endpoint="https://audit.test/api/v1/events",
        app="testapp",
        key="k",
        flush_interval=0.05,
    )

    @audit_event(action="async.add")
    async def add(a, b):
        await asyncio.sleep(0)
        return a + b

    assert asyncio.run(add(1, 2)) == 3
    client = client_mod.get_client()
    assert client.flush(3.0)
    event = all_events(captured)[0]
    assert event["action"] == "async.add"
    assert event["success"] is True


def test_decorator_lifts_named_args(captured, reset_singleton):
    configure(
        endpoint="https://audit.test/api/v1/events",
        app="testapp",
        key="k",
        flush_interval=0.05,
    )

    @audit_event(
        action="post.delete",
        actor_from="username",
        resource_type="post",
        resource_id_from="post_id",
    )
    def delete_post(username, post_id):
        return True

    assert delete_post("geoffrey", 42) is True
    client = client_mod.get_client()
    assert client.flush(3.0)
    event = all_events(captured)[0]
    assert event["actor_name"] == "geoffrey"
    assert event["resource_type"] == "post"
    assert event["resource_id"] == 42


def test_decorator_noop_when_unconfigured(clean_env, reset_singleton):
    configure()  # no-op 客户端

    @audit_event(action="never.sent")
    def pure(x):
        return x + 1

    assert pure(1) == 2  # 直通,不报错


# --------------------------------------------------------------- middleware


def test_asgi_middleware_records_request(captured, reset_singleton):
    configure(
        endpoint="https://audit.test/api/v1/events",
        app="testapp",
        key="k",
        flush_interval=0.05,
    )

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    wrapped = AuditASGIMiddleware(app)
    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request"}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/posts",
        "client": ("127.0.0.1", 55555),
        "headers": [
            (b"user-agent", b"test-agent/1.0"),
            (b"x-forwarded-for", b"9.9.9.9, 8.8.8.8"),
        ],
    }
    asyncio.run(wrapped(scope, receive, send))

    assert [m["type"] for m in sent] == ["http.response.start", "http.response.body"]
    client = client_mod.get_client()
    assert client.flush(3.0)
    event = all_events(captured)[0]
    assert event["method"] == "POST"
    assert event["path"] == "/api/posts"
    assert event["status_code"] == 201
    assert event["success"] is True
    assert event["client_ip"] == "9.9.9.9"  # X-Forwarded-For 优先
    assert event["user_agent"] == "test-agent/1.0"
    assert event["latency_ms"] >= 0


def test_asgi_middleware_skips_health_paths(captured, reset_singleton):
    configure(
        endpoint="https://audit.test/api/v1/events",
        app="testapp",
        key="k",
        flush_interval=0.05,
    )

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})

    wrapped = AuditASGIMiddleware(app)

    async def send(message):
        pass

    async def receive():
        return {"type": "http.request"}

    for path in ("/healthz", "/readyz"):
        asyncio.run(
            wrapped(
                {"type": "http", "method": "GET", "path": path, "headers": []},
                receive,
                send,
            )
        )
    client = client_mod.get_client()
    assert client.flush(1.0)
    assert all_events(captured) == []


def test_wsgi_middleware_records_request(captured, reset_singleton):
    configure(
        endpoint="https://audit.test/api/v1/events",
        app="testapp",
        key="k",
        flush_interval=0.05,
    )

    def app(environ, start_response):
        start_response("404 NOT FOUND", [("Content-Type", "text/plain")])
        return [b"gone"]

    wrapped = AuditWSGIMiddleware(app)
    environ = {
        "REQUEST_METHOD": "DELETE",
        "PATH_INFO": "/api/posts/9",
        "REMOTE_ADDR": "10.0.0.1",
        "HTTP_USER_AGENT": "wsgi-agent",
    }
    statuses = []

    def start_response(status, headers, exc_info=None):
        statuses.append(status)

    body = wrapped(environ, start_response)
    assert list(body) == [b"gone"]
    assert statuses == ["404 NOT FOUND"]

    client = client_mod.get_client()
    assert client.flush(3.0)
    event = all_events(captured)[0]
    assert event["method"] == "DELETE"
    assert event["path"] == "/api/posts/9"
    assert event["status_code"] == 404
    assert event["success"] is False
    assert event["risk_level"] == "medium"
    assert event["client_ip"] == "10.0.0.1"
