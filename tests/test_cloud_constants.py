"""Tests for dot-accessible Provider/Region constants."""

from geoffrey_llm.cloud import (
    CloudClient, CloudConfig, Provider, Region, get_provider_registry,
)


def test_provider_values_match_registry():
    registry = get_provider_registry()
    for name in Provider.ALL:
        assert name in registry


def test_provider_values_are_lowercase_strings():
    assert Provider.ALIBABA == "alibaba"
    assert Provider.TENCENT == "tencent"
    assert Provider.HUAWEI == "huawei"
    assert Provider.AWS == "aws"
    assert Provider.MOCK == "mock"


def test_region_spot_values():
    assert Region.ALIBABA.CN_BEIJING == "cn-beijing"
    assert Region.ALIBABA.CN_HANGZHOU == "cn-hangzhou"
    assert Region.TENCENT.AP_GUANGZHOU == "ap-guangzhou"
    assert Region.TENCENT.NA_SILICONVALLEY == "na-siliconvalley"
    assert Region.HUAWEI.CN_NORTH_4 == "cn-north-4"
    assert Region.AWS.US_EAST_1 == "us-east-1"
    assert Region.AWS.AP_SOUTHEAST_1 == "ap-southeast-1"


def test_all_region_values_are_nonempty_strings():
    for provider_name, namespace in (
        ("alibaba", Region.ALIBABA),
        ("tencent", Region.TENCENT),
        ("huawei", Region.HUAWEI),
        ("aws", Region.AWS),
    ):
        values = [value for key, value in vars(namespace).items() if not key.startswith("_")]
        assert values, f"{provider_name} 地域常量不能为空"
        for value in values:
            assert isinstance(value, str) and value.strip(), value


def test_client_accepts_constants():
    client = CloudClient(CloudConfig(provider=Provider.MOCK, region=Region.ALIBABA.CN_BEIJING))
    assert client.provider.name == "mock"
    assert client.config.region == "cn-beijing"
    assert [inst.id for inst in client.instances.list()] == ["i-demo"]


def test_constants_interchangeable_with_strings():
    by_constant = CloudConfig(provider=Provider.MOCK, region=Region.ALIBABA.CN_BEIJING)
    by_string = CloudConfig(provider="mock", region="cn-beijing")
    assert by_constant.provider == by_string.provider
    assert by_constant.region == by_string.region
