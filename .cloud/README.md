# geoffrey-llm Cloud Reference

This directory records API mapping notes derived from official vendor documentation for `geoffrey_llm.cloud`. It is documentation only: it must never contain access keys, secret keys, session tokens, account IDs, real resource IDs, exported credentials, or secret-bearing command output.

## SDK scope

The public Python entry point is `geoffrey_llm.cloud`, not this hidden directory. The first release normalizes:

- compute instances
- VPCs and subnets
- security groups and rules
- object-storage buckets and object listings
- managed database instances

Cloud credentials are resolved at runtime by official vendor SDK chains (environment, named profile where supported, and workload/instance role). `CloudConfig` intentionally has no credential fields.

## Safety policy

All clients default to read-only mode. Security-group mutations additionally require `read_only=False`, `allow_mutation=True`, and `dry_run=False`; `0.0.0.0/0` and `::/0` require an explicit per-call override.

## Vendor notes

- [Alibaba Cloud](alibaba/README.md)
- [Tencent Cloud](tencent/README.md)
- [Huawei Cloud](huawei/README.md)
- [AWS](aws/README.md)

Retrieved: 2026-08-07.
