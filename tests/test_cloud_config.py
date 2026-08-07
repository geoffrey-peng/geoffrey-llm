import pytest

from geoffrey_llm.cloud import CloudConfig
from geoffrey_llm.cloud.credentials import credential_source


def test_config_never_contains_credentials():
    config = CloudConfig(provider="aws", region="us-east-1")
    data = config.to_dict()
    assert "access_key" not in data
    assert "secret_key" not in data
    assert "token" not in data


def test_invalid_mutation_configuration_rejected():
    with pytest.raises(ValueError):
        CloudConfig(provider="mock", region="test-1", allow_mutation=True).validate()


def test_credential_source_environment_is_non_sensitive(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    assert credential_source("aws") == "environment"


def test_explicit_profile_precedes_environment(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    assert credential_source("aws", "work") == "profile:work"
