"""Tencent Cloud adapter backed by tencentcloud-sdk-python and cos-python-sdk-v5.

Service clients are created lazily per domain. Credentials come from the
official ``DefaultCredentialProvider`` chain; no secret material is accepted
by ``CloudConfig`` or stored here.

Official references: .cloud/tencent/README.md
"""

from typing import Any, Dict, List, Optional

from ..errors import CloudError
from ..models import (
    Bucket, CloudInstance, DatabaseInstance, SecurityGroup, SecurityGroupActionResult,
    SecurityGroupRule, StorageObject, Subnet, Vpc,
)
from ..safety import ensure_mutation_allowed, ensure_rule_source_allowed
from .sdk_base import OfficialSdkProvider

_CDB_STATUS = {0: "creating", 1: "running", 4: "deleting", 5: "isolated", 6: "isolated"}


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    return getattr(obj, name, default)


class TencentCloudProvider(OfficialSdkProvider):
    name = "tencent"
    install_extra = "cloud-tencent"

    def __init__(self, config):
        super().__init__(config)
        self._credential = None
        self._cvm_client = None
        self._vpc_client = None
        self._cdb_client = None
        self._cos_client = None

    # ---- lazy official SDK clients ----

    def _credentials(self):
        if self._credential is None:
            try:
                from tencentcloud.common import credential
            except Exception as error:
                raise self._dependency_error("tencentcloud-sdk-python-common") from error
            self._credential = credential.DefaultCredentialProvider().get_credential()
        return self._credential

    def _cvm(self):
        if self._cvm_client is None:
            try:
                from tencentcloud.cvm.v20170312 import cvm_client
            except Exception as error:
                raise self._dependency_error("tencentcloud-sdk-python-cvm") from error
            self._cvm_client = cvm_client.CvmClient(self._credentials(), self.config.region)
        return self._cvm_client

    def _vpc(self):
        if self._vpc_client is None:
            try:
                from tencentcloud.vpc.v20170312 import vpc_client
            except Exception as error:
                raise self._dependency_error("tencentcloud-sdk-python-vpc") from error
            self._vpc_client = vpc_client.VpcClient(self._credentials(), self.config.region)
        return self._vpc_client

    def _cdb(self):
        if self._cdb_client is None:
            try:
                from tencentcloud.cdb.v20170320 import cdb_client
            except Exception as error:
                raise self._dependency_error("tencentcloud-sdk-python-cdb") from error
            self._cdb_client = cdb_client.CdbClient(self._credentials(), self.config.region)
        return self._cdb_client

    def _cos(self):
        if self._cos_client is None:
            try:
                from qcloud_cos import CosConfig, CosS3Client
            except Exception as error:
                raise self._dependency_error("cos-python-sdk-v5") from error
            cred = self._credentials()
            self._cos_client = CosS3Client(CosConfig(
                Region=self.config.region,
                SecretId=getattr(cred, "secretId", None),
                SecretKey=getattr(cred, "secretKey", None),
                Token=getattr(cred, "token", None),
                Scheme="https",
            ))
        return self._cos_client

    # ---- mapping helpers ----

    @staticmethod
    def _tags(tag_items) -> Dict[str, str]:
        values: Dict[str, str] = {}
        for item in tag_items or []:
            if isinstance(item, dict):
                key = item.get("Key")
                if key is not None:
                    values[key] = item.get("Value", "")
            else:
                key = getattr(item, "Key", None)
                if key is not None:
                    values[key] = getattr(item, "Value", "")
        return values

    def _instance(self, item) -> CloudInstance:
        vpc = _get(item, "VirtualPrivateCloud")
        state = _get(item, "InstanceState")
        return CloudInstance(
            provider=self.name,
            region=self.config.region,
            id=_get(item, "InstanceId", ""),
            name=_get(item, "InstanceName"),
            status=(state or "").lower() or None,
            instance_type=_get(item, "InstanceType"),
            vpc_id=_get(vpc, "VpcId"),
            subnet_id=_get(vpc, "SubnetId"),
            private_ips=list(_get(vpc, "PrivateIpAddresses") or []),
            public_ips=list(_get(item, "PublicIpAddresses") or []),
            tags=self._tags(_get(item, "Tags")),
        )

    def _security_group(self, item) -> SecurityGroup:
        return SecurityGroup(
            provider=self.name, region=self.config.region, id=_get(item, "SecurityGroupId", ""),
            name=_get(item, "SecurityGroupName"),
            description=_get(item, "SecurityGroupDescription"),
            vpc_id=_get(item, "VpcId"),
            tags=self._tags(_get(item, "Tags")),
        )

    def _rule(self, direction: str, item) -> SecurityGroupRule:
        protocol = (_get(item, "Protocol") or "all").lower()
        port = _get(item, "Port")
        port_range = None
        if port and str(port) != "ALL":
            port_range = f"{port}/{port}" if "-" not in str(port) else str(port).replace("-", "/")
        action = (_get(item, "Action") or "ACCEPT").lower()
        return SecurityGroupRule(
            direction=direction,
            protocol=protocol,
            port_range=port_range,
            cidr=_get(item, "CidrBlock"),
            source_group_id=_get(item, "SecurityGroupIdPrefix"),
            description=_get(item, "PolicyDescription"),
            policy="accept" if action == "accept" else "drop",
        )

    def _database(self, item) -> DatabaseInstance:
        status = _get(item, "Status")
        return DatabaseInstance(
            provider=self.name,
            region=self.config.region,
            id=_get(item, "InstanceId", ""),
            name=_get(item, "InstanceName"),
            engine=(_get(item, "Engine") or "").lower() or None,
            engine_version=_get(item, "EngineVersion"),
            status=_CDB_STATUS.get(status, str(status)) if status is not None else None,
            instance_class=str(_get(item, "InstanceType")) if _get(item, "InstanceType") is not None else None,
            vpc_id=_get(item, "VpcId"),
            subnet_id=_get(item, "SubnetId"),
            endpoint=_get(item, "Vip"),
            port=_get(item, "Vport"),
            tags=self._tags(_get(item, "Tags")),
        )

    # ---- compute ----

    def list_instances(self, *, vpc_id: Optional[str] = None) -> List[CloudInstance]:
        cvm_models = self._import("tencentcloud.cvm.v20170312.models")
        request = cvm_models.DescribeInstancesRequest()
        request.Offset = 0
        request.Limit = 100
        if vpc_id:
            request.Filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
        response = self._cvm().DescribeInstances(request)
        return [self._instance(item) for item in (_get(response, "InstanceSet") or [])]

    def get_instance(self, instance_id: str) -> CloudInstance:
        cvm_models = self._import("tencentcloud.cvm.v20170312.models")
        request = cvm_models.DescribeInstancesRequest()
        request.InstanceIds = [instance_id]
        response = self._cvm().DescribeInstances(request)
        items = _get(response, "InstanceSet") or []
        if not items:
            raise CloudError(f"未找到实例: {instance_id}")
        return self._instance(items[0])

    # ---- network ----

    def list_vpcs(self) -> List[Vpc]:
        vpc_models = self._import("tencentcloud.vpc.v20170312.models")
        request = vpc_models.DescribeVpcsRequest()
        request.Offset = 0
        request.Limit = 100
        response = self._vpc().DescribeVpcs(request)
        return [
            Vpc(self.name, self.config.region, _get(item, "VpcId", ""),
                _get(item, "VpcName"), _get(item, "CidrBlock"), None)
            for item in (_get(response, "VpcSet") or [])
        ]

    def list_subnets(self, *, vpc_id: Optional[str] = None) -> List[Subnet]:
        vpc_models = self._import("tencentcloud.vpc.v20170312.models")
        request = vpc_models.DescribeSubnetsRequest()
        request.Offset = 0
        request.Limit = 100
        if vpc_id:
            request.Filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
        response = self._vpc().DescribeSubnets(request)
        return [
            Subnet(self.name, self.config.region, _get(item, "SubnetId", ""),
                   _get(item, "VpcId", ""), _get(item, "SubnetName"),
                   _get(item, "CidrBlock"), _get(item, "Zone"),
                   _get(item, "AvailableIpAddressCount"))
            for item in (_get(response, "SubnetSet") or [])
        ]

    # ---- security groups ----

    def list_security_groups(self, *, vpc_id: Optional[str] = None) -> List[SecurityGroup]:
        vpc_models = self._import("tencentcloud.vpc.v20170312.models")
        request = vpc_models.DescribeSecurityGroupsRequest()
        request.Offset = 0
        request.Limit = 100
        if vpc_id:
            request.Filters = [{"Name": "vpc-id", "Values": [vpc_id]}]
        response = self._vpc().DescribeSecurityGroups(request)
        return [self._security_group(item) for item in (_get(response, "SecurityGroupSet") or [])]

    def get_security_group(self, group_id: str) -> SecurityGroup:
        vpc_models = self._import("tencentcloud.vpc.v20170312.models")
        request = vpc_models.DescribeSecurityGroupsRequest()
        request.SecurityGroupIds = [group_id]
        response = self._vpc().DescribeSecurityGroups(request)
        items = _get(response, "SecurityGroupSet") or []
        if not items:
            raise CloudError(f"未找到安全组: {group_id}")
        return self._security_group(items[0])

    def list_security_group_rules(self, group_id: str) -> List[SecurityGroupRule]:
        vpc_models = self._import("tencentcloud.vpc.v20170312.models")
        request = vpc_models.DescribeSecurityGroupAttributeRequest()
        request.SecurityGroupId = group_id
        response = self._vpc().DescribeSecurityGroupAttribute(request)
        policy_set = _get(response, "SecurityGroupPolicySet")
        rules = []
        for direction, key in (("ingress", "Ingress"), ("egress", "Egress")):
            for item in (_get(policy_set, key) or []):
                rules.append(self._rule(direction, item))
        return rules

    def _policy_version(self, group_id: str) -> int:
        vpc_models = self._import("tencentcloud.vpc.v20170312.models")
        request = vpc_models.DescribeSecurityGroupAttributeRequest()
        request.SecurityGroupId = group_id
        response = self._vpc().DescribeSecurityGroupAttribute(request)
        return _get(_get(response, "SecurityGroupPolicySet"), "Version", 0) or 0

    @staticmethod
    def _policy_dict(rule: SecurityGroupRule) -> Dict[str, Any]:
        port = "ALL"
        if rule.port_range:
            start, end = rule.port_range.split("/", 1)
            port = start if start == end else f"{start}-{end}"
        value: Dict[str, Any] = {
            "Protocol": (rule.protocol or "all").upper(),
            "Port": port,
            "Action": "ACCEPT" if rule.policy == "accept" else "DROP",
        }
        if rule.cidr:
            value["CidrBlock"] = rule.cidr
        if rule.source_group_id:
            value["SecurityGroupIdPrefix"] = rule.source_group_id
        if rule.description:
            value["PolicyDescription"] = rule.description
        return value

    def _policy_request(self, verb: str, group_id: str, rule: SecurityGroupRule, version: int):
        vpc_models = self._import("tencentcloud.vpc.v20170312.models")
        request = getattr(vpc_models, f"{verb}SecurityGroupPoliciesRequest")()
        request.SecurityGroupId = group_id
        key = "Ingress" if rule.direction == "ingress" else "Egress"
        request.SecurityGroupPolicySet = {"Version": version, key: [self._policy_dict(rule)]}
        return request

    def authorize_security_group_rule(self, group_id, rule, *, dry_run=None, allow_public_cidr=False):
        ensure_rule_source_allowed(rule, allow_public_cidr)
        action = f"authorize_{rule.direction}"
        if ensure_mutation_allowed(self.config, dry_run):
            return SecurityGroupActionResult(self.name, self.config.region, action, group_id, False, True)
        version = self._policy_version(group_id)
        response = self._vpc().CreateSecurityGroupPolicies(
            self._policy_request("Create", group_id, rule, version)
        )
        return SecurityGroupActionResult(
            self.name, self.config.region, action, group_id, True, False,
            _get(response, "RequestId"),
        )

    def revoke_security_group_rule(self, group_id, rule, *, dry_run=None):
        action = f"revoke_{rule.direction}"
        if ensure_mutation_allowed(self.config, dry_run):
            return SecurityGroupActionResult(self.name, self.config.region, action, group_id, False, True)
        version = self._policy_version(group_id)
        response = self._vpc().DeleteSecurityGroupPolicies(
            self._policy_request("Delete", group_id, rule, version)
        )
        return SecurityGroupActionResult(
            self.name, self.config.region, action, group_id, True, False,
            _get(response, "RequestId"),
        )

    # ---- object storage ----

    def list_buckets(self) -> List[Bucket]:
        response = self._cos().list_buckets()
        entries = ((response.get("Buckets") or {}).get("Bucket")) if isinstance(response, dict) else []
        return [
            Bucket(self.name, item.get("Location"), item.get("Name", ""), item.get("CreationDate"))
            for item in (entries or [])
        ]

    def list_objects(self, bucket: str, *, prefix: Optional[str] = None) -> List[StorageObject]:
        response = self._cos().list_objects(Bucket=bucket, Prefix=prefix or "")
        contents = response.get("Contents") if isinstance(response, dict) else None
        return [
            StorageObject(self.name, bucket, item.get("Key", ""), item.get("Size"),
                          item.get("LastModified"), item.get("ETag"), item.get("StorageClass"))
            for item in (contents or [])
        ]

    # ---- databases ----

    def list_databases(self) -> List[DatabaseInstance]:
        cdb_models = self._import("tencentcloud.cdb.v20170320.models")
        request = cdb_models.DescribeDBInstancesRequest()
        request.Offset = 0
        request.Limit = 100
        response = self._cdb().DescribeDBInstances(request)
        return [self._database(item) for item in (_get(response, "Items") or [])]

    def get_database(self, database_id: str) -> DatabaseInstance:
        cdb_models = self._import("tencentcloud.cdb.v20170320.models")
        request = cdb_models.DescribeDBInstancesRequest()
        request.InstanceIds = [database_id]
        response = self._cdb().DescribeDBInstances(request)
        for item in (_get(response, "Items") or []):
            if _get(item, "InstanceId") == database_id:
                return self._database(item)
        raise CloudError(f"未找到数据库实例: {database_id}")
