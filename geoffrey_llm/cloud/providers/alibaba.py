"""Alibaba Cloud adapter backed by the official Tea SDKs and oss2.

Service clients are created lazily per domain so a partial vendor SDK install
still works for the installed services. Credentials always come from the
official ``alibabacloud_credentials`` default provider chain; no secret
material is accepted by ``CloudConfig`` or stored here.

Official references: .cloud/alibaba/README.md
"""

from typing import Dict, List, Optional

from ..errors import CloudError
from ..models import (
    Bucket, CloudInstance, DatabaseInstance, SecurityGroup, SecurityGroupActionResult,
    SecurityGroupRule, StorageObject, Subnet, Vpc,
)
from ..safety import ensure_mutation_allowed, ensure_rule_source_allowed
from .sdk_base import OfficialSdkProvider

_INSTANCE_STATUS = {
    "Running": "running",
    "Stopped": "stopped",
    "Starting": "starting",
    "Stopping": "stopping",
    "Pending": "pending",
}


class AlibabaCloudProvider(OfficialSdkProvider):
    name = "alibaba"
    install_extra = "cloud-alibaba"

    def __init__(self, config):
        super().__init__(config)
        self._credential_client = None
        self._ecs_client = None
        self._vpc_client = None
        self._rds_client = None
        self._oss_service = None

    # ---- lazy official SDK clients ----

    def _credential(self):
        if self._credential_client is None:
            try:
                from alibabacloud_credentials.client import Client as CredentialClient
            except Exception as error:
                raise self._dependency_error("alibabacloud-credentials") from error
            self._credential_client = CredentialClient()
        return self._credential_client

    def _openapi_config(self, endpoint: str):
        try:
            from alibabacloud_tea_openapi import models as open_api_models
        except Exception as error:
            raise self._dependency_error("alibabacloud-tea-openapi") from error
        return open_api_models.Config(
            credential=self._credential(),
            region_id=self.config.region,
            endpoint=endpoint,
        )

    def _ecs(self):
        if self._ecs_client is None:
            try:
                from alibabacloud_ecs20140526.client import Client as EcsClient
            except Exception as error:
                raise self._dependency_error("alibabacloud-ecs20140526") from error
            self._ecs_client = EcsClient(
                self._openapi_config(f"ecs.{self.config.region}.aliyuncs.com")
            )
        return self._ecs_client

    def _vpc(self):
        if self._vpc_client is None:
            try:
                from alibabacloud_vpc20160428.client import Client as VpcClient
            except Exception as error:
                raise self._dependency_error("alibabacloud-vpc20160428") from error
            self._vpc_client = VpcClient(
                self._openapi_config(f"vpc.{self.config.region}.aliyuncs.com")
            )
        return self._vpc_client

    def _rds(self):
        if self._rds_client is None:
            try:
                from alibabacloud_rds20140815.client import Client as RdsClient
            except Exception as error:
                raise self._dependency_error("alibabacloud-rds20140815") from error
            self._rds_client = RdsClient(
                self._openapi_config(f"rds.{self.config.region}.aliyuncs.com")
            )
        return self._rds_client

    def _oss(self):
        if self._oss_service is None:
            try:
                import oss2
            except Exception as error:
                raise self._dependency_error("oss2") from error

            class _CredentialBridge(oss2.CredentialsProvider):
                def __init__(self, credential_client):
                    self._credential_client = credential_client

                def get_credentials(self):
                    cred = self._credential_client.get_credential()
                    return oss2.Credentials(
                        access_key_id=cred.get_access_key_id(),
                        access_key_secret=cred.get_access_key_secret(),
                        security_token=cred.get_security_token(),
                    )

            auth = oss2.ProviderAuth(_CredentialBridge(self._credential()))
            self._oss_service = oss2.Service(
                auth, f"https://oss-{self.config.region}.aliyuncs.com"
            )
        return self._oss_service

    # ---- mapping helpers ----

    @staticmethod
    def _tags(tag_items) -> Dict[str, str]:
        values: Dict[str, str] = {}
        for item in tag_items or []:
            key = getattr(item, "tag_key", None)
            if key is not None:
                values[key] = getattr(item, "tag_value", None) or ""
        return values

    def _instance(self, item) -> CloudInstance:
        vpc_attrs = getattr(item, "vpc_attributes", None)
        private_ips: List[str] = []
        vswitch_id = None
        vpc_id = None
        if vpc_attrs is not None:
            vpc_id = getattr(vpc_attrs, "vpc_id", None)
            vswitch_id = getattr(vpc_attrs, "v_switch_id", None)
            addresses = getattr(vpc_attrs, "private_ip_address", None)
            private_ips = list(getattr(addresses, "ip_address", None) or []) if addresses else []
        public_ips: List[str] = []
        public_block = getattr(item, "public_ip_address", None)
        if public_block is not None:
            public_ips.extend(getattr(public_block, "ip_address", None) or [])
        eip = getattr(getattr(item, "eip_address", None), "ip_address", None)
        if eip:
            public_ips.append(eip)
        status = getattr(item, "status", None)
        return CloudInstance(
            provider=self.name,
            region=self.config.region,
            id=getattr(item, "instance_id", ""),
            name=getattr(item, "instance_name", None),
            status=_INSTANCE_STATUS.get(status, (status or "").lower() or None),
            instance_type=getattr(item, "instance_type", None),
            vpc_id=vpc_id,
            subnet_id=vswitch_id,
            private_ips=private_ips,
            public_ips=public_ips,
            tags=self._tags(getattr(item, "tags", None) and item.tags.tag),
        )

    def _database(self, item) -> DatabaseInstance:
        port = getattr(item, "port", None)
        return DatabaseInstance(
            provider=self.name,
            region=self.config.region,
            id=getattr(item, "dbinstance_id", ""),
            name=getattr(item, "dbinstance_description", None),
            engine=(getattr(item, "engine", None) or "").lower() or None,
            engine_version=getattr(item, "engine_version", None),
            status=(getattr(item, "dbinstance_status", None) or "").lower() or None,
            instance_class=getattr(item, "dbinstance_class", None),
            vpc_id=getattr(item, "vpc_id", None),
            subnet_id=getattr(item, "v_switch_id", None),
            endpoint=getattr(item, "connection_string", None),
            port=int(port) if port not in (None, "") else None,
            tags=self._tags(getattr(item, "tags", None) and item.tags.tag),
        )

    # ---- compute ----

    def list_instances(self, *, vpc_id: Optional[str] = None) -> List[CloudInstance]:
        ecs_models = self._import("alibabacloud_ecs20140526.models")
        request = ecs_models.DescribeInstancesRequest(
            region_id=self.config.region, vpc_id=vpc_id, page_size=100, page_number=1
        )
        response = self._ecs().describe_instances(request)
        instances = (getattr(response.body, "instances", None) and response.body.instances.instance) or []
        return [self._instance(item) for item in instances]

    def get_instance(self, instance_id: str) -> CloudInstance:
        ecs_models = self._import("alibabacloud_ecs20140526.models")
        request = ecs_models.DescribeInstancesRequest(
            region_id=self.config.region, instance_ids=f'["{instance_id}"]'
        )
        response = self._ecs().describe_instances(request)
        instances = (getattr(response.body, "instances", None) and response.body.instances.instance) or []
        if not instances:
            raise CloudError(f"未找到实例: {instance_id}")
        return self._instance(instances[0])

    # ---- network ----

    def list_vpcs(self) -> List[Vpc]:
        vpc_models = self._import("alibabacloud_vpc20160428.models")
        request = vpc_models.DescribeVpcsRequest(
            region_id=self.config.region, page_size=50, page_number=1
        )
        response = self._vpc().describe_vpcs(request)
        items = (getattr(response.body, "vpcs", None) and response.body.vpcs.vpc) or []
        return [
            Vpc(
                provider=self.name, region=self.config.region, id=item.vpc_id,
                name=getattr(item, "vpc_name", None), cidr=getattr(item, "cidr_block", None),
                status=(getattr(item, "status", None) or "").lower() or None,
                tags=self._tags(getattr(item, "tags", None) and item.tags.tag),
            )
            for item in items
        ]

    def list_subnets(self, *, vpc_id: Optional[str] = None) -> List[Subnet]:
        vpc_models = self._import("alibabacloud_vpc20160428.models")
        request = vpc_models.DescribeVSwitchesRequest(
            region_id=self.config.region, vpc_id=vpc_id, page_size=50, page_number=1
        )
        response = self._vpc().describe_vswitches(request)
        items = (getattr(response.body, "v_switches", None) and response.body.v_switches.v_switch) or []
        return [
            Subnet(
                provider=self.name, region=self.config.region, id=item.v_switch_id,
                vpc_id=getattr(item, "vpc_id", ""), name=getattr(item, "v_switch_name", None),
                cidr=getattr(item, "cidr_block", None), zone=getattr(item, "zone_id", None),
                available_ip_count=getattr(item, "available_ip_address_count", None),
            )
            for item in items
        ]

    # ---- security groups ----

    def _security_group(self, item) -> SecurityGroup:
        return SecurityGroup(
            provider=self.name, region=self.config.region, id=item.security_group_id,
            name=getattr(item, "security_group_name", None),
            description=getattr(item, "description", None),
            vpc_id=getattr(item, "vpc_id", None),
            tags=self._tags(getattr(item, "tags", None) and item.tags.tag),
        )

    def list_security_groups(self, *, vpc_id: Optional[str] = None) -> List[SecurityGroup]:
        ecs_models = self._import("alibabacloud_ecs20140526.models")
        request = ecs_models.DescribeSecurityGroupsRequest(
            region_id=self.config.region, vpc_id=vpc_id, page_size=50, page_number=1
        )
        response = self._ecs().describe_security_groups(request)
        items = (getattr(response.body, "security_groups", None) and response.body.security_groups.security_group) or []
        return [self._security_group(item) for item in items]

    def get_security_group(self, group_id: str) -> SecurityGroup:
        ecs_models = self._import("alibabacloud_ecs20140526.models")
        request = ecs_models.DescribeSecurityGroupsRequest(
            region_id=self.config.region, security_group_ids=f'["{group_id}"]'
        )
        response = self._ecs().describe_security_groups(request)
        items = (getattr(response.body, "security_groups", None) and response.body.security_groups.security_group) or []
        if not items:
            raise CloudError(f"未找到安全组: {group_id}")
        return self._security_group(items[0])

    def list_security_group_rules(self, group_id: str) -> List[SecurityGroupRule]:
        ecs_models = self._import("alibabacloud_ecs20140526.models")
        request = ecs_models.DescribeSecurityGroupAttributeRequest(
            region_id=self.config.region, security_group_id=group_id
        )
        response = self._ecs().describe_security_group_attribute(request)
        permissions = (getattr(response.body, "permissions", None) and response.body.permissions.permission) or []
        rules = []
        for item in permissions:
            port_range = getattr(item, "port_range", None)
            if port_range in (None, "-1/-1"):
                port_range = None
            priority = getattr(item, "priority", None)
            rules.append(SecurityGroupRule(
                direction=(getattr(item, "direction", "ingress") or "ingress").lower(),
                protocol=(getattr(item, "ip_protocol", None) or "all").lower(),
                port_range=port_range,
                cidr=getattr(item, "source_cidr_ip", None) or getattr(item, "dest_cidr_ip", None),
                source_group_id=getattr(item, "source_group_id", None) or getattr(item, "dest_group_id", None),
                description=getattr(item, "description", None),
                priority=int(priority) if priority not in (None, "") else None,
                policy=(getattr(item, "policy", "accept") or "accept").lower(),
            ))
        return rules

    def _sg_change_request(self, verb: str, group_id: str, rule: SecurityGroupRule):
        ecs_models = self._import("alibabacloud_ecs20140526.models")
        classes = {
            ("authorize", "ingress"): ecs_models.AuthorizeSecurityGroupRequest,
            ("authorize", "egress"): ecs_models.AuthorizeSecurityGroupEgressRequest,
            ("revoke", "ingress"): ecs_models.RevokeSecurityGroupRequest,
            ("revoke", "egress"): ecs_models.RevokeSecurityGroupEgressRequest,
        }
        kwargs = {
            "security_group_id": group_id,
            "region_id": self.config.region,
            "ip_protocol": (rule.protocol or "all").upper(),
            "port_range": rule.port_range or "-1/-1",
            "description": rule.description,
            "policy": "accept" if rule.policy == "accept" else "drop",
        }
        if rule.priority is not None:
            kwargs["priority"] = rule.priority
        if rule.direction == "ingress":
            if rule.cidr:
                kwargs["source_cidr_ip"] = rule.cidr
            if rule.source_group_id:
                kwargs["source_group_id"] = rule.source_group_id
        else:
            if rule.cidr:
                kwargs["dest_cidr_ip"] = rule.cidr
            if rule.source_group_id:
                kwargs["dest_group_id"] = rule.source_group_id
        return classes[(verb, rule.direction)](**kwargs)

    def authorize_security_group_rule(self, group_id, rule, *, dry_run=None, allow_public_cidr=False):
        ensure_rule_source_allowed(rule, allow_public_cidr)
        action = f"authorize_{rule.direction}"
        if ensure_mutation_allowed(self.config, dry_run):
            return SecurityGroupActionResult(self.name, self.config.region, action, group_id, False, True)
        request = self._sg_change_request("authorize", group_id, rule)
        call = self._ecs().authorize_security_group if rule.direction == "ingress" else self._ecs().authorize_security_group_egress
        response = call(request)
        return SecurityGroupActionResult(
            self.name, self.config.region, action, group_id, True, False,
            getattr(response.body, "request_id", None),
        )

    def revoke_security_group_rule(self, group_id, rule, *, dry_run=None):
        action = f"revoke_{rule.direction}"
        if ensure_mutation_allowed(self.config, dry_run):
            return SecurityGroupActionResult(self.name, self.config.region, action, group_id, False, True)
        request = self._sg_change_request("revoke", group_id, rule)
        call = self._ecs().revoke_security_group if rule.direction == "ingress" else self._ecs().revoke_security_group_egress
        response = call(request)
        return SecurityGroupActionResult(
            self.name, self.config.region, action, group_id, True, False,
            getattr(response.body, "request_id", None),
        )

    # ---- object storage ----

    def list_buckets(self) -> List[Bucket]:
        result = self._oss().list_buckets()
        return [
            Bucket(self.name, getattr(item, "location", None), item.name,
                   str(getattr(item, "creation_date", "")) or None)
            for item in (getattr(result, "buckets", None) or [])
        ]

    def list_objects(self, bucket: str, *, prefix: Optional[str] = None) -> List[StorageObject]:
        oss2 = self._import("oss2")
        service = self._oss()
        handle = oss2.Bucket(service.auth, service.endpoint, bucket)
        result = handle.list_objects(prefix=prefix or "")
        return [
            StorageObject(self.name, bucket, item.key, getattr(item, "size", None),
                          str(item.last_modified) if getattr(item, "last_modified", None) else None,
                          getattr(item, "etag", None), getattr(item, "storage_class", None))
            for item in (getattr(result, "object_list", None) or [])
        ]

    # ---- databases ----

    def list_databases(self) -> List[DatabaseInstance]:
        rds_models = self._import("alibabacloud_rds20140815.models")
        request = rds_models.DescribeDBInstancesRequest(
            region_id=self.config.region, page_size=100, page_number=1
        )
        response = self._rds().describe_dbinstances(request)
        items = (getattr(response.body, "items", None) and response.body.items.dbinstance) or []
        return [self._database(item) for item in items]

    def get_database(self, database_id: str) -> DatabaseInstance:
        rds_models = self._import("alibabacloud_rds20140815.models")
        request = rds_models.DescribeDBInstancesRequest(
            region_id=self.config.region, dbinstance_id=database_id
        )
        response = self._rds().describe_dbinstances(request)
        items = (getattr(response.body, "items", None) and response.body.items.dbinstance) or []
        for item in items:
            if getattr(item, "dbinstance_id", None) == database_id:
                return self._database(item)
        raise CloudError(f"未找到数据库实例: {database_id}")
