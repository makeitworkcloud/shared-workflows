# Agent Instructions

## Repository Purpose

This repository contains reusable GitHub Actions workflows for the `makeitworkcloud` organization.

## Push Access

Agents are authorized to push directly to `main` in this repository.

## Key Workflows

### opentofu.yml

Reusable workflow for OpenTofu/Terraform root module repositories (`tfroot-*`). It:

1. Fetches the canonical pre-commit config from `makeitworkcloud/images`
2. Assumes the SOPS KMS role through GitHub OIDC/WIF
3. Runs pre-commit on the `arc-tf` runner pod (which is itself the `tfroot-runner` image — no nested `container:` block)
4. Posts plan output as PR comments
5. Applies on merge to main

**Pre-commit configuration is centralized** in `makeitworkcloud/images/tfroot-runner/pre-commit-config.yaml`. Do not add `.pre-commit-config.yaml` to individual tfroot repos.

### Workflow Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `runs-on` | `arc-tf` | Runner label — the in-cluster ARC scale set whose pods run the tfroot-runner image |
| `setup-ssh` | `false` | Provision an SSH key + known_hosts for libvirt-style root modules |
| `environment` | `production` | Environment for the apply job |
| `aws-region` | `us-west-2` | AWS region for SOPS KMS access |
| `aws-role-to-assume` | `arn:aws:iam::332355796717:role/github-actions-sops-kms` | IAM role assumed via GitHub OIDC for SOPS KMS decrypt/encrypt |

Caller workflows must grant `id-token: write` permissions for OIDC. SOPS decryption for `tfroot-*` repos uses AWS KMS via OIDC; do not pass `SOPS_AGE_KEY` to this workflow.

There is no `container` input. The `arc-tf` runner pod IS the image, so adding `container:` on top would nest a container inside a container — don't do it.

## Failure Modes

### "manifest unknown" or image pull failures

The `tfroot-runner` image is missing or the tag is wrong. Check:
1. Did the `images` repo `buildah` workflow succeed for the latest commit?
2. Is the runner template image tag in `kustomize-cluster/workloads/arc/arc-tf-application.yaml` resolvable on GHCR (`ghcr.io/makeitworkcloud/tfroot-runner:latest`)?

### Pre-commit hook failures

If hooks fail with missing tools or config mismatches:
1. Verify the canonical config in `images/tfroot-runner/pre-commit-config.yaml`
2. Rebuild `tfroot-runner` image if hooks were added/updated

## Related Repositories

- `images` - Contains `tfroot-runner` image and canonical pre-commit config
- `tfroot-cloudflare`, `tfroot-libvirt`, `tfroot-github`, `tfroot-aws` - Terraform root module repos that consume this workflow
