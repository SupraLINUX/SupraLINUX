# Repository mutation and CI responsibility

Status: **active decision**  
Date: **2026-09-17**

## Decision

GitHub Actions is a validation and build system for SupraLINUX. It is not the normal mechanism for materializing, editing, promoting, or otherwise mutating repository source state.

Multi-file repository changes are prepared as one coherent change set, validated before publication as far as the execution environment allows, and then written to `architecture/bootstrap-v1` as a single atomic Git commit. The preferred remote-write mechanism is Git objects (`blob -> tree -> commit -> ref`) using the current branch tree as the base. Per-file commits are reserved for genuinely independent changes, not for assembling one logical batch.

CI runs only after the coherent source state exists in Git. A workflow may generate build/test artifacts and evidence, but it must not be used as a substitute editor or as a temporary repository materializer.

## Rationale

The previous iterative pattern created unnecessary failure surfaces:

- temporary materializer/promoter workflows could fail before package work began;
- sequential per-file mutations exposed partially updated manifests, scripts and documentation;
- repeated workflow retries produced noise without changing the root cause;
- repository-policy failures could be mistaken for package failures;
- remote fetch/edit loops made large changes slow and difficult to reason about.

An atomic source commit makes the state under test unambiguous and keeps CI focused on validation rather than repository construction.

## Operational rules

1. Read the current branch HEAD and base tree once at the start of a write transaction.
2. Gather only the source/reference material required for the change. Retained GitHub artifacts may be downloaded and inspected locally.
3. Prepare the complete package/manifests/scripts/documentation change set before moving the branch ref.
4. Validate syntax, schemas, invariants and deterministic checks locally whenever the available environment can run them.
5. Create all changed blobs, construct one tree from the current base tree, create one commit with the current HEAD as parent, then fast-forward the branch ref once.
6. Re-read the branch ref immediately before publication. If HEAD changed, do not force-update; rebuild/rebase the transaction against the new HEAD.
7. Run Repository Policy after publication, then the minimum package/build lanes affected by the event delta.
8. Diagnose GitHub Actions from the job/run summary first. Read the complete log only when the summary and retained evidence are insufficient.
9. Do not rerun an unchanged failing job merely to seek a different result. Change an identified input/cause first, unless the failure is explicitly classified as transient infrastructure.
10. Preserve DAG semantics: `PASS`, `FAIL`, and `BLOCKED` are distinct. A failed node does not prevent independent nodes from being attempted.

## CI boundaries

Allowed CI responsibilities include:

- repository and manifest policy;
- source-integrity verification;
- dependency/provider validation;
- clean package builds;
- tests and consumer smoke tests;
- artifact/evidence production;
- authoritative KVM/JIT gates;
- publication verification when a publication stage is explicitly reached.

Normal CI must not:

- create the source change it is meant to validate;
- commit generated fixes back to the branch;
- use a temporary workflow as the primary way to assemble a batch;
- promote canonical manifests by mutating Git from inside the validation job.

## Historical status

Earlier materializer, one-shot promoter, staging-probe, or similar workflows/commits remain historical evidence where already recorded. They are not the normative implementation model for subsequent SupraLINUX work.

## Relationship to the build DAG

This decision does not change the build architecture. SupraLINUX still discovers failures globally, attempts all independent nodes possible at each topological level, feeds only PASS artifacts to dependents, records FAIL only for nodes actually attempted, and records dependency-prevented nodes as BLOCKED.

The change is narrower: repository state is assembled atomically before CI, while CI evaluates that state.
