# shared-workflows

Reusable GitHub Actions workflows for makeitworkcloud repositories.

## Usage

Call a shared workflow from your repository:

```yaml
name: OpenTofu

on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main

permissions:
  contents: read
  id-token: write
  pull-requests: write

jobs:
  opentofu:
    uses: makeitworkcloud/shared-workflows/.github/workflows/opentofu.yml@main
    secrets:
      SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
```

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `opentofu.yml` | OpenTofu/Terraform CI/CD with plan comments and apply on merge |

## Container

All workflows use `ghcr.io/makeitworkcloud/runner:latest`.

See [images](https://github.com/makeitworkcloud/images) for container source and included tools.

## Repository Setup

1. Grant `id-token: write` in the caller workflow so GitHub OIDC can assume the SOPS KMS role.
2. Optionally add `SOPS_AGE_KEY` secret as an age fallback while SOPS files retain age recipients.
3. Ensure the default `aws-role-to-assume` exists (`arn:aws:iam::332355796717:role/github-actions-sops-kms`) or pass another role ARN.
4. Create caller workflow in `.github/workflows/`.
5. Ensure repository has required files (e.g., `Makefile` with expected targets).
