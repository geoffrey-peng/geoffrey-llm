"""Guardrails for cloud mutations."""

from typing import Optional

from .config import CloudConfig
from .errors import CloudSafetyError
from .models import SecurityGroupRule


def ensure_mutation_allowed(config: CloudConfig, dry_run: Optional[bool]) -> bool:
    effective_dry_run = config.dry_run_default if dry_run is None else dry_run
    if effective_dry_run:
        return True
    if not config.mutations_enabled:
        raise CloudSafetyError("真实云资源变更需要 read_only=False 且 allow_mutation=True")
    return False


def ensure_rule_source_allowed(rule: SecurityGroupRule, allow_public_cidr: bool) -> None:
    if rule.cidr in {"0.0.0.0/0", "::/0"} and not allow_public_cidr:
        raise CloudSafetyError("开放公网 CIDR 需要显式设置 allow_public_cidr=True")
