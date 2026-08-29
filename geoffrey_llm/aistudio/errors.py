"""AIStudio (Geo Lab 平台) API 错误定义。"""

from __future__ import annotations

from typing import Any, Optional

import httpx


class AIStudioError(Exception):
    """AIStudio 客户端基础异常。"""


class AIStudioConfigError(AIStudioError):
    """配置缺失(如未提供 admin_token)。"""


class AIStudioAPIError(AIStudioError):
    """AIStudio API 请求失败。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response: Optional[Any] = response
