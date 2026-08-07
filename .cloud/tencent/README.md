# Tencent Cloud mapping

The official common SDK credential provider chain is used for CVM, VPC, and CDB. COS has a separate official SDK and bucket names include the application ID suffix.

| Unified domain | Tencent Cloud service | Primary operation |
|---|---|---|
| instances | CVM | `DescribeInstances` |
| VPC/subnets/security groups | VPC | `DescribeVpcs`, `DescribeSubnets`, `DescribeSecurityGroups` |
| SG rules | VPC | security-group policy APIs |
| object storage | COS | `list_buckets`, `list_objects` |
| databases | CDB | `DescribeDBInstances` |

Official sources:

- https://github.com/TencentCloud/tencentcloud-sdk-python
- https://www.tencentcloud.com/document/product/213/33258
- https://www.tencentcloud.com/document/product/215/15778
- https://www.tencentcloud.com/document/product/215/15784
- https://www.tencentcloud.com/document/product/215/15808
- https://www.tencentcloud.com/document/product/236/15872
- https://www.tencentcloud.com/document/product/436/12269

Retrieved: 2026-08-07.
