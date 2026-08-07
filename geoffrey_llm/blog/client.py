"""博客系统 REST API 客户端。"""

from __future__ import annotations

import os
from typing import Any, Optional, Union

import httpx

from .errors import BlogAPIError, BlogConfigError


class BlogClient:
    """访问个人博客 REST API。

    Token 可通过 ``BLOG_API_TOKEN``、``BLOG_SECRET`` 或用户现有的
    ``BLOG_SERCET`` 环境变量提供。这里的 token 对应博客的 ``API_TOKEN``，
    不是 Flask 的 ``SECRET_KEY``。
    """

    DEFAULT_BASE_URL = "https://blog.geoffrey-peng.cc"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.token = token or self._get_token()
        if not self.token:
            raise BlogConfigError(
                "未配置博客 API Token，请设置 BLOG_API_TOKEN、BLOG_SECRET 或 BLOG_SERCET"
            )

        self.base_url = (base_url or os.getenv("BLOG_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    @staticmethod
    def _get_token() -> Optional[str]:
        return (
            os.getenv("BLOG_API_TOKEN")
            or os.getenv("BLOG_SECRET")
            or os.getenv("BLOG_SERCET")
        )

    def close(self) -> None:
        """关闭内部 HTTP 客户端。"""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "BlogClient":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self.token}"
        response = self._client.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            **kwargs,
        )
        if response.is_error:
            try:
                detail = response.json().get("error", response.text)
            except (ValueError, AttributeError):
                detail = response.text
            raise BlogAPIError(
                f"博客 API 请求失败 ({response.status_code}): {detail}",
                status_code=response.status_code,
                response=response,
            )
        if not response.content:
            return None
        return response.json()

    def list_categories(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/categories")

    def list_posts(
        self,
        page: int = 1,
        per_page: int = 20,
        category_id: Optional[int] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if category_id is not None:
            params["category_id"] = category_id
        return self._request("GET", "/api/posts", params=params)

    def get_post(self, post_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/posts/{post_id}")

    def create_post(
        self,
        title: str,
        slug: str,
        content: str,
        category_id: int,
        is_public: bool = True,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/posts",
            json={
                "title": title,
                "slug": slug,
                "content": content,
                "category_id": category_id,
                "is_public": is_public,
            },
        )

    def update_post(self, post_id: int, **fields: Any) -> dict[str, Any]:
        allowed = {"title", "slug", "content", "category_id", "is_public"}
        payload = {key: value for key, value in fields.items() if key in allowed}
        if not payload:
            raise BlogConfigError("update_post 至少需要一个可更新字段")
        return self._request("PUT", f"/api/posts/{post_id}", json=payload)

    def delete_post(self, post_id: int) -> dict[str, Any]:
        return self._request("DELETE", f"/api/posts/{post_id}")

    def create_share(
        self, post_id: int, expires_days: Optional[int] = None
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/posts/{post_id}/shares",
            json={"expires_days": expires_days},
        )

    def list_shares(self, post_id: Optional[int] = None) -> list[dict[str, Any]]:
        params = {"post_id": post_id} if post_id is not None else None
        return self._request("GET", "/api/shares", params=params)

    def revoke_share(self, identifier: Union[int, str]) -> dict[str, Any]:
        return self._request("DELETE", f"/api/shares/{identifier}")
