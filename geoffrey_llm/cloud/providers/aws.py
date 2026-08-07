"""AWS adapter backed by boto3 for EC2, S3, and RDS."""

from typing import Dict, List, Optional

from ..errors import CloudError
from ..models import Bucket, CloudInstance, DatabaseInstance, SecurityGroup, SecurityGroupActionResult, SecurityGroupRule, StorageObject, Subnet, Vpc
from ..safety import ensure_mutation_allowed, ensure_rule_source_allowed
from .sdk_base import OfficialSdkProvider


class AwsCloudProvider(OfficialSdkProvider):
    name = "aws"
    install_extra = "cloud-aws"

    def __init__(self, config):
        super().__init__(config)
        try:
            import boto3
        except Exception as error:
            raise self._dependency_error("boto3") from error
        session_args = {"region_name": config.region}
        if config.profile:
            session_args["profile_name"] = config.profile
        self._session = boto3.Session(**session_args)
        self._ec2 = self._session.client("ec2")
        self._s3 = self._session.client("s3")
        self._rds = self._session.client("rds")

    @staticmethod
    def _tags(items) -> Dict[str, str]:
        return {item["Key"]: item["Value"] for item in items or []}

    def _instances(self, response):
        values = []
        for reservation in response.get("Reservations", []):
            for item in reservation.get("Instances", []):
                values.append(CloudInstance(self.name, self.config.region, item["InstanceId"], self._tags(item.get("Tags")).get("Name"), item.get("State", {}).get("Name"), item.get("InstanceType"), item.get("VpcId"), item.get("SubnetId"), [ip["PrivateIpAddress"] for ip in item.get("NetworkInterfaces", []) if ip.get("PrivateIpAddress")], [item["PublicIpAddress"]] if item.get("PublicIpAddress") else [], self._tags(item.get("Tags")), item))
        return values

    def list_instances(self, *, vpc_id=None):
        filters = [{"Name": "vpc-id", "Values": [vpc_id]}] if vpc_id else []
        return self._instances(self._ec2.describe_instances(Filters=filters))

    def get_instance(self, instance_id):
        values = self._instances(self._ec2.describe_instances(InstanceIds=[instance_id]))
        if not values:
            raise CloudError(f"未找到实例: {instance_id}")
        return values[0]

    def list_vpcs(self):
        return [Vpc(self.name, self.config.region, item["VpcId"], self._tags(item.get("Tags")).get("Name"), item.get("CidrBlock"), item.get("State"), self._tags(item.get("Tags")), item) for item in self._ec2.describe_vpcs().get("Vpcs", [])]

    def list_subnets(self, *, vpc_id=None):
        filters = [{"Name": "vpc-id", "Values": [vpc_id]}] if vpc_id else []
        return [Subnet(self.name, self.config.region, item["SubnetId"], item["VpcId"], self._tags(item.get("Tags")).get("Name"), item.get("CidrBlock"), item.get("AvailabilityZone"), item.get("AvailableIpAddressCount"), item) for item in self._ec2.describe_subnets(Filters=filters).get("Subnets", [])]

    def _group(self, item):
        return SecurityGroup(self.name, self.config.region, item["GroupId"], item.get("GroupName"), item.get("Description"), item.get("VpcId"), self._tags(item.get("Tags")), item)

    def list_security_groups(self, *, vpc_id=None):
        filters = [{"Name": "vpc-id", "Values": [vpc_id]}] if vpc_id else []
        return [self._group(item) for item in self._ec2.describe_security_groups(Filters=filters).get("SecurityGroups", [])]

    def get_security_group(self, group_id):
        return self._group(self._ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"][0])

    @staticmethod
    def _protocol(value):
        if value in (None, "-1"):
            return "all"
        return value.lower()

    def list_security_group_rules(self, group_id):
        group = self._ec2.describe_security_groups(GroupIds=[group_id])["SecurityGroups"][0]
        values = []
        for direction, key in (("ingress", "IpPermissions"), ("egress", "IpPermissionsEgress")):
            for item in group.get(key, []):
                protocol = self._protocol(item.get("IpProtocol"))
                port_range = None if item.get("FromPort") is None else f"{item['FromPort']}/{item.get('ToPort', item['FromPort'])}"
                for source in item.get("IpRanges", []):
                    values.append(SecurityGroupRule(direction, protocol, port_range, source.get("CidrIp"), description=source.get("Description"), raw=item))
                for source in item.get("Ipv6Ranges", []):
                    values.append(SecurityGroupRule(direction, protocol, port_range, source.get("CidrIpv6"), description=source.get("Description"), raw=item))
                for pair in item.get("UserIdGroupPairs", []):
                    values.append(SecurityGroupRule(direction, protocol, port_range, None, pair.get("GroupId"), pair.get("Description"), raw=item))
        return values

    @staticmethod
    def _permission(rule):
        protocol = rule.protocol or "all"
        result = {"IpProtocol": "-1" if protocol == "all" else protocol}
        if rule.port_range:
            start, end = rule.port_range.split("/", 1)
            result.update({"FromPort": int(start), "ToPort": int(end)})
        if rule.cidr:
            if ":" in rule.cidr:
                result["Ipv6Ranges"] = [{"CidrIpv6": rule.cidr, **({"Description": rule.description} if rule.description else {})}]
            else:
                result["IpRanges"] = [{"CidrIp": rule.cidr, **({"Description": rule.description} if rule.description else {})}]
        elif rule.source_group_id:
            result["UserIdGroupPairs"] = [{"GroupId": rule.source_group_id}]
        return result

    def authorize_security_group_rule(self, group_id, rule, *, dry_run=None, allow_public_cidr=False):
        ensure_rule_source_allowed(rule, allow_public_cidr)
        effective_dry_run = ensure_mutation_allowed(self.config, dry_run)
        if effective_dry_run:
            return SecurityGroupActionResult(self.name, self.config.region, f"authorize_{rule.direction}", group_id, False, True)
        method = self._ec2.authorize_security_group_ingress if rule.direction == "ingress" else self._ec2.authorize_security_group_egress
        response = method(GroupId=group_id, IpPermissions=[self._permission(rule)])
        return SecurityGroupActionResult(self.name, self.config.region, f"authorize_{rule.direction}", group_id, True, False, response.get("ResponseMetadata", {}).get("RequestId"), raw=response)

    def revoke_security_group_rule(self, group_id, rule, *, dry_run=None):
        effective_dry_run = ensure_mutation_allowed(self.config, dry_run)
        if effective_dry_run:
            return SecurityGroupActionResult(self.name, self.config.region, f"revoke_{rule.direction}", group_id, False, True)
        method = self._ec2.revoke_security_group_ingress if rule.direction == "ingress" else self._ec2.revoke_security_group_egress
        response = method(GroupId=group_id, IpPermissions=[self._permission(rule)])
        return SecurityGroupActionResult(self.name, self.config.region, f"revoke_{rule.direction}", group_id, True, False, response.get("ResponseMetadata", {}).get("RequestId"), raw=response)

    def list_buckets(self):
        return [Bucket(self.name, None, item["Name"], str(item.get("CreationDate")), item) for item in self._s3.list_buckets().get("Buckets", [])]

    def list_objects(self, bucket, *, prefix=None):
        response = self._s3.list_objects_v2(Bucket=bucket, **({"Prefix": prefix} if prefix else {}))
        return [StorageObject(self.name, bucket, item["Key"], item.get("Size"), str(item.get("LastModified")), item.get("ETag"), item.get("StorageClass"), item) for item in response.get("Contents", [])]

    def list_databases(self):
        return [self._database(item) for item in self._rds.describe_db_instances().get("DBInstances", [])]

    def get_database(self, database_id):
        return self._database(self._rds.describe_db_instances(DBInstanceIdentifier=database_id)["DBInstances"][0])

    def _database(self, item):
        endpoint = item.get("Endpoint", {})
        return DatabaseInstance(self.name, self.config.region, item["DBInstanceIdentifier"], item.get("DBName"), item.get("Engine"), item.get("EngineVersion"), item.get("DBInstanceStatus"), item.get("DBInstanceClass"), item.get("DBSubnetGroup", {}).get("VpcId"), None, endpoint.get("Address"), endpoint.get("Port"), raw=item)
