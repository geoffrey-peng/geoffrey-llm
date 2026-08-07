"""Provider-neutral cloud resource models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class CloudInstance:
    provider: str
    region: str
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    instance_type: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    private_ips: List[str] = field(default_factory=list)
    public_ips: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None


@dataclass
class Vpc:
    provider: str
    region: str
    id: str
    name: Optional[str] = None
    cidr: Optional[str] = None
    status: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None


@dataclass
class Subnet:
    provider: str
    region: str
    id: str
    vpc_id: str
    name: Optional[str] = None
    cidr: Optional[str] = None
    zone: Optional[str] = None
    available_ip_count: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class SecurityGroup:
    provider: str
    region: str
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    vpc_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None


@dataclass
class SecurityGroupRule:
    direction: Literal["ingress", "egress"]
    protocol: str
    port_range: Optional[str] = None
    cidr: Optional[str] = None
    source_group_id: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    policy: str = "accept"
    id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class SecurityGroupActionResult:
    provider: str
    region: str
    action: str
    group_id: str
    changed: bool
    dry_run: bool
    request_id: Optional[str] = None
    message: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class Bucket:
    provider: str
    region: Optional[str]
    name: str
    creation_date: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class StorageObject:
    provider: str
    bucket: str
    key: str
    size: Optional[int] = None
    last_modified: Optional[str] = None
    etag: Optional[str] = None
    storage_class: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class DatabaseInstance:
    provider: str
    region: str
    id: str
    name: Optional[str] = None
    engine: Optional[str] = None
    engine_version: Optional[str] = None
    status: Optional[str] = None
    instance_class: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    endpoint: Optional[str] = None
    port: Optional[int] = None
    tags: Dict[str, str] = field(default_factory=dict)
    raw: Optional[Dict[str, Any]] = None
