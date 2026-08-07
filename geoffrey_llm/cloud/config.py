"""Cloud client configuration."""

from dataclasses import dataclass
from typing import Optional

from ..common.config import BaseConfig


@dataclass
class CloudConfig(BaseConfig):
    provider: str
    region: str
    profile: Optional[str] = None
    timeout: int = 30
    read_only: bool = True
    allow_mutation: bool = False
    dry_run_default: bool = True

    def validate(self) -> None:
        if not self.provider.strip():
            raise ValueError("云厂商不能为空")
        if not self.region.strip():
            raise ValueError("云区域不能为空")
        if self.timeout <= 0:
            raise ValueError("timeout 必须大于 0")
        if self.read_only and self.allow_mutation:
            raise ValueError("read_only=True 时不能设置 allow_mutation=True")

    @property
    def mutations_enabled(self) -> bool:
        return not self.read_only and self.allow_mutation
