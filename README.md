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

### Namecheap

Only repositories that manage Namecheap resources should map their repository
Actions secret into the reusable workflow secret:

```yaml
jobs:
  opentofu:
    uses: makeitworkcloud/shared-workflows/.github/workflows/opentofu.yml@main
    secrets:
      NAMECHEAP_API_KEY: ${{ secrets.NAMECHEAP_API_KEY }}
```

Do not add this mapping for consumers that do not use Namecheap.

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `opentofu.yml` | OpenTofu/Terraform CI/CD with PR validation and an apply on every push to `main` |

Same-repository PRs run tests and a credentialed plan; fork PRs run tests only. A push to `main` runs tests followed by a fresh apply, which does not reuse the PR plan.

## Runners

Repository CI runs on `ubuntu-24.04`. The reusable OpenTofu workflow defaults
to the `arc-tf` runner, whose pod uses the `tfroot-runner` image directly. That
image uses Actions Runner `2.336.0`, above the `2.327.1` minimum required by
the workflows' Node 24 actions.

See [images](https://github.com/makeitworkcloud/images) for container source and included tools.

## Repository Setup

1. Grant `id-token: write` in the caller workflow so GitHub OIDC can authenticate the cloud provider.
2. For AWS roots, ensure the default `aws-role-to-assume` exists (`arn:aws:iam::332355796717:role/github-actions-sops-kms`) or pass another role ARN.
3. For GCP roots, pass both `gcp-workload-identity-provider` and `gcp-service-account`; this selects Google Workload Identity Federation instead of AWS credentials.
4. Create caller workflow in `.github/workflows/`.
5. Ensure repository has required files (e.g., `Makefile` with expected targets).
