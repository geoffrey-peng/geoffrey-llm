"""检索 REST API 客户端（重排序 / 嵌入）。

安装:
    pip install geoffrey-llm[retrieval]
"""

from .client import RetrievalClient
from .errors import RetrievalAPIError, RetrievalConfigError

__all__ = ["RetrievalClient", "RetrievalAPIError", "RetrievalConfigError"]
