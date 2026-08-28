# Agent Instructions

This repository owns reusable GitHub Actions workflows for Make IT Work Cloud. Treat workflow inputs, permissions, runner labels, triggers, emitted checks, and artifacts as a public interface to all callers.

`opentofu.yml` runs on the `arc-tf` runner pod, whose image is owned by `images/tfroot-runner`; do not add a nested job container. The canonical pre-commit configuration is owned by that image repository and is fetched at CI time.

Use GitHub MCP to identify callers, inspect checks, and diagnose Actions delivery. Do not use local `gh` commands or dispatch/re-run workflows without explicit confirmation. A change must preserve uncredentialed fork validation, same-repository plan behavior, and environment-gated apply behavior unless the user explicitly requests a contract change.
