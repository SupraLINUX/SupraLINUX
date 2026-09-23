# KDE Frameworks Tier 3 build campaign

Status: **validated topology; Level 0 attempt 4 active** as of 2026-09-22.

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

Both planning checks passed in Repository Policy before Level 0 activation. The immutable plan itself remains `execution_authorized=false`; `manifests/kde-tier3-build-level0.json` is the separate execution authority for the 12 Level 0 nodes. Levels 1–3 remain unauthorized. Before Level 0 results are promoted, canonical Tier 3 package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.


## Remediation-plan stability

Level 0 attempt 1 exposed five source-package adaptations. While their selective rematerialization is pending, the generated campaign plan intentionally continues to validate against the **last promoted materialization PASS**. This preserves the validated 12 / 2 / 4 / 2 topology and previous artifact evidence without pretending that unbuilt remediation artifacts already exist.

After the five `6.30.0-0supralinux2` materializations pass, the generated plan is refreshed with their real artifact IDs/digests before Level 0 is reauthorized. The per-level execution manifest remains the only build authority.


The five remediated Level 0 nodes now point to the real source artifacts from materialization run `35759443440` at revision `6.30.0-0supralinux2`. The 12 / 2 / 4 / 2 topology is unchanged. Level 0 is still not authorized in this promotion step; reactivation is a separate gate after Repository Policy confirms the refreshed pins.


Repository Policy run `35769883615` validated the promoted remediation artifacts and refreshed campaign pins. The separate Level 0 authority now starts attempt 2 as a complete 12-node rerun; the immutable 12 / 2 / 4 / 2 topology remains unchanged.


## After Level 0 attempt 2

The 12 / 2 / 4 / 2 KDE-upstream topology is unchanged. Attempt 2 passed nine workflow jobs and left three package-owned failures. Because all three fixes modify source-package contracts, Level 0 is paused while KIconThemes, KJobWidgets and KWallet are selectively rematerialized as `-0supralinux3`.

The global plan continues to reference each node's last promoted materialization while that selective source work is pending. After the three new artifacts pass, their exact IDs/digests replace the old pins, Repository Policy validates the promotion, and a separate activation starts full Level 0 attempt 3.


## Round 2 promoted pins

The campaign now points KIconThemes, KJobWidgets and KWallet to the real `6.30.0-0supralinux3` source artifacts from materialization run `35806738003`. The other 17 materialization pins are unchanged.

The 12 / 2 / 4 / 2 topology and all dependency semantics remain unchanged. Level 0 is still paused in this promotion commit; activation is a separate validated transition.


## Attempt 3 activation

Repository Policy run `35807934729` validated the refreshed `-0supralinux3` pins. The 12 / 2 / 4 / 2 topology is unchanged; only Level 0 is authorized, as a complete 12-node attempt 3. Later levels remain gated.


## Attempt 3 closure

The corrected full 12-node run `35808764577` closed **10 workflow SUCCESS / 2 FAIL**. The topology remains 12 / 2 / 4 / 2 and no result is promoted yet.

Round 3 does not alter the KDE DAG. KJobWidgets has one source-package metadata remediation and must be selectively rematerialized; KWallet has only a retained provider-closure correction. After that gate, Level 0 must rerun all 12 nodes before any Level 1 authorization.


## Round 3 promoted inputs

The generated campaign now pins KJobWidgets to `6.30.0-0supralinux4` materialization run `35812918054`. KWallet remains on its `6.30.0-0supralinux3` source artifact while its separate Level 0 provider closure includes KArchive.

The 12 / 2 / 4 / 2 topology remains unchanged. Attempt 4 is not active in this promotion commit; Levels 1–3 remain gated.


## Attempt 4 activation

Repository Policy run `35813396247` validated the round-3 promoted inputs. Level 0 is authorized as a complete 12-node attempt 4 with `fail-fast=false`; the 12 / 2 / 4 / 2 topology is unchanged and later levels remain unauthorized.
