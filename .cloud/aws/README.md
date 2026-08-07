# AWS mapping

Official Python SDK: boto3. Credential resolution is delegated to the boto3 session chain (environment, shared profile, web identity, and instance/container roles).

| Unified domain | AWS service | Primary operations |
|---|---|---|
| instances | EC2 | `DescribeInstances` |
| VPC/subnets/security groups | EC2 | `DescribeVpcs`, `DescribeSubnets`, `DescribeSecurityGroups` |
| SG rules | EC2 | `AuthorizeSecurityGroupIngress/Egress`, `RevokeSecurityGroupIngress/Egress` |
| object storage | S3 | `ListBuckets`, `ListObjectsV2` |
| databases | RDS | `DescribeDBInstances` |

Official sources:

- https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html
- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html

Retrieved: 2026-08-07.
