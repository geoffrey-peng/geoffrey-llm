"""AIStudio (Geo Lab 平台) REST API 客户端。

对接自建 LLM 网关平台(api-platform)的两类资源:

1. Prompt 提示词管理(需要 admin_token):
   - list_prompts()    列出全部提示词(含停用)
   - get_prompt(pid)   按 ID 查看单个提示词
   - create_prompt()   创建
   - update_prompt()   修改
   - delete_prompt()   删除

   提示词 ID 为平台生成的 UUID(形如 ``3e4b2bf6-9498-...``),
   创建后即固定,可用于后续查看/修改/删除,不是从 1 开始的数字序号。

2. Agent 智能体调用:
   - list_agents() / get_agent() 查看已创建的智能体(需要 admin_token)
   - chat()                      调用已发布的智能体对话(agent_api_key 或 admin_token 均可)

用法::

    from geoffrey_llm.aistudio import AIStudioClient

    with AIStudioClient(base_url="http://localhost:8001", admin_token="eyJ...") as cli:
        # 提示词管理
        for p in cli.list_prompts():
            print(p["id"], p["name"])
        prompt = cli.create_prompt(name="测试", content="你是一个测试助手")
        cli.update_prompt(prompt["id"], description="改一下描述")
        cli.delete_prompt(prompt["id"])

        # 调用已发布的智能体
        agents = cli.list_agents()
        app_id = agents["agents"][0]["app_id"]
        reply = cli.chat(app_id, [{"role": "user", "content": "你好"}],
                         api_key="agent-xxxx")
        print(reply["content"])
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from .errors import AIStudioAPIError, AIStudioConfigError


class AIStudioClient:
    """访问 AIStudio (Geo Lab 平台) REST API。

    - ``admin_token``: 管理员 JWT(平台「管理员登录」接口签发),
      管理类操作(提示词 CRUD / 智能体查看)必需,
      也可通过环境变量 ``AISTUDIO_ADMIN_TOKEN`` 提供。
    - ``agent_api_key``: 智能体发布后签发的 ``agent-xxx`` Key,
      调用智能体对话时优先使用;未提供时回退 admin_token(便于调试)。
      也可通过环境变量 ``AISTUDIO_AGENT_KEY`` 提供。
    """

    DEFAULT_BASE_URL = "http://localhost:8001"
    DEFAULT_TIMEOUT = 60.0

    def __init__(
        self,
        admin_token: Optional[str] = None,
        agent_api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.admin_token = admin_token or os.getenv("AISTUDIO_ADMIN_TOKEN") or ""
        self.agent_api_key = agent_api_key or os.getenv("AISTUDIO_AGENT_KEY") or ""
        self.base_url = (base_url or os.getenv("AISTUDIO_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "AIStudioClient":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    # ---------- 内部 ----------
    def _request(
        self,
        method: str,
        path: str,
        *,
        token: Optional[str] = None,
        error_prefix: str = "AIStudio API 请求失败",
        **kwargs: Any,
    ) -> Any:
        headers = dict(kwargs.pop("headers", {}))
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self._client.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except (ValueError, AttributeError):
                detail = response.text
            raise AIStudioAPIError(
                f"{error_prefix} ({response.status_code}): {detail}",
                status_code=response.status_code,
                response=response,
            )
        if not response.content:
            return None
        return response.json()

    def _require_admin(self) -> str:
        if not self.admin_token:
            raise AIStudioConfigError(
                "未配置管理员令牌,请传入 admin_token 或设置 AISTUDIO_ADMIN_TOKEN 环境变量"
            )
        return self.admin_token

    # ---------- Prompt 提示词管理 ----------
    def list_prompts(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        """列出提示词。

        - ``include_inactive=False``: 走公开接口,仅返回已启用的(无需 admin_token)
        - ``include_inactive=True``: 走管理接口,返回全部(含停用,需要 admin_token)
        每条记录包含 ``id``(UUID)、``name``、``category``、``content`` 等字段。
        """
        if include_inactive:
            return self._request(
                "GET", "/api/v1/admin/prompts",
                token=self._require_admin(), error_prefix="列出提示词失败",
            )
        return self._request("GET", "/api/v1/prompts", error_prefix="列出提示词失败")

    def get_prompt(self, prompt_id: str) -> dict[str, Any]:
        """按 ID 查看单个提示词(ID 为平台生成的 UUID)。"""
        return self._request(
            "GET", f"/api/v1/admin/prompts/{prompt_id}",
            token=self._require_admin(), error_prefix="查看提示词失败",
        )

    def create_prompt(
        self,
        name: str,
        content: str,
        category: str = "通用",
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> dict[str, Any]:
        """创建提示词,返回含 ``id`` 的完整记录。"""
        return self._request(
            "POST", "/api/v1/admin/prompts",
            token=self._require_admin(), error_prefix="创建提示词失败",
            json={
                "name": name,
                "content": content,
                "category": category,
                "description": description,
                "is_active": is_active,
            },
        )

    def update_prompt(self, prompt_id: str, **fields: Any) -> dict[str, Any]:
        """修改提示词,可传 ``name/content/category/description/is_active`` 任意组合。"""
        if not fields:
            raise AIStudioConfigError("update_prompt 至少需要提供一个要修改的字段")
        return self._request(
            "PUT", f"/api/v1/admin/prompts/{prompt_id}",
            token=self._require_admin(), error_prefix="修改提示词失败",
            json=fields,
        )

    def delete_prompt(self, prompt_id: str) -> dict[str, Any]:
        """删除提示词。"""
        return self._request(
            "DELETE", f"/api/v1/admin/prompts/{prompt_id}",
            token=self._require_admin(), error_prefix="删除提示词失败",
        )

    # ---------- Agent 智能体 ----------
    def list_agents(self) -> dict[str, Any]:
        """列出全部智能体应用(需要 admin_token)。"""
        return self._request(
            "GET", "/api/v1/admin/agents",
            token=self._require_admin(), error_prefix="列出智能体失败",
        )

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        """按 ID 查看智能体配置(需要 admin_token)。"""
        return self._request(
            "GET", f"/api/v1/admin/agents/{agent_id}",
            token=self._require_admin(), error_prefix="查看智能体失败",
        )

    def chat(
        self,
        app_id: str,
        messages: list[dict[str, str]],
        *,
        api_key: Optional[str] = None,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """调用已发布的智能体对话。

        - ``app_id``: 智能体的应用 ID(``app-xxx``,见发布渠道页或 list_agents)
        - ``messages``: OpenAI 格式消息列表
        - ``api_key``: ``agent-xxx`` Key;未传入时依次回退
          构造参数 ``agent_api_key`` / 环境变量 ``AISTUDIO_AGENT_KEY`` / admin_token

        返回 ``{"content", "usage", "sources", "model"}``,
        ``sources`` 为智能体引用的知识库切片。
        """
        key = api_key or self.agent_api_key or self.admin_token
        if not key:
            raise AIStudioConfigError(
                "调用智能体需要 API Key(agent-xxx)或管理员令牌,"
                "请传入 api_key 或设置 AISTUDIO_AGENT_KEY / AISTUDIO_ADMIN_TOKEN"
            )
        if not app_id:
            raise AIStudioConfigError("chat() 需要传入智能体的 app_id")
        return self._request(
            "POST", f"/api/v1/agent/{app_id}/chat",
            token=key, error_prefix="智能体调用失败",
            json={"messages": messages, "top_k": top_k},
        )
