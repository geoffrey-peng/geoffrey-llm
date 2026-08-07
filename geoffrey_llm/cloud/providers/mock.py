"""In-memory cloud provider used by tests and local examples."""

from dataclasses import replace
from typing import Dict, List, Optional

from ..config import CloudConfig
from ..errors import CloudError
from ..models import (
    Bucket, CloudInstance, DatabaseInstance, SecurityGroup, SecurityGroupActionResult,
    SecurityGroupRule, StorageObject, Subnet, Vpc,
)
from ..safety import ensure_mutation_allowed, ensure_rule_source_allowed
from .base import BaseCloudProvider


class MockCloudProvider(BaseCloudProvider):
    name = "mock"

    def __init__(self, config: CloudConfig):
        self.config = config
        region = config.region
        self._instances = [CloudInstance("mock", region, "i-demo", "demo-instance", "running", "small", "vpc-demo", "subnet-demo")]
        self._vpcs = [Vpc("mock", region, "vpc-demo", "demo-vpc", "10.0.0.0/16")]
        self._subnets = [Subnet("mock", region, "subnet-demo", "vpc-demo", "demo-subnet", "10.0.1.0/24", "zone-a")]
        self._groups = [SecurityGroup("mock", region, "sg-demo", "demo-security-group", vpc_id="vpc-demo")]
        self._rules: Dict[str, List[SecurityGroupRule]] = {"sg-demo": []}
        self._buckets = [Bucket("mock", region, "demo-bucket")]
        self._objects = {"demo-bucket": [StorageObject("mock", "demo-bucket", "example.txt", 12)]}
        self._databases = [DatabaseInstance("mock", region, "db-demo", "demo-db", "mysql", "8.0", "running", "basic", "vpc-demo", "subnet-demo")]

    def _get(self, values, resource_id: str):
        for value in values:
            if value.id == resource_id:
                return value
        raise CloudError(f"未找到资源: {resource_id}")

    def list_instances(self, *, vpc_id: Optional[str] = None) -> List[CloudInstance]:
        return [item for item in self._instances if not vpc_id or item.vpc_id == vpc_id]

    def get_instance(self, instance_id: str) -> CloudInstance:
        return self._get(self._instances, instance_id)

    def list_vpcs(self) -> List[Vpc]:
        return list(self._vpcs)

    def list_subnets(self, *, vpc_id: Optional[str] = None) -> List[Subnet]:
        return [item for item in self._subnets if not vpc_id or item.vpc_id == vpc_id]

    def list_security_groups(self, *, vpc_id: Optional[str] = None) -> List[SecurityGroup]:
        return [item for item in self._groups if not vpc_id or item.vpc_id == vpc_id]

    def get_security_group(self, group_id: str) -> SecurityGroup:
        return self._get(self._groups, group_id)

    def list_security_group_rules(self, group_id: str) -> List[SecurityGroupRule]:
        self.get_security_group(group_id)
        return list(self._rules[group_id])

    def authorize_security_group_rule(self, group_id, rule, *, dry_run=None, allow_public_cidr=False):
        self.get_security_group(group_id)
        ensure_rule_source_allowed(rule, allow_public_cidr)
        effective_dry_run = ensure_mutation_allowed(self.config, dry_run)
        if not effective_dry_run and rule not in self._rules[group_id]:
            self._rules[group_id].append(replace(rule))
        return SecurityGroupActionResult(self.name, self.config.region, f"authorize_{rule.direction}", group_id, not effective_dry_run, effective_dry_run)

    def revoke_security_group_rule(self, group_id, rule, *, dry_run=None):
        self.get_security_group(group_id)
        effective_dry_run = ensure_mutation_allowed(self.config, dry_run)
        changed = False
        if not effective_dry_run:
            try:
                self._rules[group_id].remove(rule)
                changed = True
            except ValueError:
                pass
        return SecurityGroupActionResult(self.name, self.config.region, f"revoke_{rule.direction}", group_id, changed, effective_dry_run)

    def list_buckets(self) -> List[Bucket]:
        return list(self._buckets)

    def list_objects(self, bucket: str, *, prefix: Optional[str] = None) -> List[StorageObject]:
        if bucket not in self._objects:
            raise CloudError(f"未找到存储桶: {bucket}")
        return [item for item in self._objects[bucket] if not prefix or item.key.startswith(prefix)]

    def list_databases(self) -> List[DatabaseInstance]:
        return list(self._databases)

    def get_database(self, database_id: str) -> DatabaseInstance:
        return self._get(self._databases, database_id)
