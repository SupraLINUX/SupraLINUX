# KDE Tier 2 campaign automation

Status: **implemented foundation**  
Last reviewed: **2026-09-20**

## Purpose

Tier 2 previously duplicated inventory, dependency and readiness facts across several manifests, validators and workflow-specific files. That made it possible for a historical validator or incomplete discovery view to become stale even when package evidence itself was valid.

The automation foundation establishes one planning authority:

`manifests/kde-frameworks-tier2.json`

Historical attempt ledgers and evidence remain immutable records. Generated/current planning views must instead be derived from the canonical manifest.

## Gates

For a non-PASS node, the intended order is:

`upstream discovery -> provider audit -> package contract -> build attempt -> evidence -> PASS/FAIL`

A compatibility architecture decision may stop the node before provider audit. That is the current KMime state under ADR-0002.

A node with an unresolved provider audit is **pending**, not FAIL and not BLOCKED.

## Campaign compiler

`scripts/compile_kde_tier2_campaign.py` derives:

`manifests/kde-tier2-campaign-plan.json`

The generated plan contains:

- the canonical PASS/pending/FAIL/BLOCKED snapshot;
- retained PASS nodes;
- nodes requiring provider audit;
- nodes ready for package-contract materialization;
- human-decision-gated nodes;
- nodes with a materialized contract that may enter the build queue;
- a deterministic provider-audit queue.

Repository Policy runs the compiler with `--check`. Any hand-edited or stale plan fails CI.

To intentionally regenerate after changing canonical planning data:

```bash
python3 scripts/compile_kde_tier2_campaign.py --write
python3 scripts/compile_kde_tier2_campaign.py --check
```

## Consistency gate

`scripts/validate_kde_tier2_consistency.py` compares current derived views against the canonical manifest. It checks node coverage, Framework dependency edges, upstream tag/commit/CMake metadata, discovery readiness/predecessors and the global state snapshot.

The validator intentionally does not embed a second copy of Tier 2 source hashes or dependency tables.

## Current generated state

- retained PASS: KAuth;
- provider audit required before materialization: 13 nodes;
- human decision required: KMime / ADR-0002;
- package-contract-ready: none;
- build queue: none.

The first deterministic provider-audit batch is KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. This ordering is an audit scheduling heuristic, not a claim that those packages are already build-ready.

## Publication policy

PASS may make a package eligible for the SupraLINUX `testing` channel. Promotion to `stable` is never automatic and requires explicit user approval after manual testing.
