"""博客客户端异常。"""

from typing import Optional

from geoffrey_llm.common.errors import GeoffreyError


class BlogConfigError(GeoffreyError):
    """博客客户端配置错误。"""


class BlogAPIError(GeoffreyError):
    """博客 API 返回错误。"""

    def __init__(self, message: str, status_code: Optional[int] = None, response: object = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
