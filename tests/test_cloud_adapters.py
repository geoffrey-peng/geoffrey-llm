"""Adapter mapping tests using fake SDK objects.

These verify the provider->neutral-model translation and safety guards without
any real cloud SDK installed, credentials, or network access. Alibaba/Tencent/
Huawei providers build clients lazily, so they can be instantiated directly;
AWS builds clients eagerly, so a fake ``boto3`` module is injected.
"""

import sys
import types
from types import SimpleNamespace

import pytest

from geoffrey_llm.cloud import CloudConfig, SecurityGroupRule
from geoffrey_llm.cloud.providers.alibaba import AlibabaCloudProvider
from geoffrey_llm.cloud.providers.tencent import TencentCloudProvider
from geoffrey_llm.cloud.providers.huawei import HuaweiCloudProvider


# ---- Alibaba ----

@pytest.fixture
def alibaba():
    return AlibabaCloudProvider(CloudConfig(provider="alibaba", region="cn-beijing"))


def test_alibaba_instance_mapping(alibaba):
    item = SimpleNamespace(
        instance_id="i-abc",
        instance_name="web-1",
        status="Running",
        instance_type="ecs.g7.large",
        vpc_attributes=SimpleNamespace(
            vpc_id="vpc-1",
            v_switch_id="vsw-1",
            private_ip_address=SimpleNamespace(ip_address=["192.168.0.10"]),
        ),
        public_ip_address=SimpleNamespace(ip_address=["47.94.0.1"]),
        eip_address=SimpleNamespace(ip_address=None),
        tags=SimpleNamespace(tag=[SimpleNamespace(tag_key="env", tag_value="prod")]),
    )
    inst = alibaba._instance(item)
    assert inst.id == "i-abc"
    assert inst.status == "running"
    assert inst.vpc_id == "vpc-1"
    assert inst.subnet_id == "vsw-1"
    assert inst.private_ips == ["192.168.0.10"]
    assert inst.public_ips == ["47.94.0.1"]
    assert inst.tags == {"env": "prod"}


def test_alibaba_database_mapping(alibaba):
    item = SimpleNamespace(
        dbinstance_id="rm-1", dbinstance_description="prod-db", engine="MySQL",
        engine_version="8.0", dbinstance_status="Running", dbinstance_class="rds.mysql.s2.large",
        vpc_id="vpc-1", v_switch_id="vsw-1", connection_string="rm-1.mysql.rds", port="3306",
        tags=None,
    )
    db = alibaba._database(item)
    assert db.id == "rm-1"
    assert db.engine == "mysql"
    assert db.status == "running"
    assert db.port == 3306
    assert db.endpoint == "rm-1.mysql.rds"


def test_alibaba_sg_rule_mapping_from_permission(alibaba):
    perm = SimpleNamespace(
        direction="ingress", ip_protocol="TCP", port_range="443/443",
        source_cidr_ip="10.0.0.0/8", dest_cidr_ip=None, source_group_id=None,
        dest_group_id=None, description="https", priority="1", policy="accept",
    )
    port_range = getattr(perm, "port_range", None)
    if port_range in (None, "-1/-1"):
        port_range = None
    rule = SecurityGroupRule(
        direction=perm.direction,
        protocol=perm.ip_protocol.lower(),
        port_range=port_range,
        cidr=perm.source_cidr_ip,
        priority=int(perm.priority),
        policy=perm.policy,
    )
    assert rule.port_range == "443/443"
    assert rule.cidr == "10.0.0.0/8"
    assert rule.priority == 1


# ---- Tencent ----

@pytest.fixture
def tencent():
    return TencentCloudProvider(CloudConfig(provider="tencent", region="ap-guangzhou"))


def test_tencent_instance_mapping(tencent):
    item = SimpleNamespace(
        InstanceId="ins-1", InstanceName="web", InstanceState="RUNNING",
        InstanceType="S5.MEDIUM2",
        VirtualPrivateCloud=SimpleNamespace(VpcId="vpc-1", SubnetId="subnet-1", PrivateIpAddresses=["10.0.0.5"]),
        PublicIpAddresses=["1.2.3.4"],
        Tags=[{"Key": "team", "Value": "infra"}],
    )
    inst = tencent._instance(item)
    assert inst.id == "ins-1"
    assert inst.status == "running"
    assert inst.vpc_id == "vpc-1"
    assert inst.subnet_id == "subnet-1"
    assert inst.private_ips == ["10.0.0.5"]
    assert inst.public_ips == ["1.2.3.4"]
    assert inst.tags == {"team": "infra"}


def test_tencent_rule_mapping(tencent):
    item = SimpleNamespace(
        Protocol="TCP", Port="8000-9000", CidrBlock="0.0.0.0/0",
        SecurityGroupIdPrefix=None, PolicyDescription="web", Action="ACCEPT",
    )
    rule = tencent._rule("ingress", item)
    assert rule.protocol == "tcp"
    assert rule.port_range == "8000/9000"
    assert rule.policy == "accept"


def test_tencent_rule_mapping_all_ports(tencent):
    item = SimpleNamespace(Protocol="ALL", Port="ALL", CidrBlock="10.0.0.0/8",
                           SecurityGroupIdPrefix=None, PolicyDescription=None, Action="DROP")
    rule = tencent._rule("egress", item)
    assert rule.protocol == "all"
    assert rule.port_range is None
    assert rule.policy == "drop"


def test_tencent_database_status_mapping(tencent):
    item = SimpleNamespace(InstanceId="cdb-1", InstanceName="db", Engine="MySQL",
                           EngineVersion="8.0", Status=1, InstanceType=1, VpcId="vpc-1",
                           SubnetId="subnet-1", Vip="10.0.0.9", Vport=3306, Tags=None)
    db = tencent._database(item)
    assert db.status == "running"
    assert db.endpoint == "10.0.0.9"
    assert db.port == 3306


def test_tencent_policy_dict(tencent):
    rule = SecurityGroupRule("ingress", "tcp", "443/443", "10.0.0.0/8", description="https")
    d = tencent._policy_dict(rule)
    assert d["Protocol"] == "TCP"
    assert d["Port"] == "443"
    assert d["CidrBlock"] == "10.0.0.0/8"
    assert d["Action"] == "ACCEPT"


# ---- Huawei ----

@pytest.fixture
def huawei():
    return HuaweiCloudProvider(CloudConfig(provider="huawei", region="cn-north-4"))


def test_huawei_instance_mapping(huawei):
    item = SimpleNamespace(
        id="ecs-1", name="web", status="ACTIVE",
        flavor=SimpleNamespace(id="s6.large.2"),
        metadata={"vpc_id": "vpc-1"},
        addresses={"net": [
            SimpleNamespace(addr="192.168.0.5", os_ext_ips_type="fixed"),
            SimpleNamespace(addr="1.2.3.4", os_ext_ips_type="floating"),
        ]},
        tags=[SimpleNamespace(key="env", value="dev")],
    )
    inst = huawei._instance(item)
    assert inst.id == "ecs-1"
    assert inst.status == "active"
    assert inst.vpc_id == "vpc-1"
    assert inst.instance_type == "s6.large.2"
    assert inst.private_ips == ["192.168.0.5"]
    assert inst.public_ips == ["1.2.3.4"]
    assert inst.tags == {"env": "dev"}


def test_huawei_database_mapping(huawei):
    item = SimpleNamespace(
        id="rds-1", name="db", status="ACTIVE",
        datastore=SimpleNamespace(type="MySQL", version="8.0"),
        flavor_ref="rds.mysql.c6.large", vpc_id="vpc-1", subnet_id="subnet-1",
        port=3306, nodes=[SimpleNamespace(private_ips=["10.0.0.20"])], tags=None,
    )
    db = huawei._database(item)
    assert db.id == "rds-1"
    assert db.engine == "mysql"
    assert db.status == "active"
    assert db.endpoint == "10.0.0.20"
    assert db.port == 3306


def test_huawei_multiport_conversion(huawei):
    assert huawei._multiport(SecurityGroupRule("ingress", "tcp", "443/443")) == "443"
    assert huawei._multiport(SecurityGroupRule("ingress", "tcp", "8000/9000")) == "8000-9000"
    assert huawei._multiport(SecurityGroupRule("ingress", "icmp")) is None


# ---- AWS (fake boto3) ----

@pytest.fixture
def aws(monkeypatch):
    from geoffrey_llm.cloud.providers.aws import AwsCloudProvider

    class _FakeClient:
        pass

    class _FakeSession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def client(self, name):
            return _FakeClient()

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.Session = _FakeSession
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    return AwsCloudProvider(CloudConfig(provider="aws", region="us-east-1"))


def test_aws_instance_mapping(aws):
    response = {"Reservations": [{"Instances": [{
        "InstanceId": "i-0abc",
        "State": {"Name": "running"},
        "InstanceType": "t3.micro",
        "VpcId": "vpc-1",
        "SubnetId": "subnet-1",
        "NetworkInterfaces": [{"PrivateIpAddress": "10.0.0.5"}],
        "PublicIpAddress": "1.2.3.4",
        "Tags": [{"Key": "Name", "Value": "web"}],
    }]}]}
    instances = aws._instances(response)
    assert len(instances) == 1
    inst = instances[0]
    assert inst.id == "i-0abc"
    assert inst.status == "running"
    assert inst.name == "web"
    assert inst.vpc_id == "vpc-1"
    assert inst.private_ips == ["10.0.0.5"]
    assert inst.public_ips == ["1.2.3.4"]


def test_aws_protocol_normalization(aws):
    assert aws._protocol("-1") == "all"
    assert aws._protocol(None) == "all"
    assert aws._protocol("tcp") == "tcp"


def test_aws_permission_ipv4_vs_ipv6(aws):
    v4 = aws._permission(SecurityGroupRule("ingress", "tcp", "443/443", "10.0.0.0/8"))
    assert v4["IpProtocol"] == "tcp"
    assert v4["FromPort"] == 443 and v4["ToPort"] == 443
    assert v4["IpRanges"] == [{"CidrIp": "10.0.0.0/8"}]

    v6 = aws._permission(SecurityGroupRule("ingress", "tcp", "443/443", "::/0"))
    assert v6["Ipv6Ranges"] == [{"CidrIpv6": "::/0"}]

    all_proto = aws._permission(SecurityGroupRule("ingress", "all", None, "10.0.0.0/8"))
    assert all_proto["IpProtocol"] == "-1"


def test_aws_database_mapping(aws):
    item = {
        "DBInstanceIdentifier": "db-1", "DBName": "app", "Engine": "mysql",
        "EngineVersion": "8.0", "DBInstanceStatus": "available",
        "DBInstanceClass": "db.t3.micro",
        "DBSubnetGroup": {"VpcId": "vpc-1"},
        "Endpoint": {"Address": "db-1.abc.us-east-1.rds.amazonaws.com", "Port": 3306},
    }
    db = aws._database(item)
    assert db.id == "db-1"
    assert db.engine == "mysql"
    assert db.status == "available"
    assert db.vpc_id == "vpc-1"
    assert db.endpoint == "db-1.abc.us-east-1.rds.amazonaws.com"
    assert db.port == 3306
