"""AIStudio (Geo Lab 平台) REST API 客户端。

安装:
    pip install geoffrey-llm[aistudio]

功能:
    - 提示词管理: 创建 / 查看 / 修改 / 删除(ID 为平台生成的 UUID)
    - 智能体调用: 调用已发布 Agent 的对话接口
"""

from .client import AIStudioClient
from .errors import AIStudioAPIError, AIStudioConfigError, AIStudioError

__all__ = ["AIStudioClient", "AIStudioError", "AIStudioAPIError", "AIStudioConfigError"]
