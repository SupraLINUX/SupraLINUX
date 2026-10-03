# Centralized pull-request CI routing

Status: **active decision**  
Date: **2026-09-17**

## Decision

Ordinary hosted pull-request CI for SupraLINUX is centralized in `.github/workflows/pr-ci-router.yml`.

The router owns `pull_request` lifecycle events `opened`, `synchronize` and `reopened` for the migrated hosted package/reference/provider/diagnostic family. The 18 routed workflows are reusable/manual lanes: they expose `workflow_call`, retain `workflow_dispatch`, preserve `push: main` where it previously existed, and do not independently subscribe to ordinary PR lifecycle events.

This decision does not change the build DAG, package semantics, test contracts, artifacts, or authoritative KVM admission model. It changes scheduling and event admission only.

## Problem

PR #1 is a long-lived Draft PR with a large accumulated diff. Independent `pull_request` subscriptions caused every synchronization to create many top-level workflow runs, even when the latest commit changed documentation only.

GitHub PR path filtering is not sufficient for this use case because it answers against the PR's accumulated changed paths rather than serving as an exact latest-synchronization delta gate. The repository already had lane-level event-delta helpers, but those helpers ran only after the individual workflows had already been scheduled.

The result was unnecessary runner scheduling, duplicated setup, obsolete runs continuing after newer commits, and more CI noise around the actual KDE work.

## Execution model

The centralized router performs a cheap `plan` job first.

For `pull_request/synchronize`:

```text
github.event.before -> github.event.after
```

For `opened` and `reopened`:

```text
pull_request.base.sha -> pull_request.head.sha
```

The router checks the changed paths from that exact comparison.

If every changed path is under `docs/**` or is `README.md`, the router sets `run_ci=false`. All 18 reusable hosted lanes are skipped without acquiring runners.

If at least one non-documentation path changed, the router sets `run_ci=true` and may call the reusable lanes. Each lane then retains its own exact scope detector, so a general CI-relevant synchronization still does not imply that every package/node performs expensive work.

## Concurrency

Router runs are grouped by PR number:

```yaml
concurrency:
  group: pr-ci-router-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

A new synchronization therefore cancels the obsolete router run for the same PR. Completed evidence is preserved; only still-running superseded work is stopped.

## Boundaries

Repository Policy remains an independent PR workflow and always validates repository invariants.

The authoritative KVM/JIT workflows that are admitted through controlled PR labels remain outside the ordinary router. They retain their fork checks, labels, JIT runner constraints, exact-run binding and authoritative semantics.

`workflow_dispatch` remains available on the routed reusable lanes as an explicit manual force path.

## Policy enforcement

`scripts/validate_repository.py` requires:

- the PR router to exist;
- explicit `opened`, `synchronize`, `reopened` lifecycle handling;
- immutable checkout and full comparison history;
- exact `before/after` and base/head comparison inputs;
- documentation-only classification;
- per-PR `cancel-in-progress` concurrency;
- every migrated lane to expose `workflow_call` and `workflow_dispatch`;
- every migrated lane to be referenced by the router;
- no migrated lane to regain an independent ordinary `pull_request` trigger.

`scripts/validate_qt_provider.py` additionally enforces the same reusable/router relationship for the Qt provider lane without weakening any Qt provider requirements or evidence checks.

## Verification history

The design was not promoted to active status until it passed live GitHub Actions exercises.

1. `65c4d33360fd6d5031e1e9a406f84b39446627a7` introduced the centralized router and converted the hosted lanes to reusable workflows.
2. `0ac245e462ba17f840b241e2c32c6cccf1975366` added per-PR cancellation.
3. Router run `35178935759` was automatically **cancelled** by a newer synchronization, proving `cancel-in-progress` behavior.
4. `a4ee9c05d13b47c2cb9e7282e9c4e5c66ee9a6d9` updated repository invariants to validate the new architecture rather than the removed direct-trigger model.
5. `bb475ab1ce5a882759704a07f4c86f4183e76d42` aligned the Qt provider validator with the router while preserving Qt policy.
6. Repository Policy run `35181296924` completed **PASS**, 30/30 steps.
7. Documentation-only probe commit `d4a9a698fe83ea9cb6341ecf80e08f096bb7386b` changed only `docs/ci-router-probe.md`.
8. PR CI router run `35181360370` completed **PASS** with exactly one executed planning job and all 18 reusable hosted lanes `skipped`.
9. Repository Policy run `35181360187` completed **PASS**, 30/30 steps, on the same documentation-only synchronization.

These runs are the acceptance evidence for this decision.

## Result

For an ordinary documentation-only PR synchronization, SupraLINUX now creates two relevant top-level workflows instead of the previous broad fan-out:

- Repository Policy, which validates repository integrity;
- PR CI router, whose planning job classifies the exact event delta.

The package/reference/provider/diagnostic lanes remain visible as skipped jobs inside the router but do not execute runners or their expensive steps.

For relevant code/package/manifest changes, the router admits the reusable lanes and their existing node-specific scope logic continues to apply.

## Historical status

The temporary `docs/ci-router-probe.md` file was used only to generate live documentation-only synchronization evidence. It is removed after successful verification and is not part of the architecture.

The earlier model of many independent ordinary PR subscribers is historical and must not be reintroduced without an explicit architecture decision, validator update, documentation update and new evidence.
