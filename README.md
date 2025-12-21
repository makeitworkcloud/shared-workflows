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

1. Add `SOPS_AGE_KEY` secret (via tfroot-github or manually)
2. Create caller workflow in `.github/workflows/`
3. Ensure repository has required files (e.g., `Makefile` with expected targets)
