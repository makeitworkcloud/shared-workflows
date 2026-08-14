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
```

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `opentofu.yml` | OpenTofu/Terraform CI/CD with PR validation and an environment-gated apply on every push to `main` |

Same-repository PRs run tests and a credentialed plan; fork PRs run tests only. A push to `main` runs tests followed by a fresh apply, which does not reuse the PR plan.

## Runners

Repository CI runs on `ubuntu-24.04`. The reusable OpenTofu workflow defaults
to the `arc-tf` runner, whose pod uses the `tfroot-runner` image directly. That
image uses Actions Runner `2.336.0`, above the `2.327.1` minimum required by
the workflows' Node 24 actions.

See [images](https://github.com/makeitworkcloud/images) for container source and included tools.

## Repository Setup

1. Grant `id-token: write` in the caller workflow so GitHub OIDC can assume the SOPS KMS role.
2. Ensure the default `aws-role-to-assume` exists (`arn:aws:iam::332355796717:role/github-actions-sops-kms`) or pass another role ARN.
3. Create caller workflow in `.github/workflows/`.
4. Ensure repository has required files (e.g., `Makefile` with expected targets).
