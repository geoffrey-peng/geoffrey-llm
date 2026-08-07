"""Huawei Cloud adapter backed by huaweicloud-sdk-python-v3 and esdk-obs-python.

Service clients are created lazily per domain. Credentials come from the
official ``CredentialProviderChain``; no secret material is accepted by
``CloudConfig`` or stored here.

Official references: .cloud/huawei/README.md
"""

from typing import Dict, List, Optional

from ..errors import CloudError
from ..models import (
    Bucket, CloudInstance, DatabaseInstance, SecurityGroup, SecurityGroupActionResult,
    SecurityGroupRule, StorageObject, Subnet, Vpc,
)
from ..safety import ensure_mutation_allowed, ensure_rule_source_allowed
from .sdk_base import OfficialSdkProvider


class HuaweiCloudProvider(OfficialSdkProvider):
    name = "huawei"
    install_extra = "cloud-huawei"

    def __init__(self, config):
        super().__init__(config)
        self._credentials_value = None
        self._ecs_client = None
        self._vpc_client = None
        self._rds_client = None
        self._obs_client = None

    # ---- lazy official SDK clients ----

    def _credentials(self):
        if self._credentials_value is None:
            try:
                from huaweicloudsdkcore.auth.provider import CredentialProviderChain
            except Exception as error:
                raise self._dependency_error("huaweicloudsdkcore") from error
            chain = CredentialProviderChain.get_basic_credential_provider_chain()
            self._credentials_value = chain.get_credentials()
        return self._credentials_value

    def _ecs(self):
        if self._ecs_client is None:
            try:
                from huaweicloudsdkecs.v2 import EcsClient
                from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion
            except Exception as error:
                raise self._dependency_error("huaweicloudsdkecs") from error
            self._ecs_client = (
                EcsClient.new_builder()
                .with_credentials(self._credentials())
                .with_region(EcsRegion.value_of(self.config.region))
                .build()
            )
        return self._ecs_client

    def _vpc(self):
        if self._vpc_client is None:
            try:
                from huaweicloudsdkvpc.v2 import VpcClient
                from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion
            except Exception as error:
                raise self._dependency_error("huaweicloudsdkvpc") from error
            self._vpc_client = (
                VpcClient.new_builder()
                .with_credentials(self._credentials())
                .with_region(VpcRegion.value_of(self.config.region))
                .build()
            )
        return self._vpc_client

    def _rds(self):
        if self._rds_client is None:
            try:
                from huaweicloudsdkrds.v3 import RdsClient
                from huaweicloudsdkrds.v3.region.rds_region import RdsRegion
            except Exception as error:
                raise self._dependency_error("huaweicloudsdkrds") from error
            self._rds_client = (
                RdsClient.new_builder()
                .with_credentials(self._credentials())
                .with_region(RdsRegion.value_of(self.config.region))
                .build()
            )
        return self._rds_client

    def _obs(self):
        if self._obs_client is None:
            try:
                from obs import ObsClient
            except Exception as error:
                raise self._dependency_error("esdk-obs-python") from error
            creds = self._credentials()
            self._obs_client = ObsClient(
                access_key_id=getattr(creds, "ak", None),
                secret_access_key=getattr(creds, "sk", None),
                security_token=getattr(creds, "security_token", None),
                server=f"https://obs.{self.config.region}.myhuaweicloud.com",
            )
        return self._obs_client

    # ---- mapping helpers ----

    @staticmethod
    def _tags(tag_items) -> Dict[str, str]:
        values: Dict[str, str] = {}
        for item in tag_items or []:
            key = getattr(item, "key", None)
            if key is not None:
                values[key] = getattr(item, "value", None) or ""
        return values

    def _instance(self, item) -> CloudInstance:
        metadata = getattr(item, "metadata", None) or {}
        vpc_id = metadata.get("vpc_id") if isinstance(metadata, dict) else getattr(metadata, "vpc_id", None)
        private_ips: List[str] = []
        public_ips: List[str] = []
        addresses = getattr(item, "addresses", None) or {}
        if isinstance(addresses, dict):
            for network_addresses in addresses.values():
                for addr in network_addresses or []:
                    ip = getattr(addr, "addr", None)
                    if not ip:
                        continue
                    if getattr(addr, "os_ext_ips_type", "fixed") == "floating":
                        public_ips.append(ip)
                    else:
                        private_ips.append(ip)
        flavor = getattr(item, "flavor", None)
        status = getattr(item, "status", None)
        return CloudInstance(
            provider=self.name,
            region=self.config.region,
            id=getattr(item, "id", ""),
            name=getattr(item, "name", None),
            status=(status or "").lower() or None,
            instance_type=getattr(flavor, "id", None) if flavor is not None else None,
            vpc_id=vpc_id,
            subnet_id=None,
            private_ips=private_ips,
            public_ips=public_ips,
            tags=self._tags(getattr(item, "tags", None)),
        )

    def _security_group(self, item) -> SecurityGroup:
        return SecurityGroup(
            provider=self.name, region=self.config.region, id=getattr(item, "id", ""),
            name=getattr(item, "name", None), description=getattr(item, "description", None),
            vpc_id=getattr(item, "vpc_id", None),
            tags=self._tags(getattr(item, "tags", None)),
        )

    def _database(self, item) -> DatabaseInstance:
        datastore = getattr(item, "datastore", None)
        nodes = getattr(item, "nodes", None) or []
        private_ip = None
        if nodes:
            ips = getattr(nodes[0], "private_ips", None) or []
            private_ip = ips[0] if ips else None
        return DatabaseInstance(
            provider=self.name,
            region=self.config.region,
            id=getattr(item, "id", ""),
            name=getattr(item, "name", None),
            engine=(getattr(datastore, "type", None) or "").lower() or None,
            engine_version=getattr(datastore, "version", None),
            status=(getattr(item, "status", None) or "").lower() or None,
            instance_class=getattr(item, "flavor_ref", None),
            vpc_id=getattr(item, "vpc_id", None),
            subnet_id=getattr(item, "subnet_id", None),
            endpoint=private_ip,
            port=getattr(item, "port", None),
            tags=self._tags(getattr(item, "tags", None)),
        )

    # ---- compute ----

    def list_instances(self, *, vpc_id: Optional[str] = None) -> List[CloudInstance]:
        ecs_models = self._import("huaweicloudsdkecs.v2")
        request = ecs_models.ListServersDetailsRequest(limit=100, offset=0)
        response = self._ecs().list_servers_details(request)
        values = [self._instance(item) for item in (getattr(response, "servers", None) or [])]
        if vpc_id:
            values = [item for item in values if item.vpc_id == vpc_id]
        return values

    def get_instance(self, instance_id: str) -> CloudInstance:
        ecs_models = self._import("huaweicloudsdkecs.v2")
        response = self._ecs().show_server(ecs_models.ShowServerRequest(server_id=instance_id))
        server = getattr(response, "server", None)
        if server is None:
            raise CloudError(f"未找到实例: {instance_id}")
        return self._instance(server)

    # ---- network ----

    def list_vpcs(self) -> List[Vpc]:
        vpc_models = self._import("huaweicloudsdkvpc.v2")
        response = self._vpc().list_vpcs(vpc_models.ListVpcsRequest(limit=100))
        return [
            Vpc(self.name, self.config.region, getattr(item, "id", ""),
                getattr(item, "name", None), getattr(item, "cidr", None),
                (getattr(item, "status", None) or "").lower() or None,
                self._tags(getattr(item, "tags", None)))
            for item in (getattr(response, "vpcs", None) or [])
        ]

    def list_subnets(self, *, vpc_id: Optional[str] = None) -> List[Subnet]:
        vpc_models = self._import("huaweicloudsdkvpc.v2")
        response = self._vpc().list_subnets(vpc_models.ListSubnetsRequest(limit=100, vpc_id=vpc_id))
        return [
            Subnet(self.name, self.config.region, getattr(item, "id", ""),
                   getattr(item, "vpc_id", ""), getattr(item, "name", None),
                   getattr(item, "cidr", None), getattr(item, "availability_zone", None),
                   getattr(item, "available_ip_address", None))
            for item in (getattr(response, "subnets", None) or [])
        ]

    # ---- security groups ----

    def list_security_groups(self, *, vpc_id: Optional[str] = None) -> List[SecurityGroup]:
        vpc_models = self._import("huaweicloudsdkvpc.v2")
        response = self._vpc().list_security_groups(
            vpc_models.ListSecurityGroupsRequest(limit=100, vpc_id=vpc_id)
        )
        return [self._security_group(item) for item in (getattr(response, "security_groups", None) or [])]

    def get_security_group(self, group_id: str) -> SecurityGroup:
        vpc_models = self._import("huaweicloudsdkvpc.v2")
        response = self._vpc().show_security_group(vpc_models.ShowSecurityGroupRequest(security_group_id=group_id))
        group = getattr(response, "security_group", None)
        if group is None:
            raise CloudError(f"未找到安全组: {group_id}")
        return self._security_group(group)

    def list_security_group_rules(self, group_id: str) -> List[SecurityGroupRule]:
        vpc_models = self._import("huaweicloudsdkvpc.v2")
        request = vpc_models.ListSecurityGroupRulesRequest(security_group_id=group_id, limit=100)
        response = self._vpc().list_security_group_rules(request)
        rules = []
        for item in (getattr(response, "security_group_rules", None) or []):
            multiport = getattr(item, "multiport", None)
            port_range = None
            if multiport and str(multiport) not in ("any", ""):
                multiport = str(multiport)
                port_range = multiport.replace("-", "/") if "-" in multiport else f"{multiport}/{multiport}"
            rules.append(SecurityGroupRule(
                direction=(getattr(item, "direction", "ingress") or "ingress").lower(),
                protocol=(getattr(item, "protocol", None) or "all").lower(),
                port_range=port_range,
                cidr=getattr(item, "remote_ip_prefix", None),
                source_group_id=getattr(item, "remote_group_id", None),
                description=getattr(item, "description", None),
                id=getattr(item, "id", None),
            ))
        return rules

    @staticmethod
    def _multiport(rule: SecurityGroupRule) -> Optional[str]:
        if not rule.port_range:
            return None
        start, end = rule.port_range.split("/", 1)
        return start if start == end else f"{start}-{end}"

    def authorize_security_group_rule(self, group_id, rule, *, dry_run=None, allow_public_cidr=False):
        ensure_rule_source_allowed(rule, allow_public_cidr)
        action = f"authorize_{rule.direction}"
        if ensure_mutation_allowed(self.config, dry_run):
            return SecurityGroupActionResult(self.name, self.config.region, action, group_id, False, True)
        vpc_models = self._import("huaweicloudsdkvpc.v2")
        body = vpc_models.CreateSecurityGroupRuleOption(
            security_group_id=group_id,
            direction=rule.direction,
            ethertype="IPv6" if rule.cidr and ":" in rule.cidr else "IPv4",
            protocol=(rule.protocol or "all").lower(),
            multiport=self._multiport(rule),
            remote_ip_prefix=rule.cidr,
            remote_group_id=rule.source_group_id,
            description=rule.description,
        )
        response = self._vpc().create_security_group_rule(vpc_models.CreateSecurityGroupRuleRequest(body=body))
        created = getattr(response, "security_group_rule", None)
        return SecurityGroupActionResult(
            self.name, self.config.region, action, group_id, True, False,
            getattr(created, "id", None),
        )

    def revoke_security_group_rule(self, group_id, rule, *, dry_run=None):
        action = f"revoke_{rule.direction}"
        if ensure_mutation_allowed(self.config, dry_run):
            return SecurityGroupActionResult(self.name, self.config.region, action, group_id, False, True)
        if not rule.id:
            raise CloudError("华为云删除安全组规则需要规则 ID（rule.id）")
        vpc_models = self._import("huaweicloudsdkvpc.v2")
        self._vpc().delete_security_group_rule(
            vpc_models.DeleteSecurityGroupRuleRequest(security_group_id=group_id, security_group_rule_id=rule.id)
        )
        return SecurityGroupActionResult(self.name, self.config.region, action, group_id, True, False)

    # ---- object storage ----

    def list_buckets(self) -> List[Bucket]:
        response = self._obs().listBuckets(isQueryLocation=True)
        entries = getattr(response, "body", None) or []
        return [
            Bucket(self.name, getattr(item, "location", None), getattr(item, "name", ""),
                   str(getattr(item, "create_date", "")) or None)
            for item in entries
        ]

    def list_objects(self, bucket: str, *, prefix: Optional[str] = None) -> List[StorageObject]:
        response = self._obs().listObjects(bucket, prefix=prefix)
        body = getattr(response, "body", None)
        entries = getattr(body, "contents", None) or []
        return [
            StorageObject(self.name, bucket, getattr(item, "key", ""),
                          getattr(item, "size", None),
                          str(getattr(item, "lastModified", "")) if getattr(item, "lastModified", None) else None,
                          getattr(item, "etag", None), getattr(item, "storageClass", None))
            for item in entries
        ]

    # ---- databases ----

    def list_databases(self) -> List[DatabaseInstance]:
        rds_models = self._import("huaweicloudsdkrds.v3")
        response = self._rds().list_instances(rds_models.ListInstancesRequest(offset=0, limit=100))
        return [self._database(item) for item in (getattr(response, "instances", None) or [])]

    def get_database(self, database_id: str) -> DatabaseInstance:
        rds_models = self._import("huaweicloudsdkrds.v3")
        response = self._rds().list_instances(rds_models.ListInstancesRequest(id=database_id, offset=0, limit=100))
        for item in (getattr(response, "instances", None) or []):
            if getattr(item, "id", None) == database_id:
                return self._database(item)
        raise CloudError(f"未找到数据库实例: {database_id}")
