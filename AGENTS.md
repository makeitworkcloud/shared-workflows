# Agent Instructions

## Repository Purpose

This repository contains reusable GitHub Actions workflows for the `makeitworkcloud` organization.

## Contribution Workflow

Use a branch and pull request for all changes. Do not push directly to `main`,
and do not push any branch unless explicitly requested.

## Key Workflows

### opentofu.yml

Reusable workflow for OpenTofu/Terraform root module repositories (`tfroot-*`). It:

1. Fetches the canonical pre-commit config from `makeitworkcloud/images`
2. Runs OpenTofu initialization and pre-commit without AWS or SSH credentials on the `arc-tf` runner pod (which is itself the `tfroot-runner` image - no nested `container:` block)
3. Runs a credentialed plan only for same-repository pull requests; fork pull requests run only the uncredentialed test job
4. Posts available plan output as a PR comment, reports a plan failure in that comment, and then fails the plan job
5. Applies on any push to `main` after the test and configured environment gates pass

**Pre-commit configuration is centralized** in `makeitworkcloud/images/tfroot-runner/pre-commit-config.yaml`. Do not add `.pre-commit-config.yaml` to individual tfroot repos.

### Workflow Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `runs-on` | `arc-tf` | Runner label — the in-cluster ARC scale set whose pods run the tfroot-runner image |
| `setup-ssh` | `false` | Provision an SSH key + known_hosts for libvirt-style root modules |
| `environment` | `production` | Environment for the apply job |
| `aws-region` | `us-west-2` | AWS region for SOPS KMS access |
| `aws-role-to-assume` | `arn:aws:iam::332355796717:role/github-actions-sops-kms` | IAM role assumed via GitHub OIDC for SOPS KMS decrypt/encrypt |

The test job has only `contents: read` permission and does not receive AWS or SSH credentials. The plan job has `contents: read`, `id-token: write`, and `pull-requests: write`; the apply job has `contents: read` and `id-token: write`. Caller workflows must grant the permissions needed by credentialed plan and apply jobs. SOPS decryption for `tfroot-*` repos uses AWS KMS via OIDC; do not pass `SOPS_AGE_KEY` to this workflow.

There is no `container` input. The `arc-tf` runner pod IS the image, so adding `container:` on top would nest a container inside a container — don't do it.

### _dependabot-notify.yml

Reusable workflow that posts a synthetic alert to the cluster Alertmanager
(kube-prometheus-stack, exposed as `alertmanager.makeitwork.cloud` behind a
path-scoped Cloudflare Access app) when a caller repo's `pull_request` event
actor is `dependabot[bot]`. Callers are managed centrally by `tfroot-github`
(`.github/workflows/dependabot-notify.yml` in each repo, `secrets: inherit`).

The reusable lives at the underscore-prefixed path because `tfroot-github`
manages `.github/workflows/dependabot-notify.yml` as the caller in every
repository, including this one — anything at the non-prefixed path here is
overwritten on the next tfroot-github apply.

Requires the `CLOUDFLARE_AUTH_CLIENT_ID` / `CLOUDFLARE_AUTH_CLIENT_SECRET`
Actions secrets in the caller repository (the "GitHub Actions" Cloudflare
Access service token, distributed by `tfroot-github`). Alertmanager itself
has no auth; the Access app is the only gate. No checkout and no
`GITHUB_TOKEN` permissions are needed.

## Failure Modes

### "manifest unknown" or image pull failures

The `tfroot-runner` image is missing or the tag is wrong. Check:
1. Did the `images` repo `buildah` workflow succeed for the latest commit?
2. Is the runner template image tag in `kustomize-cluster/workloads/arc/arc-tf-application.yaml` resolvable on GHCR (`ghcr.io/makeitworkcloud/tfroot-runner:latest`)?

### Pre-commit hook failures

If hooks fail with missing tools or config mismatches:
1. Verify the canonical config in `images/tfroot-runner/pre-commit-config.yaml`
2. Rebuild `tfroot-runner` image if hooks were added/updated

### Checks never appear on a PR

No checks at all (not even pending) means workflow runs were never created.
Confirm with `gh run list --repo <repo> --branch <branch>` and by checking
check-runs on the head SHA. Zero runs of every event type across the org's
repos — especially when earlier PRs triggered normally — indicates a GitHub
Actions event-delivery incident, not a workflow configuration problem. Check
https://www.githubstatus.com before editing workflow files to "fix" it.
Recover by closing and reopening the PR (`reopened`) or force-pushing the
branch (`synchronize`); both are trigger types in these workflows.

### dependabot-notify shows `skipped` on human PRs

Expected. The notify job requires `github.actor == 'dependabot[bot]'`; on
human-authored PRs the caller workflow runs and the job skips. A skipped
notify job is not a failure — but `gh run watch --exit-status` treats a run
whose jobs all skipped as unsuccessful, so watch the `ci`/`opentofu` run when
validating a PR.

## Related Repositories

- `images` - Contains `tfroot-runner` image and canonical pre-commit config
- `tfroot-cloudflare`, `tfroot-libvirt`, `tfroot-github`, `tfroot-aws` - Terraform root module repos that consume this workflow
