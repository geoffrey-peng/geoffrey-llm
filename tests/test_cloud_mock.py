import pytest

from geoffrey_llm.cloud import CloudClient, CloudConfig, CloudSafetyError, SecurityGroupRule


def client(**kwargs):
    return CloudClient(CloudConfig(provider="mock", region="test-1", **kwargs))


def test_mock_unified_resource_domains():
    cloud = client()
    assert cloud.instances.get("i-demo").id == "i-demo"
    assert cloud.network.list_vpcs()[0].id == "vpc-demo"
    assert cloud.network.list_subnets(vpc_id="vpc-demo")[0].id == "subnet-demo"
    assert cloud.security_groups.get("sg-demo").id == "sg-demo"
    assert cloud.object_storage.list_buckets()[0].name == "demo-bucket"
    assert cloud.object_storage.list_objects("demo-bucket")[0].key == "example.txt"
    assert cloud.databases.get("db-demo").id == "db-demo"


def test_mutation_is_dry_run_by_default():
    cloud = client(read_only=False, allow_mutation=True)
    rule = SecurityGroupRule("ingress", "tcp", "443/443", "10.0.0.0/8")
    result = cloud.security_groups.authorize("sg-demo", rule)
    assert result.dry_run is True
    assert result.changed is False
    assert cloud.security_groups.list_rules("sg-demo") == []


def test_real_mutation_requires_explicit_opt_in():
    cloud = client()
    rule = SecurityGroupRule("ingress", "tcp", "443/443", "10.0.0.0/8")
    with pytest.raises(CloudSafetyError):
        cloud.security_groups.authorize("sg-demo", rule, dry_run=False)


def test_real_mutation_and_revoke():
    cloud = client(read_only=False, allow_mutation=True)
    rule = SecurityGroupRule("ingress", "tcp", "443/443", "10.0.0.0/8")
    created = cloud.security_groups.authorize("sg-demo", rule, dry_run=False)
    assert created.changed and not created.dry_run
    assert cloud.security_groups.list_rules("sg-demo") == [rule]
    deleted = cloud.security_groups.revoke("sg-demo", rule, dry_run=False)
    assert deleted.changed and not deleted.dry_run
    assert cloud.security_groups.list_rules("sg-demo") == []


def test_public_cidr_needs_explicit_override_even_for_dry_run():
    cloud = client()
    rule = SecurityGroupRule("ingress", "tcp", "22/22", "0.0.0.0/0")
    with pytest.raises(CloudSafetyError):
        cloud.security_groups.authorize("sg-demo", rule)
    result = cloud.security_groups.authorize("sg-demo", rule, allow_public_cidr=True)
    assert result.dry_run is True
