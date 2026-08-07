# Huawei Cloud mapping

Huawei Cloud SDK v3 provides ECS, VPC, and RDS clients. OBS uses a separate official SDK. Credentials are resolved by the official provider chain and never stored in this repository.

| Unified domain | Huawei Cloud service | Primary operation |
|---|---|---|
| instances | ECS | `ListServersDetails`, `ShowServer` |
| VPC/subnets/security groups | VPC | `ListVpcs`, `ListSubnets`, `ListSecurityGroups` |
| object storage | OBS | `listBuckets`, `listObjects` |
| databases | RDS | `ListInstances` |

Official sources:

- https://github.com/huaweicloud/huaweicloud-sdk-python-v3
- https://github.com/huaweicloud/huaweicloud-sdk-python-obs
- https://support.huaweicloud.com/intl/en-us/sdk-python-devg-obs/obs_23_0407.html

Retrieved: 2026-08-07.
