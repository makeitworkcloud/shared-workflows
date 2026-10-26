# OpenCode advisory PR reviews

Status: authored draft; not CI-validated, selected by callers, or enabled.

The reusable `.github/workflows/_opencode-review.yml` follows the
[official V2 CLI CI approach](https://opencode.ai/v2/docs/cli/commands/).
It adds no server bridge, cloud service, custom image, chart release, or
cluster rollout. OpenCode reviews are advisory, not a merge approval or
replacement for required CI.
The review job can succeed while publishing `REVIEW_INCOMPLETE`; its green
Actions conclusion is not evidence of completed review coverage and must not
be used as a required review-completion gate.

## Ownership and interface

`shared-workflows` owns the reusable workflow. `tfroot-github` owns the planned
generated caller path `.github/workflows/opencode-review.yml`. No generated
caller or selected shared-workflow SHA exists in this draft. Do not seed or
adopt that path without its owner and collision checks.

| Input or secret | Contract |
| --- | --- |
| `enabled` | Boolean, default `false`; also requires repository variable `OPENCODE_REVIEW_ENABLED=true`. |
| `model` | Required `openai/<model>` identifier; no variant suffix. |
| `pr-number` | PR number for a manual dispatch; defaults to `0`. |
| `approved-head-sha` | Exact current head approved by a manual dispatch. |
| `OPENAI_API_KEY` | Optional Actions secret; inference is incomplete when absent. |

Callers must grant only `contents: read` and `pull-requests: write`, explicitly
map the provider secret, and pin the reusable workflow to a reviewed immutable
commit. Do not inherit unrelated secrets. Credential provisioning and choosing
the model are separate activation decisions; this change provisions neither.

## Events and fork approval

The callee accepts a default-branch `pull_request_target` caller for `opened`,
`reopened`, `synchronize`, and `ready_for_review`, or a default-branch
`workflow_dispatch` caller. Other refs/events fail closed.

Same-repository PRs include bot and Dependabot authors. Automatic fork events
only update the sticky comment with approval instructions; they never run
inference. A maintainer explicitly dispatches the caller with `pr-number` and
`approved-head-sha`. The triggering actor must currently have write, maintain,
or admin permission. Approval does not carry forward to a new head.

Reviews use a repository/PR concurrency group and cancel superseded runs. A
cancelled run may leave the SHA-attributed, nonfinal pending comment behind;
cleanup is not guaranteed.

## Review boundary

The workflow captures exact open-PR base/head SHAs, checks out the head with full
history and no persisted credentials, submodules, or LFS, then computes one
`base...head` Git diff with external diff and text conversion disabled. There
is no alternate source route. Sensitive-named paths, binary/submodule/LFS
changes, missing objects, and diffs over **100000 bytes** produce incomplete
results without inference. Unchanged sensitive paths remain excluded from the
agent's read rules; these naming exclusions are not a general secret scanner.

OpenCode runs outside the PR checkout with fresh home/XDG directories and
trusted V2 configuration. PR plugins and configuration are not loaded as
runtime configuration. Only trusted reviewer prompt bodies and five selected
skill Markdown files are imported from `charts` commit
`09a08579a2b0023044875b131477dd05b0e638fc`; production configuration, MCP
servers, provider settings, and primary-agent instructions are not imported.

The primary can delegate to `adversarial-code-reviewer`,
`infra-security-reviewer`, `devops-engineer`, `qa-engineer`, and
`release-engineer`. Every agent has independent deny-by-default permissions;
children cannot delegate. Source reading and named trusted skills are narrowly
allowed, but shell, mutation, Code Mode, web, and MCP tools are not.
`devops-engineer` remains tool-free. All reviewers use the selected model.
Missing required evidence or blocked reviewers must be reported, not invented.

## Results and dependencies

The CLI has 15 minutes within a 20-minute job, with no retry or provider-failover
wrapper. Exact base/head freshness is checked before inference and before final
publication. The maintained sticky-comment action updates one `opencode-review`
comment. Its write is not atomic with the freshness check; every result is
explicitly attributed to its reviewed SHAs rather than claimed current forever.

Only the final assistant text is extracted from the pinned CLI's NDJSON stream.
Reasoning, tool output, stderr, and provider errors are not published. Findings
are rendered as inert indented text, preventing model-generated images, links,
or mentions from becoming active comment markup. The final model line must be
exactly `REVIEW_COMPLETE` or `REVIEW_INCOMPLETE`; missing/invalid/oversized output
is incomplete, not silently truncated. Completion does not mean no defects.
The rendered comment, including indentation and snapshot attribution, is also
bounded to 60000 bytes; an expanded or multibyte result over that limit is
reported incomplete without publishing partial findings.

This path selects official npm `@opencode/cli@2.1.4`, Node 24, checkout 7.0.1,
setup-node 7.1.0, github-script 9.0.0, and sticky-pull-request-comment 3.0.5.
Actions use full commit pins in the workflow. The GitHub latest-release selector
currently reports OpenCode V1; it must not select the V2 CLI dependency.

## Validation and activation gates

`.github/workflows/_opencode-review-tests.yml` runs
`tests/test_opencode_review_workflow.py` with PyYAML 6.0.3 and Node mocks against
the actual inline scripts. It uses no provider secret or inference. Existing
repository lint remains unchanged. These tests cover control flow, generated
configuration, collection bounds, stale snapshots, and stream decoding; they
do not prove runtime permission enforcement, real event/secret behavior,
cancellation, CLI compatibility, or review usefulness.

Before activation: resolve completed-diff/security reviews and PR CI; select the
reviewed shared commit in the separately reviewed `tfroot-github` caller;
confirm its plan and any apply/adoption; provision the provider secret securely;
confirm explicit repository enablement; and authorize a bounded functional
pilot including malicious configuration and denied-tool probes. Each stage
requires its own evidence. Nothing in this authored draft establishes a later
delivery stage.
