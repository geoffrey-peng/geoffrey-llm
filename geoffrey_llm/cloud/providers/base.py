"""Provider contracts for unified cloud services."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import (
    Bucket,
    CloudInstance,
    DatabaseInstance,
    SecurityGroup,
    SecurityGroupActionResult,
    SecurityGroupRule,
    StorageObject,
    Subnet,
    Vpc,
)


class BaseCloudProvider(ABC):
    name: str

    @abstractmethod
    def list_instances(self, *, vpc_id: Optional[str] = None) -> List[CloudInstance]:
        pass

    @abstractmethod
    def get_instance(self, instance_id: str) -> CloudInstance:
        pass

    @abstractmethod
    def list_vpcs(self) -> List[Vpc]:
        pass

    @abstractmethod
    def list_subnets(self, *, vpc_id: Optional[str] = None) -> List[Subnet]:
        pass

    @abstractmethod
    def list_security_groups(self, *, vpc_id: Optional[str] = None) -> List[SecurityGroup]:
        pass

    @abstractmethod
    def get_security_group(self, group_id: str) -> SecurityGroup:
        pass

    @abstractmethod
    def list_security_group_rules(self, group_id: str) -> List[SecurityGroupRule]:
        pass

    @abstractmethod
    def authorize_security_group_rule(
        self, group_id: str, rule: SecurityGroupRule, *, dry_run: Optional[bool] = None,
        allow_public_cidr: bool = False,
    ) -> SecurityGroupActionResult:
        pass

    @abstractmethod
    def revoke_security_group_rule(
        self, group_id: str, rule: SecurityGroupRule, *, dry_run: Optional[bool] = None,
    ) -> SecurityGroupActionResult:
        pass

    @abstractmethod
    def list_buckets(self) -> List[Bucket]:
        pass

    @abstractmethod
    def list_objects(self, bucket: str, *, prefix: Optional[str] = None) -> List[StorageObject]:
        pass

    @abstractmethod
    def list_databases(self) -> List[DatabaseInstance]:
        pass

    @abstractmethod
    def get_database(self, database_id: str) -> DatabaseInstance:
        pass
