# CI event-delta scope

Status: **implemented for Attica package/reference workflows; verification in CI in progress**  
Last reviewed: **2026-09-12**

## Purpose

Long-lived Draft PRs accumulate many changed paths relative to `main`. GitHub pull-request `paths:` filters therefore answer whether a path changed anywhere in the PR, not whether the latest synchronization changed a package input. That behavior caused expensive package/reference jobs to be scheduled again for evidence and documentation-only commits.

SupraLINUX package workflows that perform expensive work must distinguish workflow scheduling from expensive execution. A cheap job may start on a PR synchronization, but package builds, retained-artifact downloads and external reference captures should execute only when the exact event delta changes an input relevant to that operation.

## Attica implementation

For `pull_request/synchronize`, the Attica workflows compare `${{ github.event.before }}` to `${{ github.event.after }}` after `actions/checkout` with `fetch-depth: 0`.

Package-build scope is limited to:

- `packages/kde/attica/**`;
- `scripts/run-kde-attica-package-preflight.sh`;
- `scripts/kde-attica-package-preflight-needed.sh`;
- `.github/workflows/kde-attica-package-preflight.yml`.

Packaging-reference scope is separate and limited to:

- `scripts/run-kde-attica-packaging-reference.sh`;
- `scripts/kde-attica-packaging-reference-needed.sh`;
- `.github/workflows/kde-attica-packaging-reference.yml`.

Documentation and machine-readable evidence/state changes are intentionally not build/reference inputs.

## Historical implementation defect

The first documentation-only exercise reached the new scope step but failed with exit `126`: the new helper files had been created through the GitHub Contents API with mode `0644`, while the workflows invoked them as executables. No expensive Attica build/reference steps ran in that failed exercise.

The correction invokes scope helpers explicitly through `bash`, so scope logic no longer depends on their executable bit. Repository Policy validates the input lists, exact event-delta binding and conditional gating of expensive steps.

## Required semantics

- A relevant input delta executes the corresponding expensive operation.
- An irrelevant delta returns the intentional skip state and the job still succeeds.
- `workflow_dispatch` remains an explicit way to force the operation.
- A scope implementation error is a CI failure; it must not be reported as a package FAIL.
- Skipping an unchanged node does not alter existing PASS/FAIL/BLOCKED evidence.

This mechanism is the template for the generalized Tier 1 package campaign.
