# KDE Frameworks Tier 3 build campaign

Status: **Level 0 closed; Level 1 Attempt 6 active with round-10 source pins** as of 2026-09-24.

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


## Level 1 preflight before activation

Level 0 Attempt 5 is closed: 11 nodes are canonical PASS and KNewStuff remains runtime-validation-required on KCMUtils. KIO and KXMLGui are topologically ready because all of their actual Tier 3 blocking predecessors are among those 11 PASS nodes.

Before Level 1 activation, KIO's materialized Debian baseline was compared again with KDE upstream 6.30. That review found two Debian-only false Framework Build-Depends plus one Linux-profile conditional and one behavior-changing downstream patch that must be corrected in the source package.

Only KIO is rematerialized as `6.30.0-0supralinux2`. The **12 / 2 / 4 / 2** topology is unchanged: no removed Debian relation becomes a KDE edge, and KArchive/KDocTools/KDED support semantics remain separate from the Tier 3 build topology. Level 1 execution remains unauthorized until the new KIO source artifact is promoted and Repository Policy validates the refreshed plan.


### Refreshed KIO source pin

The generated campaign now points KIO to `6.30.0-0supralinux2`, materialization run `35825070347`, artifact `10735250819`, SHA-256 `8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106`. Topology remains unchanged. Repository Policy must validate this refreshed source pin before the separate Level 1 plan can be activated.


## Level 1 planning gate prepared

Repository Policy run `35825677329` validated the promoted KIO round-5 source pin. The dedicated Level 1 definition now selects exactly KIO and KXMLGui, pins every external/Tier 3/support predecessor to an existing PASS artifact, and retains the KDE-upstream 12 / 2 / 4 / 2 topology unchanged.

The Level 1 manifest starts with `execution_authorized=false`. KIO uses the promoted `6.30.0-0supralinux2` source artifact; KXMLGui remains `6.30.0-0supralinux1`. KDED participates only in KIO runtime closure validation and is not promoted into the Tier 3 build DAG as a false build edge.

Repository Policy must validate this Level 1 plan before a separate activation commit can schedule either binary build.


### Level 1 Attempt 1 activation

The Level 1 plan passed Repository Policy run `35826072726`. A separate activation authorizes exactly KIO and KXMLGui as Attempt 1 and transitions the canonical phase to `build-level1`.

The validated topology and artifact pins are unchanged. Activation itself creates no package PASS state and performs no stable publication.


## Level 1 Attempt 1 provider-closure remediation

Attempt 1 run `35826694664` attempted both Level 1 nodes and both failed during sbuild dependency installation. The failures are independent real FAIL results, not BLOCKED nodes.

The source artifacts are unchanged. The remediation expands only the exact retained provider closure required by already-PASS 6.30 packages: KIO adds KArchive, KCodecs and KNotifications; KXMLGui adds KArchive, KCodecs, KColorScheme, KCompletion and Sonnet.

These closure artifacts do not create new KDE dependency edges and are not added to direct `.buildinfo` predecessor proof. The 12 / 2 / 4 / 2 topology remains unchanged. Attempt 2 requires a separate activation after Repository Policy validates the closure.


## Attempt 1 canonical classification correction

Run `35826694664` had 0 successful and 2 failed workflow jobs, but both failures share the same orchestration cause: incomplete provider closure during `install-deps`. The raw CI failures remain evidence; canonical package failure count is **0** because neither node reached a node-owned compile/test/package defect.

No source package is rematerialized and no revision is bumped. Attempt 2 will rerun both Level 1 nodes only after Policy validates the complete closure, including KConfigWidgets and Breeze Icons where required. Provider closure remains separate from KDE dependency authority and from direct `.buildinfo` proof.


## Level 1 Attempt 2 activation

Round 6 provider closure passed Repository Policy run `35828634884`; Level 1 workflow `35828634887` validated the paused remediation and scheduled zero package builds. Attempt 2 is now separately authorized as a full two-node rerun with `fail-fast=false`.

KIO and KXMLGui retain their existing source artifacts and revisions. The additional providers remain package-manager closure only and do not become KDE DAG edges or direct `.buildinfo` proof requirements.


## Round 7 refreshed Level 1 source pins

The generated campaign remains the same **12 / 2 / 4 / 2** KDE-upstream topology. Only the two Level 1 source-evidence pins changed after source-only run `35882795135`:

- KIO: `6.30.0-0supralinux3`, artifact `10760324592`, SHA-256 `b58b7a45f6df0c8f01e9bd9a37799c1470369124a7c1b48fecb82a5f7f86ae8d`;
- KXMLGui: `6.30.0-0supralinux2`, artifact `10761208629`, SHA-256 `72cd10276558264646a9e38d5beab7b231434338597ef8d276030e790ff02214`.

Campaign execution authority remains false. These refreshed pins must pass Repository Policy before the dedicated Level 1 manifest can separately authorize Attempt 3.


## Level 1 Attempt 3 activation

The refreshed KIO/KXMLGui source pins passed Repository Policy and the paused Level 1 planner. Attempt 3 is now separately authorized as a complete Level 1 rerun using the unchanged **12 / 2 / 4 / 2** KDE-upstream topology.

Both nodes are independent at this level and run with `fail-fast=false`. Any PASS/FAIL transition comes only from the new binary evidence; downstream Level 2 remains unauthorized until Level 1 is closed.

## Round 8 / Attempt 4 planning gate

The generated **12 / 2 / 4 / 2** campaign is synchronized to KIO `6.30.0-0supralinux4` artifact `10766471076` and KXMLGui `6.30.0-0supralinux3` artifact `10766665506`. Repository Policy `35895610944` and the paused Level 1 workflow `35895610937` both passed at commit `9f680b0d8790c7bc472e8352e6675d606f706ee7`.

Campaign topology and the generated campaign's `execution_authorized=false` remain unchanged. A separate Level 1 activation is required before Attempt 4 may build either node.

## Level 1 Attempt 4 activation

The generated campaign remains the validated **12 / 2 / 4 / 2** KDE-upstream topology and still has `execution_authorized=false`; execution authority is delegated only by the dedicated Level 1 manifest.

After round-8 source promotion passed Policy/planner validation (`35895610944` / `35895610937`) and the forward-compatible Attempt 4 lifecycle passed again (`35961362802` / `35961362869`), Level 1 is separately activated for KIO `6.30.0-0supralinux4` and KXMLGui `6.30.0-0supralinux3`.

## Round 9 source-remediation boundary

The generated **12 / 2 / 4 / 2** campaign is intentionally **not regenerated yet**. It continues to pin the promoted round-8 KIO/KXMLGui source artifacts while round 9 rematerialization is pending.

Only after KIO `6.30.0-0supralinux5` and KXMLGui `6.30.0-0supralinux4` both materialize PASS will the generated campaign be refreshed to those exact new artifacts and validated before Attempt 5 activation. Its own `execution_authorized=false` remains unchanged.

## Round 9 / Attempt 5 planning gate

The generated **12 / 2 / 4 / 2** campaign is now synchronized to KIO `6.30.0-0supralinux5` artifact `10794251210` and KXMLGui `6.30.0-0supralinux4` artifact `10793229286`, both from source-only materialization run `35965579279`.

Campaign topology is unchanged and its own `execution_authorized=false` remains unchanged. Repository Policy and the paused Level 1 planner must validate these exact pins before a separate Attempt 5 activation may schedule either binary build.

## Attempt 5 planning gate PASS / lifecycle pre-validation

The generated **12 / 2 / 4 / 2** campaign with KIO `6.30.0-0supralinux5` artifact `10794251210` and KXMLGui `6.30.0-0supralinux4` artifact `10793229286` passed Repository Policy `35990068378` and the paused Level 1 workflow `35990068382` at commit `45675c1fb5a43f95204c2cf0c5c15df0ef703832`.

Campaign `execution_authorized=false` is unchanged. Validators are extended first so a later, separate Level 1 activation can be checked against those exact planning gates without mixing validation and execution in one transition. Attempt 5 is still not running.

## Level 1 Attempt 5 activation

The generated campaign remains the validated **12 / 2 / 4 / 2** KDE-upstream topology and still has `execution_authorized=false`; execution authority is delegated only by `manifests/kde-tier3-build-level1.json`.

After round-9 source promotion passed Policy/planner validation (`35990068378` / `35990068382`) and the forward-compatible Attempt-5 lifecycle passed again (`35990715536` / `35990715990`, with materialization `35990715302` also PASS), Level 1 is separately activated for KIO `6.30.0-0supralinux5` and KXMLGui `6.30.0-0supralinux4`.

## Round 10 source-remediation boundary

The generated **12 / 2 / 4 / 2** campaign is intentionally **not regenerated yet**. It continues to pin the promoted round-9 KIO/KXMLGui source artifacts while round 10 materialization is pending.

Only after KIO `6.30.0-0supralinux6` and KXMLGui `6.30.0-0supralinux5` both materialize PASS will the generated campaign be refreshed to those exact new artifacts and validated before a separately authorized Attempt 6. The campaign's own `execution_authorized=false` remains unchanged.

## Round 10 / Attempt 6 planning gate

The generated **12 / 2 / 4 / 2** campaign is synchronized to the round-10 source materialization PASS from workflow `36002910277`: KIO `6.30.0-0supralinux6` artifact `10809231495` (SHA-256 `5a0c2db21af5a87d4bd5ee2b02ebff7bce4dd98c66622398f00c67ef7210227b`) and KXMLGui `6.30.0-0supralinux5` artifact `10808294092` (SHA-256 `bccf76b46d0c9619e4306f1fe704ff5b501b9554a63f7968093e3afd4beb0d86`).

Campaign topology is unchanged and `execution_authorized=false` remains authoritative. Repository Policy and the paused Level 1 planner must validate these exact pins before any Attempt 6 lifecycle pre-validation or activation. Source PASS is not binary PASS and does not authorize stable publication.

## Attempt 6 planning gate PASS / lifecycle pre-validation

The generated **12 / 2 / 4 / 2** campaign with KIO `6.30.0-0supralinux6` artifact `10809231495` and KXMLGui `6.30.0-0supralinux5` artifact `10808294092` passed Repository Policy `36032425645` and the paused Level 1 workflow `36032425729` at commit `0fee159ac1f24dc160e1edd9976a7708f89d657d`.

The Level 1 planner completed successfully, emitted the intentional skip report, and skipped both the shared rootfs and binary build matrix. Campaign `execution_authorized=false` remains unchanged. Validators are extended first so a later, separate Attempt 6 activation can be checked against those exact planning gates without mixing validation and execution.

## Level 1 Attempt 6 activation

The generated campaign remains the validated **12 / 2 / 4 / 2** KDE-upstream topology and still has `execution_authorized=false`; execution authority is delegated only by `manifests/kde-tier3-build-level1.json`.

Round-10 source promotion passed Policy/planner validation (`36032425645` / `36032425729`) at `0fee159ac1f24dc160e1edd9976a7708f89d657d`. The forward-compatible Attempt-6 lifecycle then passed Repository Policy `36033162764`, Level 1 `36033163019`, and materialization `36033162995` at `16d829174476a6f9846d53d14efc2dd21651332d`, with package builds still skipped.

A separate activation now authorizes exactly KIO `6.30.0-0supralinux6` and KXMLGui `6.30.0-0supralinux5` for the complete Level 1 Attempt 6.
