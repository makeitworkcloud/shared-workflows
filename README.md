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

### Cloudflare

Only repositories that manage Cloudflare resources should map their repository
Actions secret into the reusable workflow secret:

```yaml
jobs:
  opentofu:
    uses: makeitworkcloud/shared-workflows/.github/workflows/opentofu.yml@main
    secrets:
      CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

Do not add this mapping for consumers that do not use Cloudflare.

### Automatic pre-commit fix commits

Repositories whose same-repository pull requests should receive automatic
pre-commit fixes map the centrally distributed chart updater GitHub App key:

```yaml
jobs:
  opentofu:
    uses: makeitworkcloud/shared-workflows/.github/workflows/opentofu.yml@main
    secrets:
      CHART_UPDATER_GITHUB_APP_PRIVATE_KEY: ${{ secrets.CHART_UPDATER_GITHUB_APP_PRIVATE_KEY }}
```

The workflow runs the canonical pre-commit suite once on each workflow run. If
it changes tracked files on a same-repository pull request, the workflow commits
the fixes and the resulting push starts the confirmation run. The key is
provisioned by `tfroot-github` to approved repositories only. Without it,
pre-commit drift fails the `test` job and the pull request branch must be
updated manually. Fork pull requests never receive secrets and always fail on
drift.

### Stale pull request lifecycle

`tfroot-github` owns the scheduled caller at
`.github/workflows/stale-pull-requests.yml`; do not hand-maintain that path in
a consumer repository. The reusable callee is
`_stale-pull-requests.yml`.

```yaml
name: stale-pull-requests

on:
  schedule:
    - cron: "17 3 * * *"
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  stale:
    uses: makeitworkcloud/shared-workflows/.github/workflows/_stale-pull-requests.yml@main
    with:
      dry-run: true
```

The caller must be on the consumer's default branch for scheduled execution.
It accepts no secrets. The workflow reports only to its Actions log, and when
`dry-run` is `false`, closes non-draft, unassigned, unmilestoned pull requests
whose `pullRequest.updated_at` is at least 30 days old. Labels `do-not-close`,
`blocked`, and `security` are exempt.

After a successful close, it deletes only an unprotected same-repository head
branch that is neither the default branch nor used as the head or base of any
open pull request. GitHub's closed-pull-request **Restore branch** path is the
recovery mechanism. Enable live mode only after a reviewed dry-run pilot.

## Available Workflows

| Workflow | Description |
|----------|-------------|
| `opentofu.yml` | OpenTofu/Terraform CI/CD with PR validation and an apply on every push to `main` |
| `_stale-pull-requests.yml` | Dry-run-first reusable lifecycle for closing pull requests inactive for at least 30 days and deleting only recoverable eligible head branches. |

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
