"""Shared helpers for official-SDK cloud adapters."""

from typing import List, Optional

from ..config import CloudConfig
from ..errors import CloudDependencyError, CloudError
from ..models import (
    Bucket, CloudInstance, DatabaseInstance, SecurityGroup, SecurityGroupActionResult,
    SecurityGroupRule, StorageObject, Subnet, Vpc,
)
from .base import BaseCloudProvider


class OfficialSdkProvider(BaseCloudProvider):
    """Base class for adapters that lazily initialize an official SDK."""

    install_extra: str

    def __init__(self, config: CloudConfig):
        config.validate()
        self.config = config

    def _dependency_error(self, package: str) -> CloudDependencyError:
        return CloudDependencyError(f"缺少 {package}；请安装 geoffrey-llm[{self.install_extra}]")

    def _import(self, module_name: str):
        """Import a vendor SDK module, converting any load failure to CloudDependencyError.

        This also covers installed-but-broken SDKs (import raises a non-ImportError),
        so callers always get a consistent, actionable error.
        """
        import importlib

        try:
            return importlib.import_module(module_name)
        except Exception as error:
            raise self._dependency_error(module_name.split(".")[0]) from error

    def _unsupported(self, operation: str):
        raise CloudError(f"云厂商 {self.name} 尚未实现操作: {operation}")

    def list_instances(self, *, vpc_id: Optional[str] = None) -> List[CloudInstance]:
        return self._unsupported("list_instances")

    def get_instance(self, instance_id: str) -> CloudInstance:
        return self._unsupported("get_instance")

    def list_vpcs(self) -> List[Vpc]:
        return self._unsupported("list_vpcs")

    def list_subnets(self, *, vpc_id: Optional[str] = None) -> List[Subnet]:
        return self._unsupported("list_subnets")

    def list_security_groups(self, *, vpc_id: Optional[str] = None) -> List[SecurityGroup]:
        return self._unsupported("list_security_groups")

    def get_security_group(self, group_id: str) -> SecurityGroup:
        return self._unsupported("get_security_group")

    def list_security_group_rules(self, group_id: str) -> List[SecurityGroupRule]:
        return self._unsupported("list_security_group_rules")

    def authorize_security_group_rule(self, group_id: str, rule: SecurityGroupRule, *, dry_run=None, allow_public_cidr=False) -> SecurityGroupActionResult:
        return self._unsupported("authorize_security_group_rule")

    def revoke_security_group_rule(self, group_id: str, rule: SecurityGroupRule, *, dry_run=None) -> SecurityGroupActionResult:
        return self._unsupported("revoke_security_group_rule")

    def list_buckets(self) -> List[Bucket]:
        return self._unsupported("list_buckets")

    def list_objects(self, bucket: str, *, prefix: Optional[str] = None) -> List[StorageObject]:
        return self._unsupported("list_objects")

    def list_databases(self) -> List[DatabaseInstance]:
        return self._unsupported("list_databases")

    def get_database(self, database_id: str) -> DatabaseInstance:
        return self._unsupported("get_database")
