# Agent Instructions

## Repository Purpose

This repository contains reusable GitHub Actions workflows for the `makeitworkcloud` organization.

## Push Access

Agents are authorized to push directly to `main` in this repository.

## Key Workflows

### opentofu.yml

Reusable workflow for OpenTofu/Terraform root module repositories (`tfroot-*`). It:

1. Fetches canonical pre-commit config from `tfroot-pre-commit-config.yaml` in this repo
2. Runs pre-commit tests using the `tfroot-runner` container image
3. Posts plan output as PR comments
4. Applies on merge to main

**Pre-commit configuration is centralized** in `tfroot-pre-commit-config.yaml`. Do not add `.pre-commit-config.yaml` to individual tfroot repos.

### Workflow Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `runs-on` | `ubuntu-latest` | Runner label |
| `container` | `ghcr.io/makeitworkcloud/tfroot-runner:latest` | Container image |
| `setup-ssh` | `false` | Whether to setup SSH keys |
| `environment` | `production` | Environment for apply job |

**Note:** `tfroot-libvirt` overrides `container` to use the internal OpenShift registry because it requires SSH access to libvirt hosts from a self-hosted runner.

## Failure Modes

### "manifest unknown" or image pull failures

The `tfroot-runner` image doesn't exist yet. Check:
1. Did the `images` repo Build workflow succeed?
2. Did the `images` repo Pull workflow import to OpenShift? (check logs for actual metadata, not "Unable to connect" errors)

### Pre-commit hook failures

If hooks fail with missing tools or config mismatches:
1. Verify the canonical config in `images/tfroot-runner/pre-commit-config.yaml`
2. Rebuild `tfroot-runner` image if hooks were added/updated

## Related Repositories

- `images` - Contains `tfroot-runner` image and canonical pre-commit config
- `tfroot-cloudflare`, `tfroot-libvirt`, `tfroot-github`, `tfroot-aws` - Terraform root module repos that consume this workflow
