# Alibaba Cloud mapping

Official Tea SDK adapters use the official credential provider chain; credentials must not be passed into `CloudConfig` or recorded here.

| Unified domain | Alibaba Cloud service | Primary API family |
|---|---|---|
| instances/security groups | ECS | `DescribeInstances`, `DescribeSecurityGroups`, `DescribeSecurityGroupAttribute`, `AuthorizeSecurityGroup`, `RevokeSecurityGroup` |
| VPC/subnets | VPC | VPC and VSwitch describe APIs |
| object storage | OSS | bucket and object list APIs |
| databases | RDS | `DescribeDBInstances` |

Official sources:

- https://help.aliyun.com/zh/sdk/developer-reference/credentials
- https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-overview
- https://help.aliyun.com/zh/vpc/developer-reference/api-vpc-2016-04-28-overview
- https://help.aliyun.com/zh/oss/developer-reference/overview
- https://help.aliyun.com/zh/rds/developer-reference/api-rds-2014-08-15-overview

Retrieved: 2026-08-07.
