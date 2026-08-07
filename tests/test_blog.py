import json

import httpx
import pytest

from geoffrey_llm.blog import BlogAPIError, BlogClient, BlogConfigError


def make_client(handler):
    transport = httpx.MockTransport(handler)
    return BlogClient(token="test-token", base_url="https://blog.test", client=httpx.Client(transport=transport))


def test_reads_existing_secret_env_name(monkeypatch):
    monkeypatch.delenv("BLOG_API_TOKEN", raising=False)
    monkeypatch.delenv("BLOG_SECRET", raising=False)
    monkeypatch.setenv("BLOG_SERCET", "legacy-token")
    client = BlogClient(base_url="https://blog.test")
    assert client.token == "legacy-token"
    client.close()


def test_missing_token_raises(monkeypatch):
    for name in ("BLOG_API_TOKEN", "BLOG_SECRET", "BLOG_SERCET"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(BlogConfigError):
        BlogClient(base_url="https://blog.test")


def test_list_posts_sends_auth_and_params():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.path == "/api/posts"
        assert request.url.params["page"] == "2"
        assert request.url.params["per_page"] == "10"
        assert request.url.params["category_id"] == "3"
        return httpx.Response(200, json={"posts": [], "page": 2})

    with make_client(handler) as client:
        assert client.list_posts(page=2, per_page=10, category_id=3) == {"posts": [], "page": 2}


def test_create_update_and_delete_post():
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={"id": 4})
        if request.method == "PUT":
            return httpx.Response(200, json={"id": 4, "title": "Updated"})
        return httpx.Response(200, json={"message": "deleted"})

    with make_client(handler) as client:
        assert client.create_post("Title", "title", "Body", 1)["id"] == 4
        assert client.update_post(4, title="Updated")["title"] == "Updated"
        assert client.delete_post(4)["message"] == "deleted"

    assert requests[0].url.path == "/api/posts"
    assert json.loads(requests[0].content) == {
        "title": "Title",
        "slug": "title",
        "content": "Body",
        "category_id": 1,
        "is_public": True,
    }
    assert json.loads(requests[1].content) == {"title": "Updated"}
    assert requests[2].url.path == "/api/posts/4"


def test_share_methods():
    def handler(request):
        if request.method == "POST":
            assert request.url.path == "/api/posts/4/shares"
            assert json.loads(request.content) == {"expires_days": 7}
            return httpx.Response(200, json={"token": "abc"})
        if request.method == "GET":
            assert request.url.params["post_id"] == "4"
            return httpx.Response(200, json=[])
        assert request.url.path == "/api/shares/abc"
        return httpx.Response(200, json={"message": "revoked"})

    with make_client(handler) as client:
        assert client.create_share(4, 7) == {"token": "abc"}
        assert client.list_shares(4) == []
        assert client.revoke_share("abc")["message"] == "revoked"


def test_api_error_exposes_status_code():
    def handler(request):
        return httpx.Response(401, json={"error": "Unauthorized"})

    with make_client(handler) as client:
        with pytest.raises(BlogAPIError, match="Unauthorized") as exc_info:
            client.get_post(99)
    assert exc_info.value.status_code == 401


def test_update_requires_fields():
    with make_client(lambda request: httpx.Response(200, json={})) as client:
        with pytest.raises(BlogConfigError):
            client.update_post(1)
