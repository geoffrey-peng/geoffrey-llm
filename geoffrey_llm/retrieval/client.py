"""检索 API 客户端（重排序 / 嵌入向量）。

对接 ``https://api.geoffrey-peng.cc/api/v1`` 的 ``/rerank`` 与
``/embeddings`` 接口，用于 RAG 检索流程中的召回与精排。
"""

from __future__ import annotations

import os
from typing import Any, Optional, Union

import httpx

from .errors import RetrievalAPIError, RetrievalConfigError


class RetrievalClient:
    """访问个人检索 API（重排序 / 嵌入）。

    API Key 可通过 ``RETRIEVAL_API_KEY`` 环境变量提供，也可在构造时直接传入。
    """

    DEFAULT_BASE_URL = "https://api.geoffrey-peng.cc/api/v1"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("RETRIEVAL_API_KEY")
        if not self.api_key:
            raise RetrievalConfigError("未配置检索 API Key，请设置 RETRIEVAL_API_KEY")

        self.base_url = (
            base_url or os.getenv("RETRIEVAL_BASE_URL") or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        """关闭内部 HTTP 客户端。"""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "RetrievalClient":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self.api_key}"
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
            raise RetrievalAPIError(
                f"检索 API 请求失败 ({response.status_code}): {detail}",
                status_code=response.status_code,
                response=response,
            )
        if not response.content:
            return None
        return response.json()

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: Optional[int] = None,
    ) -> dict[str, Any]:
        """对候选文档按与查询的相关性精排。

        :param query: 查询文本。
        :param documents: 候选文档列表。
        :param top_n: 返回最相关的前 N 条，省略则返回全部排序结果。
        :return: API 原样返回的 JSON，含 ``results``（index/score/document）与
            ``total_time``。
        """
        payload: dict[str, Any] = {"query": query, "documents": documents}
        if top_n is not None:
            payload["top_n"] = top_n
        return self._request("POST", "/rerank", json=payload)

    def embeddings(
        self,
        texts: Union[str, list[str]],
        model: str = "bge-m3",
    ) -> dict[str, Any]:
        """获取文本的向量表示（BGE-M3 稠密 + 稀疏混合向量）。

        :param texts: 单个字符串或字符串列表。
        :param model: 嵌入模型名，默认 ``bge-m3``。
        :return: API 原样返回的 JSON，含 ``data``（index/object/dense_vec/sparse_vec）
            与 ``usage``。
        """
        if isinstance(texts, str):
            texts = [texts]
        return self._request(
            "POST",
            "/embeddings",
            json={"input": texts, "model": model},
        )
