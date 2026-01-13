# Agent Instructions

## Repository Purpose

This repository contains reusable GitHub Actions workflows for the `makeitworkcloud` organization.

## Push Access

Agents are authorized to push directly to `main` in this repository.

## Key Workflows

### opentofu.yml

Reusable workflow for OpenTofu/Terraform root module repositories (`tfroot-*`). It:

1. Fetches canonical pre-commit config from `makeitworkcloud/images` repo
2. Runs pre-commit tests using the `tfroot-runner` container image
3. Posts plan output as PR comments
4. Applies on merge to main

**Pre-commit configuration is centralized** in `makeitworkcloud/images/tfroot-runner/pre-commit-config.yaml`. Do not add `.pre-commit-config.yaml` to individual tfroot repos.

## Related Repositories

- `images` - Contains `tfroot-runner` image and canonical pre-commit config
- `tfroot-cloudflare`, `tfroot-libvirt`, `tfroot-github`, `tfroot-aws` - Terraform root module repos that consume this workflow
