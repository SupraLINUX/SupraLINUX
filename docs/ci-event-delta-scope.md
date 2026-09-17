# CI event-delta scope

Status: **implemented and verified repository-wide for ordinary pull-request routing**  
Last reviewed: **2026-09-17**

## Purpose

Long-lived Draft PRs accumulate many changed paths relative to `main`. GitHub pull-request path filters answer whether a path changed anywhere in the PR, not whether the latest synchronization changed a package input. On PR #1 this caused documentation-only synchronizations to create many unrelated workflow runs even though the package lanes later skipped their expensive work.

SupraLINUX therefore separates ordinary PR event admission from lane execution. One router evaluates the exact event delta first; only relevant synchronizations are allowed to fan out into reusable package/reference/provider/diagnostic lanes.

## Centralized PR router

`.github/workflows/pr-ci-router.yml` is the single owner of ordinary `pull_request` events for `opened`, `synchronize` and `reopened` across the migrated hosted preflight lanes.

For `pull_request/synchronize`, the router compares `${{ github.event.before }}` to `${{ github.event.after }}` after `actions/checkout` with `fetch-depth: 0`.

For `opened` and `reopened`, it compares the PR base SHA with the PR head SHA.

The plan job classifies the changed paths before any reusable lane is invoked:

- if every changed path is under `docs/**` or is `README.md`, `run_ci=false`;
- otherwise `run_ci=true` and the reusable lanes may be called.

The 18 migrated workflows keep their own lane-specific event-delta checks. The router decides whether the general hosted CI family needs to be entered at all; each called lane still decides whether its own node/reference/provider inputs changed. This preserves fine-grained scope while eliminating unnecessary top-level workflow runs for documentation-only synchronizations.

## Reusable lane contract

The migrated package/reference/provider/diagnostic workflows:

- expose `workflow_call` for the PR router;
- retain `workflow_dispatch` as the explicit manual/force path;
- retain `push: main` where that trigger already existed;
- do not independently subscribe to ordinary `pull_request` lifecycle events;
- preserve the existing build, test, artifact and node-scope logic.

Repository Policy validates this contract and fails if a routed lane regains its own ordinary PR trigger or is no longer referenced by the router.

Controlled authoritative workflows triggered by PR labels are intentionally outside this router. Their security/admission semantics are separate from ordinary hosted preflight routing.

## Superseded-run cancellation

The router uses:

```yaml
concurrency:
  group: pr-ci-router-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

A newer synchronization of the same PR cancels the older router run instead of allowing obsolete package/reference work to continue consuming runners. This affects execution scheduling only; retained PASS/FAIL evidence from completed historical runs is not rewritten.

## Verified evidence

The migration was validated incrementally rather than declared successful from static inspection alone.

- Migration commit `65c4d33360fd6d5031e1e9a406f84b39446627a7` converted the hosted lanes to reusable workflows and introduced the router.
- Commit `0ac245e462ba17f840b241e2c32c6cccf1975366` added per-PR concurrency with cancellation.
- Router run `35178935759` was automatically **cancelled** when superseded by a newer synchronization, proving the cancellation contract.
- Repository/Qt validators were aligned with the new architecture in commits `a4ee9c05d13b47c2cb9e7282e9c4e5c66ee9a6d9` and `bb475ab1ce5a882759704a07f4c86f4183e76d42`.
- Repository Policy run `35181296924`: **PASS**, all 30 validation steps successful.
- Final documentation-only probe commit `d4a9a698fe83ea9cb6341ecf80e08f096bb7386b` produced only two top-level workflows: Repository Policy and PR CI router.
- PR CI router run `35181360370`: **PASS**; `Plan PR event delta` PASS and all 18 reusable hosted lanes `skipped` without runner execution.
- Repository Policy run `35181360187`: **PASS**, all 30 validation steps successful on the same documentation-only probe.

This is the accepted evidence that documentation-only synchronizations no longer fan out into package/reference/provider execution.

## Historical Attica implementation

Before the centralized router existed, Attica proved the basic exact-event-delta technique at lane level. Its package/reference workflows compared `${{ github.event.before }}` to `${{ github.event.after }}` and intentionally skipped expensive work for irrelevant deltas.

An early scope-helper exercise failed with exit `126` because helper files created through the GitHub Contents API did not have executable mode. The correction invoked those helpers explicitly through `bash`. That historical failure remains evidence of the implementation defect; it was not a package FAIL.

Commit `5b09963d3af85b4d1b014102ff12c385fb3bf775` later proved Attica documentation-only skip behavior in runs `34707922535` and `34707922491`.

The centralized router generalizes the scheduling side of that model while retaining lane-level scope detection.

## Required semantics

- Ordinary hosted PR CI is admitted through one centralized router.
- `synchronize` scope uses the exact event `before -> after` delta, not the cumulative PR diff.
- Documentation-only deltas do not invoke the 18 routed hosted lanes.
- Relevant non-documentation deltas may invoke the reusable lanes; each lane retains its own precise scope decision.
- `workflow_dispatch` remains an explicit way to force an individual reusable lane.
- Superseded router runs for the same PR are cancelled.
- A router/scope implementation error is a CI failure; it must not be reported as a package FAIL.
- Skipping an unchanged node does not alter existing PASS/FAIL/BLOCKED evidence.
- Authoritative labeled/KVM workflows retain their separate controlled admission model.
