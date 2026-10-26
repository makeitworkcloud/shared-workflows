# OpenCode PR reviews

Uses the [official V1 GitHub action](https://opencode.ai/docs/github/#pull-request-example),
as explicitly selected by the owner. No custom scripts, agents, policy generator,
JSON decoder, sticky-comment bridge, or model-specific test harness is included.

## Interface

Call `.github/workflows/_opencode-review.yml` at a reviewed immutable commit from
`pull_request` events (`opened`, `synchronize`, `reopened`, `ready_for_review`).
Pass `model` (`provider/model`), explicitly map `OPENAI_API_KEY`, and grant
`contents: read`, `pull-requests: read`, and `issues: write`. This credential
interface supports OpenAI models; other providers need their own secret mapping.
No OpenCode GitHub App installation or OIDC permission is required.

Both `enabled: true` and `OPENCODE_REVIEW_ENABLED=true` are required. The default
is disabled; required caller inputs/secrets still apply to a disabled invocation.
Fork and merge-queue events are excluded. Superseded PR runs are cancelled; the
job limit is 20 minutes. There is no custom retry or failover wrapper. Skipped or
green Actions checks do not establish completed review coverage or merge approval.

## Accepted upstream limitations

- Each run creates a new comment, not one sticky comment.
  Cancellation/re-execution can leave partial results or duplicate comments;
  failure/timeout commenting is not guaranteed.
- Upstream requires the triggering actor to have write/admin permission;
  bot and Dependabot coverage is not guaranteed.
- Fork approval/review is not implemented. No `pull_request_target` credential
  workaround is used.
- No chart-packaged agents/skills, exact-SHA approval/stale-result guard,
  custom completion marker, output sanitizer, or completion guarantee is added.
- The action follows the current PR branch, which can move during a run.
- The action is pinned to V1 `v1.19.4`'s commit, but its installer downloads the
  latest CLI and its nested cache action uses a tag. These are upstream behavior,
  not a fully immutable dependency chain.

The built-in `plan` agent and advisory prompt are not a security sandbox.
Repository configuration/plugins and provider-key exposure require a separately
authorized security pilot before enabling. The token cannot write repository
contents; provider credentials must never be exposed to untrusted execution.

Make IT Work Cloud maintainers own this wrapper in `shared-workflows`, under
the owner's explicit selection of the limited V1 integration. `tfroot-github` owns future
generated `.github/workflows/opencode-review.yml` callers. No caller, credential,
repository setting, deployment, or enablement is delivered by this change.
Existing lint/actionlint validates the YAML; there are no bespoke review tests.
Merging, caller adoption/apply, credentials, pilot, and enablement remain separate
confirmation gates. Existing chart and abandoned bridge drafts are not shipped.
