# KDE Frameworks Tier 3 build campaign

Status: **planned; execution not authorized** as of 2026-09-22.

This document defines how the 20 materialized Tier 3 Frameworks will be built without changing the project-wide PASS / FAIL / BLOCKED semantics.

## Authority and inputs

KDE upstream 6.30.0 remains the authority for dependency semantics and build/test ordering. Ubuntu 26.04 Resolute remains the platform/provider baseline. The campaign plan is generated from the canonical Tier 3 inventory, KDE-upstream dependency manifest, promoted materialization evidence, package contracts, canonical PASS DAG and the already-closed Tier 3 support sub-DAG.

The generated manifest is `manifests/kde-tier3-build-campaign.json`. It is intentionally immutable topology/evidence data. It has `execution_authorized=false`; actual package execution is authorized only by separate per-level manifests.

## Topology

The build-and-test levels are **12 / 2 / 4 / 2**:

1. Level 0: KBookmarks, KConfigWidgets, KDAV, KDESu, KIconThemes, KJobWidgets, KNewStuff, KPeople, KRunner, KSvg, KTextWidgets, KWallet.
2. Level 1: KIO, KXMLGui.
3. Level 2: Baloo, KCMUtils, KNotifyConfig, KParts.
4. Level 3: KTextEditor, Purpose.

Every Tier 3 blocking edge must point to an earlier level. All external KDE predecessors are already real SupraLINUX PASS artifacts and are pinned by version, workflow run, artifact ID and artifact SHA-256. Extra CMake Modules 6.30.0 is pinned separately as the shared build-system predecessor.

The support preconditions are also pinned:

- KIconThemes consumes the Breeze Icons PASS artifact.
- KIO's CI/documentation profile consumes the KDocTools PASS artifact.
- KIO runtime validation consumes the KDED PASS artifact.

## Execution semantics

The campaign follows the project hybrid DAG rules exactly:

- **PASS** means a package was really built and all required gates for that node completed successfully.
- **FAIL** means that node was actually attempted and failed for its own cause.
- **BLOCKED** means the node is not attempted because at least one required Tier 3 predecessor is FAIL/not PASS.
- An unrelated FAIL never stops independent nodes in the same level.
- A later level consumes only promoted PASS artifacts from earlier levels.
- Upstream tests are fatal; a build cannot be promoted by suppressing a failing KDE test.
- Materialization PASS is not package PASS.
- Per-level execution requires a separate authorization manifest.
- PASS packages may become eligible for testing, but promotion to the SupraLINUX `stable` repository is never automatic and requires explicit user approval.

## Deferred runtime validation

KNewStuff is a deliberate exception to the normal success transition. It can compile in Level 0 because KCMUtils is not a source-build predecessor. KDE's selected runtime environment, however, requires KCMUtils.

Therefore a successful KNewStuff Level 0 build does **not** immediately become canonical PASS. It remains pending with runtime validation required. After KCMUtils becomes PASS in Level 2, the dedicated runtime-validation gate must consume the promoted KNewStuff and KCMUtils artifacts. Only that gate can promote KNewStuff to PASS.

This dependency is recorded as `knewstuff -> kcmutils` under `deferred_runtime_validation`, not as a false build edge.

## Planning gate

Repository Policy checks both:

- `python3 scripts/compile_kde_tier3_build_campaign.py --check`
- `python3 scripts/validate_kde_tier3_build_campaign.py`

Until those checks pass and Level 0 receives its own execution manifest, the canonical Tier 3 package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** and no Tier 3 binary build is authorized.
