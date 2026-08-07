"""Unified entry point for supported cloud resource domains."""

from typing import Optional

from .config import CloudConfig
from .credentials import credential_source
from .models import SecurityGroupRule
from .registry import get_provider_registry


class _InstancesService:
    def __init__(self, provider): self._provider = provider
    def list(self, *, vpc_id: Optional[str] = None): return self._provider.list_instances(vpc_id=vpc_id)
    def get(self, instance_id: str): return self._provider.get_instance(instance_id)


class _NetworkService:
    def __init__(self, provider): self._provider = provider
    def list_vpcs(self): return self._provider.list_vpcs()
    def list_subnets(self, *, vpc_id: Optional[str] = None): return self._provider.list_subnets(vpc_id=vpc_id)


class _SecurityGroupService:
    def __init__(self, provider): self._provider = provider
    def list(self, *, vpc_id: Optional[str] = None): return self._provider.list_security_groups(vpc_id=vpc_id)
    def get(self, group_id: str): return self._provider.get_security_group(group_id)
    def list_rules(self, group_id: str): return self._provider.list_security_group_rules(group_id)
    def authorize(self, group_id: str, rule: SecurityGroupRule, *, dry_run: Optional[bool] = None, allow_public_cidr: bool = False):
        return self._provider.authorize_security_group_rule(group_id, rule, dry_run=dry_run, allow_public_cidr=allow_public_cidr)
    def revoke(self, group_id: str, rule: SecurityGroupRule, *, dry_run: Optional[bool] = None):
        return self._provider.revoke_security_group_rule(group_id, rule, dry_run=dry_run)


class _ObjectStorageService:
    def __init__(self, provider): self._provider = provider
    def list_buckets(self): return self._provider.list_buckets()
    def list_objects(self, bucket: str, *, prefix: Optional[str] = None): return self._provider.list_objects(bucket, prefix=prefix)


class _DatabasesService:
    def __init__(self, provider): self._provider = provider
    def list(self): return self._provider.list_databases()
    def get(self, database_id: str): return self._provider.get_database(database_id)


class CloudClient:
    """Cloud-provider-neutral façade for core infrastructure resources."""

    def __init__(self, config: CloudConfig):
        config.validate()
        self.config = config
        provider_class = get_provider_registry().get(config.provider)
        self.provider = provider_class(config)
        self.instances = _InstancesService(self.provider)
        self.network = _NetworkService(self.provider)
        self.security_groups = _SecurityGroupService(self.provider)
        self.object_storage = _ObjectStorageService(self.provider)
        self.databases = _DatabasesService(self.provider)

    @property
    def credential_source(self) -> str:
        """Non-sensitive credential resolution diagnostic."""
        return credential_source(self.config.provider, self.config.profile)
