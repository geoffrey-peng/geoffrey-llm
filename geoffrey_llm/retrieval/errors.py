"""检索客户端异常。"""

from typing import Optional

from geoffrey_llm.common.errors import GeoffreyError


class RetrievalConfigError(GeoffreyError):
    """检索客户端配置错误。"""


class RetrievalAPIError(GeoffreyError):
    """检索 API 返回错误。"""

    def __init__(self, message: str, status_code: Optional[int] = None, response: object = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
