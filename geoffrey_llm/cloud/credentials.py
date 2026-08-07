"""Runtime-only credential-chain diagnostics.

Secret values are deliberately never accepted by CloudConfig or returned here.
Actual credential loading is delegated to each official vendor SDK adapter.
"""

import os
from typing import Optional


_ENV_NAMES = {
    "alibaba": ("ALIBABA_CLOUD_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
    "tencent": ("TENCENTCLOUD_SECRET_ID", "TENCENTCLOUD_SECRET_KEY"),
    "huawei": ("HUAWEICLOUD_SDK_AK", "HUAWEICLOUD_SDK_SK"),
    "aws": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"),
}


def credential_source(provider: str, profile: Optional[str] = None) -> str:
    """Return a non-sensitive description of the likely credential source."""
    name = provider.lower()
    if profile:
        return f"profile:{profile}"
    if name == "aws" and os.getenv("AWS_PROFILE"):
        return f"profile:{os.environ['AWS_PROFILE']}"
    names = _ENV_NAMES.get(name, ())
    if names and all(os.getenv(value) for value in names):
        return "environment"
    if name == "aws" and os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE"):
        return "web_identity"
    return "official_sdk_default_chain"
