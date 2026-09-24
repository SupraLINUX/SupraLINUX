# KDE Frameworks 6.30 — Tier 3 discovery

Status: **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED — round 10 source PASS; Attempt 6 planning gates PASS; activation paused**

Last reviewed: **2026-09-24**

> Historical note: this document records the gate-by-gate progression of Tier 3. Earlier sections describe the state that was current at that point; the final **Current canonical state** section is authoritative for the present gate.

## Authority and precondition

KDE upstream is the authority for the Frameworks inventory, release version and dependency graph. Ubuntu 26.04 is the platform/provider and compatibility target; Ubuntu packaging does not select or limit the KDE Frameworks version.

Tier 3 begins only after canonical Tier 2 closed at **15 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

Upstream references:

- tier classification: `https://api.kde.org/`;
- selected stable release: `https://kde.org/info/kde-frameworks-6.30.0/`;
- selected Frameworks release: **6.30.0**.

KDE defines Tier 3 as Frameworks that may depend on Tier 1, Tier 2 and other Tier 3 Frameworks. This makes global dependency discovery mandatory before any packaging order is selected.

## Verified source inventory

The current upstream Tier 3 inventory contains exactly 20 Frameworks:

- Baloo
- KBookmarks
- KCMUtils
- KConfigWidgets
- KDAV
- KDESu
- KIconThemes
- KIO
- KJobWidgets
- KNewStuff
- KNotifyConfig
- KParts
- KPeople
- KRunner
- KSvg
- KTextEditor
- KTextWidgets
- KWallet
- KXMLGui
- Purpose

`manifests/kde-frameworks-tier3.json` records each KDE 6.30.0 release tarball and the SHA-256 published on the official KDE release-info page.

## Current lifecycle

All 20 nodes are canonical `pending` with readiness:

`dependency-graph-ready`

At this stage:

- no Ubuntu/Debian package version has been selected as authority;
- no SupraLINUX package revision is authorized;
- no provider audit is authorized;
- no package contract/materialization/build is authorized;
- no Tier 3 node is downstream-eligible;
- no pending Tier 3 node is inserted into the canonical PASS DAG.

The global KDE-upstream dependency discovery is now complete and recorded in `manifests/kde-frameworks-tier3-dependencies.json`. Provider/profile audit is the next gate; package contracts and builds remain unauthorized until that audit is complete.

The project rule remains: **KDE decides what KDE needs.**

PASS will make future packages eligible for `testing` only. Promotion to `stable` always requires explicit user approval.


## Tier 3 dependency graph — 2026-09-22

The dependency graph was derived from each framework's upstream `v6.30.0` tag, using the root `CMakeLists.txt`, `.kde-ci.yml`, and targeted nested CMake files where CI/source semantics differed.

The graph keeps separate edge classes:
- source-required build dependencies;
- default Linux profile selections;
- required QML modules;
- test-only dependencies;
- runtime-validation dependencies;
- CI-environment requirements.

This distinction matters. For example, KNotifyConfig needs KConfigWidgets and KXMLGui for its test executable but not for the library build, while KIO's password server treats KWallet as optional in source and KDE's Linux CI explicitly selects it.

The resulting build+test graph is acyclic with **4 topological levels**:

1. KBookmarks, KConfigWidgets, KDAV, KDESu, KIconThemes, KJobWidgets, KNewStuff, KPeople, KRunner, KSvg, KTextWidgets, KWallet.
2. KIO, KXMLGui.
3. Baloo, KCMUtils, KNotifyConfig, KParts.
4. KTextEditor, Purpose.

KNewStuff can compile at level 1, but its KDE CI runtime dependency on KCMUtils is retained as a deferred runtime-validation gate rather than a false build edge.

## Non-tiered Frameworks support components

Three KDE Frameworks 6.30 components required by the selected upstream profiles are outside the API tier lists and are therefore modeled explicitly instead of being assigned an invented tier:

- **Breeze Icons 6.30.0** — selected build predecessor of KIconThemes because upstream defaults `USE_BreezeIcons=ON`; also present in KTextEditor's CI environment.
- **KDocTools 6.30.0** — CI/documentation predecessor for KIO and KDED; KIO can compile without documentation, so this is not an ABI edge.
- **KDED 6.30.0** — runtime predecessor for KIO proxy management and cookie storage; it does not block KIO compilation.

These components remain KDE-upstream authority. Ubuntu may satisfy a provider audit only if its packages meet the exact 6.30 contracts; otherwise SupraLINUX will package them.

Current Tier 3 canonical state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. All nodes are `dependency-graph-ready`, while package contracts remain unauthorized. The next gate is provider audit, starting with Breeze Icons, KDocTools and KDED.


## Support provider audit activated

The next gate is now implemented as `manifests/kde-tier3-support-provider-audit.json` plus a hosted Ubuntu 26.04 workflow.

It audits Breeze Icons, KDocTools and KDED without treating Ubuntu as KDE authority. The runner compares the actual Resolute candidate upstream version with the selected KDE 6.30.0 contract, while separately proving Qt/XML/DocBook/Python platform providers.

The provider audit has `package_state_effect=none`: success selects who must provide each support component but does not make any support component or Tier 3 node PASS. Semantic scope prevents evidence-only changes from rerunning the audit.


## Support provider audit PASS

Run `35696178617` proved that Resolute carries Breeze Icons, KDocTools and KDED at `6.24.0-0ubuntu1`, below the selected KDE Frameworks `6.30.0` contract. All three support components therefore select **SupraLINUX** as provider.

The audit itself changes no package state. The three support components remain pending and advance to `package-contract-required`. Tier 3 remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.


## Support package-contract reference capture activated

The provider decision is closed. The active gate now captures signed Ubuntu Resolute and Debian sid source metadata for Breeze Icons, KDocTools and KDED.

This capture is deliberately non-authoritative and has `package_state_effect=none`. It must finish before explicit SupraLINUX package contracts are reviewed or any support-component materialization/build is authorized.


## Support contracts ready

The exact Ubuntu/Debian packaging-tree comparison is complete and the three support contracts are now fixed.

Breeze Icons uses the current primary `breeze-icon-theme*` packages plus Ubuntu-name transitionals, with epoch `4:` retained for correct historical upgrade ordering. KDocTools and KDED preserve their Ubuntu-visible binary identities.

The active gate is now **support materialization**. No Tier 3 node or support package is PASS yet; Tier 3 remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.


## Support materialization activated

Breeze Icons, KDocTools and KDED now have finalized package contracts and enter source materialization in parallel.

The materializer verifies the exact KDE 6.30 orig tar and pinned Debian 6.30 packaging tree, then applies only Resolute/SupraLINUX packaging metadata adaptations. Binary package builds remain blocked until all three materialization artifacts are promoted.


## Support materialization PASS

Breeze Icons, KDocTools and KDED source materialization completed successfully in run `35698463205`. Each artifact preserves the KDE 6.30 authoritative source hash and contains a Resolute-adapted source package; this phase did not build binary packages and therefore changed no package state.

The active gate is now **support build level 0**: Breeze Icons and KDocTools may build independently. KDED remains deferred until KDocTools has a real PASS artifact that can feed its build.


## Support build level 0 activated

The first real support-package build campaign is now active.

Breeze Icons and KDocTools are independent level-0 nodes and build in parallel from their promoted materialized source packages. The workflow injects only pinned downstream-eligible SupraLINUX KDE 6.30 predecessors and validates their exact versions/hashes before sbuild.

KDED is explicitly **BLOCKED** by KDocTools at this stage. It is not attempted and is not counted as FAIL.


## Support build level 0 PASS

Run `35700002095` produced real downstream-eligible PASS artifacts for both level-0 support nodes:

- Breeze Icons `4:6.30.0-0supralinux1`: 4/4 tests PASS, Lintian/apt/consumer/payload/ABI gates PASS.
- KDocTools `6.30.0-0supralinux1`: 3/3 tests PASS, Lintian/apt/consumer/payload/ABI gates PASS, with KArchive and KI18n SupraLINUX 6.30 proven in buildinfo.

The support sub-DAG is now **2 PASS / 1 pending / 0 current FAIL / 0 BLOCKED**. KDED is no longer blocked and becomes the sole runnable node in support build level 1.

The canonical Tier 3 Framework inventory itself remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.


## Support build level 1 activated

KDED is now the sole runnable support node. Its build consumes the real PASS KDocTools artifact from level 0 plus pinned KConfig, KCoreAddons, KCrash, KDBusAddons and KService artifacts; KArchive and KI18n remain explicitly modeled as package-install closure rather than invented direct KDED edges.

Because upstream KDED exports no Framework library, this gate validates its executable, DBus/systemd payload and CMake config instead of fabricating a SONAME contract.


## Support build level 1 — attempt 1 retained FAIL

KDED attempt 1 in run `35702647931` compiled successfully, but the post-build payload gate produced a false negative by checking for `kded6.8` instead of the Debian-installed compressed manpage `kded6.8.gz`.

The attempt is retained as historical FAIL at `payload-contract`. KDED remains pending in remediation, not PASS. No package revision is bumped because package contents are unchanged; only the CI validator is corrected.


## Support build level 1 — attempt 2 retained FAIL

KDED attempt 2 in run `35719952518` passed the corrected payload validation, Lintian and package-install closure, then failed only because `kded6 --version` tried to initialize Qt's `xcb` platform on a headless runner.

The executable smoke is remediated with `QT_QPA_PLATFORM=offscreen`. This is a CI-only execution environment fix, so KDED remains `6.30.0-0supralinux1`; the package payload is unchanged.


## Support build level 1 — attempt 3 retained FAIL

KDED attempt 3 passed sbuild, payload, Lintian, apt closure and the headless executable smoke. It failed only in the CMake consumer because that test used `project(... NONE)`, which suppresses the compiler/multiarch initialization needed for normal discovery under `/usr/lib/x86_64-linux-gnu/cmake`.

The built `kded6-dev` package does contain the correct `KF6KDEDConfig*.cmake` files. The consumer is corrected to enable CXX; package revision remains `6.30.0-0supralinux1`.


## Support build level 1 PASS — support sub-DAG closed

KDED attempt 4 in run `35721085911` completed all gates successfully at `6.30.0-0supralinux1`: 1/1 tests PASS, Lintian PASS-errors, apt closure PASS, executable/payload/CMake consumer PASS.

The support components are now **3 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**:
- Breeze Icons PASS;
- KDocTools PASS;
- KDED PASS.

The 20 canonical Tier 3 Frameworks remain **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. Their next gate is now the **Tier 3 framework provider audit**. Package contracts and package builds for those 20 nodes remain unauthorized until that audit is complete.


## Tier 3 framework provider audit activated

KDE Frameworks 6.30.0 remains the current stable upstream release and is the authority for all 20 Tier 3 versions. The hosted Ubuntu 26.04 audit now checks Resolute's actual `kf6-*` source candidates and records whether Ubuntu can provide the exact 6.30.0 Framework or SupraLINUX must provide it.

This gate has `package_state_effect=none`. All 20 Tier 3 Frameworks remain **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. Package contracts and package builds remain unauthorized until the provider audit is promoted.


## Tier 3 framework provider audit PASS

Run `35725458767` proved that all 20 canonical Tier 3 Frameworks require SupraLINUX as provider: Resolute exposes KDE upstream 6.24.0 while the selected KDE authority is 6.30.0. Ubuntu remains the Qt provider at 6.10.2.

All 20 Frameworks remain canonical pending; the provider decision itself changed no package state.

## Tier 3 package-contract reference PASS

Run `35726410174` captured signed Ubuntu Resolute and Debian sid source metadata for all 20 Frameworks. Debian provides an exact `6.30.0-1` technical reference for every node, and each Debian orig tar matches the KDE 6.30 authority source hash.

Ubuntu and Debian expose identical binary-package names for all 20 nodes. This is evidence for compatibility, not authority.

Canonical planning readiness is now `package-contract-reference-pass`. The next gate is **Tier 3 package-contract packaging-tree capture**. Binary builds remain unauthorized and the canonical state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.


## Tier 3 packaging-tree capture activated

Canonical planning readiness is now `package-contract-tree-pending`. The capture consumes the exact promoted Ubuntu/Debian source pins for all 20 Frameworks, verifies every `.dsc`, `debian.tar` and orig tar, then retains both `debian/` trees with deterministic hashes and parsed control summaries.

This is still contract evidence only. Tier 3 remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**, and package builds remain unauthorized.


## Tier 3 packaging-tree PASS

The exact Ubuntu Resolute and Debian sid `debian/` trees for all 20 Tier 3 Frameworks passed capture in run `35729077373` (artifact `10694324518`, index SHA-256 `3f975678343f872c8094b20425e76b4026a59d1c5f50c1d5b2c5c1b48a00c7fb`).

Canonical package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. Each node is now `package-contract-tree-pass`; the next gate is explicit package-contract review. Materialization and package builds remain unauthorized.


## Tier 3 contract review activated

All 20 nodes remain **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** and now carry readiness `package-contract-review-pending`.

The review compares the promoted Ubuntu/Debian packaging trees against KDE-upstream dependency semantics and records packaging deltas without granting either reference distribution authority. Materialization and package builds remain unauthorized.


## Tier 3 contract review PASS

The packaging-delta review passed in run `35730670337`. All 20 nodes retain identical Ubuntu/Debian binary package identities, but all 20 have at least one packaging delta requiring an explicit SupraLINUX decision.

Canonical readiness is now `package-contract-review-pass`. Tier 3 remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. The next gate is `tier3-package-contract-decision`; materialization and builds remain unauthorized.


## Tier 3 package contracts ready

The contract-review evidence has been converted into explicit SupraLINUX decisions. Canonical readiness is now `package-contract-ready` and package contract state is `not-materialized`.

Materialization is the active gate. Tier 3 remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**; no package build is authorized until source-package materialization completes.
## Current canonical state — Tier 3 `build-level0` attempt 3 active

Repository Policy run `35807934729` validated the promoted round-2 source pins. A separate activation now authorizes **Level 0 attempt 3** as a complete 12-node rerun.

KIconThemes, KJobWidgets and KWallet build from `6.30.0-0supralinux3`; the other nine Level 0 nodes rerun for revalidation from their already-promoted source artifacts. The campaign remains parallel with `fail-fast=false`.

Canonical package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** until attempt-3 evidence is reviewed. KNewStuff remains subject to the later KCMUtils runtime-validation gate.

Levels 1–3 remain unauthorized. Promotion to SupraLINUX `stable` always requires explicit user approval.


### Attempt 3 orchestration retry

The first two attempt-3 workflow launches (`35808224394` and `35808388332`) exposed an orchestration defect: the Level 0 planner omitted nodes in `prepared-pending-revalidation`, producing a 3-node matrix instead of the required 12-node full rerun. Those runs are retained as non-canonical orchestration evidence only. Planner/runner scope is corrected and the full 12-node attempt 3 must run before any package promotion.


## Current canonical state — Tier 3 `build-level0` round 3 remediation

The authoritative Level 0 attempt 3 is workflow run `35808764577` at commit `417444e60bd09887383fdc4ef5f1c1f3df1efc09`. The corrected campaign executed all 12 Level 0 nodes and closed **10 workflow SUCCESS / 2 FAIL**.

The two FAILs are KJobWidgets and KWallet. KJobWidgets compiled and passed **3/3** upstream tests but requires one symbols-template metadata correction, so only KJobWidgets advances to `6.30.0-0supralinux4` and rematerializes. KWallet keeps its already-materialized `6.30.0-0supralinux3` source; its correction is only to complete the KDocTools support-provider closure with the existing PASS KArchive artifact.

KIconThemes validated its round-2 SVG provider remediation with **10/10 tests PASS**. KNewStuff again has a successful binary build and **5/5 tests PASS**, but remains runtime-validation-pending on KCMUtils and is not downstream-eligible.

Canonical Tier 3 package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** because no Level 0 attempt has been promoted. The build gate is paused while the single-node KJobWidgets rematerialization runs. After promotion and Policy validation, Level 0 requires another complete 12-node rerun. Levels 1–3 remain unauthorized, and promotion to SupraLINUX `stable` still requires explicit user approval.


### Round 3 materialization promoted

KJobWidgets `6.30.0-0supralinux4` materialized PASS in workflow `35812918054` and is now pinned to artifact `10730956293` with SHA-256 `bcd505c1d4cbc65b45861335f41d8b03f18d53995bb9ba1d9036295bd5ce7804`.

KWallet remains on its already-promoted `6.30.0-0supralinux3` source and only gains the KArchive artifact in the KDocTools provider closure.

Canonical package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. Level 0 is paused until Repository Policy validates this promotion. Attempt 4, when separately activated, must rerun all 12 Level 0 nodes.


### Level 0 attempt 4 active

Repository Policy run `35813396247` validated the round-3 promotion commit `48abcd1ed74e8d83c9c256ddc491218e102d66cf`. A separate activation authorizes a complete **12-node Level 0 attempt 4**.

KJobWidgets builds from `6.30.0-0supralinux4`; KWallet remains `6.30.0-0supralinux3` with the KArchive-completed KDocTools provider closure. The other ten nodes rerun for full revalidation.

Canonical Tier 3 package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** until attempt-4 evidence is reviewed. Levels 1–3 remain unauthorized.


## Level 0 attempt 4 result — round 4 KWallet remediation

Workflow `35813710318` at commit `01bbc2b6df1621e17b2cdf6c65ebfb0f13063c79` executed the complete 12-node Level 0 matrix and closed **11 workflow SUCCESS / 1 FAIL**. KJobWidgets validates its round-3 symbols correction and is now a successful build result. KNewStuff again builds successfully but remains `RUNTIME_PENDING` on KCMUtils.

KWallet is the only remaining FAIL. Its KDocTools/KArchive provider closure is now proven: the build installs both providers, generates `kwallet-query.1`, passes `dh_install`, passes **3/3 upstream tests**, produces the binary packages and finishes sbuild successfully. The sole blocker is Lintian because `dpkg-gensymbols` observed `_ZSt19piecewise_construct@Base` in `libKF6WalletBackend.so.6` with the current Debian revision.

Round 4 therefore changes **only KWallet source packaging metadata**: candidate `6.30.0-0supralinux4`, with an `(optional)` symbols-template entry at minimum upstream version `6.30.0`. Only KWallet rematerializes. Canonical Tier 3 remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** and Levels 1–3 remain unauthorized.


### Round 4 KWallet materialization promoted

Selective materialization run `35817654811` produced KWallet `6.30.0-0supralinux4` PASS from commit `1a9a4ba82b4aac9f1df9f6457faef8b905dd17cf`. Artifact `10731134598` is pinned by SHA-256 `de215dfb5f86816dadccc630f23360bdc4c79a010aa6f7a0e2e99b1969bcf4ef`.

The artifact proves the intended `(optional)_ZSt19piecewise_construct@Base 6.30.0` template entry and preserves the KDocTools/KArchive provider closure. This is source-materialization evidence only; canonical package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**.

Level 0 stays paused until Repository Policy validates this promotion. Attempt 5, if separately activated after that gate, must rerun all 12 Level 0 nodes.


### Level 0 Attempt 5 active

Repository Policy run `35817928654` validates the round-4 KWallet source promotion at commit `3b1387b636a7103ca8918e51836ea7ac9e105be5`. A separate activation now authorizes a complete **12-node Level 0 Attempt 5**.

KWallet uses the promoted `6.30.0-0supralinux4` source artifact; the other eleven Level 0 nodes rerun for full revalidation. KNewStuff remains subject to its later KCMUtils runtime gate. Canonical Tier 3 package state remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** until the campaign evidence is reviewed.


## Level 0 Attempt 5 promotion — 11 PASS, KNewStuff runtime pending

Workflow `35818120201` at commit `0599266fd5fc9869002629b3778d71f1e76bbdc1` executed the complete 12-node Level 0 matrix with **12 workflow SUCCESS / 0 FAIL**.

Eleven nodes are now canonical **PASS** and downstream-eligible: KBookmarks, KConfigWidgets, KDAV, KDESu, KIconThemes, KJobWidgets, KPeople, KRunner, KSvg, KTextWidgets and KWallet. Their exact Attempt 5 artifacts and SHA-256 values are retained in the Level 0 ledger and canonical DAG.

KNewStuff also built successfully, passed **5/5 upstream tests**, Lintian, APT closure, ABI, CMake consumer and QML payload gates, but remains `runtime-validation-required` because its KDE runtime contract requires KCMUtils. It is therefore **not** promoted and cannot feed downstream nodes yet.

Canonical Tier 3 state is now **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**. Level 1 contains KIO and KXMLGui; neither depends on KNewStuff, so the next gate is **Tier 3 Level 1 planning**. Level 1 builds are not authorized by this promotion.


### Post-Level0 validator transition

After Level 0 Attempt 5 promotion, the canonical Tier 3 next gate is `tier3-build-level1-planning`. The retained support sub-DAG remains PASS and unchanged; its validators now explicitly accept this post-Level0 gate instead of incorrectly treating it as an invalid support lifecycle value.

This is a validator-lifecycle correction only. It changes no package evidence, dependency edge, PASS state, runtime-validation requirement, or publication status.


### Historical Tier 3 validators after Level 0

The provider-audit, packaging-tree, contract-review and generated build-campaign validators are evidence/lifecycle validators, not package-state owners. After Level 0 promotion they explicitly accept the canonical `build-level1-planning` phase and retained PASS/runtime-pending node states.

This prevents historical gates from falsely requiring the pre-build `pending` snapshot after real package PASS evidence has already been promoted. No provider decision, source hash, package contract, dependency edge or PASS evidence is changed by this validator correction.


## Level 1 preflight — KIO source remediation round 5

After Level 0 closed with 11 canonical PASS nodes, Level 1 planning compared the materialized KIO 6.30.0 source package against the KDE 6.30 upstream CMake contract before authorizing any binary build.

The Debian 6.30 technical baseline contains two Build-Depends that do not correspond to KIO 6.30 upstream dependencies: `libkf6auth-dev` and `libkf6configwidgets-dev`. SupraLINUX removes both. They are packaging-reference edges, not KDE dependency authority, and must not pull Ubuntu KF6 6.24 or create false Tier 3 DAG edges.

KIO upstream does use KArchive when the optional KDocTools/help-worker path is selected, and locates KDED as a runtime component. Those remain part of the selected SupraLINUX profile without turning KDED into a KDE build-DAG predecessor.

The reference `debian/rules` contains `ifneq (linux,$(DEB_HOST_ARCH_OS))` around `-DWITH_WAYLAND=ON`. KDE upstream already defaults Wayland integration ON on Linux; SupraLINUX corrects the conditional so the selected Linux profile is explicit and reproducibly provable.

The downstream `report_error_removing_dirs` patch changes KIO runtime behavior and has no explicit SupraLINUX integration requirement. It is reversed and removed so KIO follows KDE upstream stable behavior. Other technically scoped reference patches are retained.

These are source-packaging changes, so KIO advances to **`6.30.0-0supralinux2`** and only KIO is rematerialized. Level 1 binary execution remains unauthorized. Canonical package state stays **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**.


### KIO round 5 source PASS

Selective materialization run `35825070347` produced KIO `6.30.0-0supralinux2` PASS from commit `fbde9a53e357a138f4d74d7905230c7859e20444`. Artifact `10735250819` is pinned by SHA-256 `8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106`.

The artifact proves the two false Build-Depends are absent, the Linux Wayland conditional is effective, and only `report_error_removing_dirs` was removed from the reference patch series. KIO is still canonically pending because this is source evidence only. Level 1 binary execution remains unauthorized until Repository Policy validates the promotion and the Level 1 plan.


### Level 1 plan prepared

The formal Level 1 gate contains KIO and KXMLGui and is linked by `manifests/kde-tier3-build-level1.json`. Its initial state is `planned-pending-activation` with `execution_authorized=false`.

All Level 1 inputs are exact retained PASS artifacts. KIO consumes its round-5 source materialization plus KBookmarks, KIconThemes, KJobWidgets and KWallet; KDocTools remains a build/documentation provider and KDED a runtime-validation provider. KXMLGui consumes KConfigWidgets, KIconThemes and KTextWidgets plus its external PASS inputs.

Canonical package state remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED** until real Level 1 package evidence is produced and separately promoted.


### Level 1 Attempt 1 active

Repository Policy run `35826072726` validated the Level 1 plan. Canonical phase is now `build-level1` and exactly KIO plus KXMLGui are authorized for real binary Attempt 1.

The pre-build canonical package snapshot remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**. Any later PASS/FAIL transition must come from the real Level 1 build evidence; stable publication remains explicitly user-approved only.


### Level 1 Attempt 1 closure

Level 1 Attempt 1 run `35826694664` produced **0 SUCCESS / 2 FAIL / 0 BLOCKED**. KIO and KXMLGui both reached real sbuild execution and failed at dependency installation because the Level 1 retained-provider set lacked transitive 6.30 PASS artifacts.

This does not change the KDE-upstream DAG and does not require source rematerialization. Round 6 is provider-closure-only for KIO and KXMLGui; their revisions remain `6.30.0-0supralinux2` and `6.30.0-0supralinux1` respectively.

Canonical package PASS state remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**: the Attempt 1 FAILs are retained historical campaign evidence and are not promoted into canonical package state. Level 1 execution is paused pending closure validation.


## Current canonical state — Attempt 1 orchestration invalidated

Level 1 workflow `35826694664` produced two **raw GitHub job failures** after KIO and KXMLGui entered sbuild. Both stopped in `install-deps` before compilation because the Level 1 orchestrator did not provide the complete transitive package-provider closure needed to install already-PASS predecessor artifacts.

These raw failures are retained verbatim in the attempt ledger, but they are **not current canonical package FAILs**: SupraLINUX FAIL requires a node-owned cause. Canonical Tier 3 therefore remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED** with zero Attempt 1 promotions and zero source revisions changed.

The corrected provider closure is:
- KIO: KConfigWidgets, KArchive, KCodecs, KNotifications and Breeze Icons.
- KXMLGui: KArchive, KCodecs, KColorScheme, KCompletion, Sonnet and Breeze Icons.

Every closure entry is an already-PASS SupraLINUX artifact and has `kde_dependency_edge=false`. These providers make Debian package relations satisfiable but do not redefine the KDE-upstream DAG or the required `.buildinfo` predecessor set. Attempt 2 remains unauthorized until Repository Policy validates this remediation.


## Level 1 Attempt 2 active

Repository Policy run `35828634884` validated the complete round-6 provider closure and Level 1 workflow `35828634887` independently confirmed the remediation state with an intentional binary-build skip.

A separate activation now authorizes **Attempt 2** for KIO and KXMLGui. No source, package revision or KDE DAG edge changes: KIO remains `6.30.0-0supralinux2`, KXMLGui remains `6.30.0-0supralinux1`, and the complete consumer-specific provider closure is retained exactly as validated.

Canonical package state remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED** until the Attempt 2 artifacts are reviewed. Attempt 1 remains historical raw CI failure evidence classified canonically as `INVALIDATED-ORCHESTRATION`.


## Current canonical state — Level 1 round 7 source remediation

Level 1 Attempt 2 workflow `35829170695` completed with **0 workflow SUCCESS / 2 real node FAIL** after the round-6 provider closure allowed both packages to reach their own build logic.

KIO failed in its upstream CTest phase because the clean sbuild environment did not yet provide the complete test environment. KXMLGui failed in CMake because the enabled upstream Python bindings require the Python wheel build frontend/backend. Both FAIL records are retained in the Level 1 attempt ledger; no package PASS was promoted.

Round 7 therefore rematerializes exactly two source packages:
- KIO `6.30.0-0supralinux3`;
- KXMLGui `6.30.0-0supralinux2`.

Level 0 remains closed at **11 canonical PASS + KNewStuff runtime-validation-required** and is not reopened by this Level 1 remediation. Level 1 binary execution is paused until both round-7 source materializations PASS and their evidence is promoted and policy-validated.

Canonical package-state snapshot remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**; the two Attempt 2 FAILs remain explicit campaign evidence while their nodes are in remediation.


## Current canonical state — round 7 source PASS

Round-7 source materialization run `35882795135` completed **KIO + KXMLGui source PASS**. KIO is now `6.30.0-0supralinux3` pinned to artifact `10760324592`; KXMLGui is `6.30.0-0supralinux2` pinned to artifact `10761208629`.

This is not a binary package promotion. Canonical Tier 3 remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED** while the two real Attempt 2 FAIL records remain historical campaign evidence under active remediation.

Level 1 execution remains paused. Repository Policy must validate the refreshed materialization/campaign pins before a separate Attempt 3 activation can schedule KIO and KXMLGui.


## Current canonical state — Attempt 3 active

The round-7 KIO/KXMLGui source promotion passed its planning gates. Level 1 Attempt 3 is now authorized as a full two-node rerun using KIO `6.30.0-0supralinux3` and KXMLGui `6.30.0-0supralinux2`.

The pre-result canonical snapshot remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**. Attempt 2's two real FAIL records remain immutable campaign history under remediation; Attempt 3 will establish the next package-owned results.

Level 2 remains unauthorized until both Level 1 results are reviewed and promoted according to PASS / FAIL / BLOCKED semantics.

## Current canonical state — Attempt 3 closed / round 8 pending

Level 1 Attempt 3 workflow `35887558758` completed with **0 SUCCESS / 2 real FAIL**. KIO reached **62/69 upstream tests passing**; KXMLGui reached its test phase after the Python binding build fix and failed only on xcb display selection.

Round 8 is a selective source remediation for KIO `6.30.0-0supralinux4` and KXMLGui `6.30.0-0supralinux3`. Binary execution is paused while those sources rematerialize. No Level 2 work is authorized and no package is promoted by this transition.

Canonical package state remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**. Attempt 3 FAIL records remain immutable campaign evidence while the affected nodes are under remediation.

## Round 8 source materialization PASS

Round 8 source materialization workflow `35894317888` completed **2/2 PASS** at commit `65f5ba76a913e7acf619eb9fee86e878e2914415`. KIO `6.30.0-0supralinux4` and KXMLGui `6.30.0-0supralinux3` are now the retained source inputs for the next Level 1 attempt. This is source-only evidence and does not change the canonical package snapshot.

Level 1 remains paused. The next gate is `tier3-build-level1-planning-validation`; Attempt 4 is not authorized until Repository Policy and the Level 1 planner validate the promoted round-8 state.

## Current canonical state — Attempt 4 active

Round-8 source promotion and its generated campaign passed Repository Policy `35895610944` plus the paused Level 1 planner `35895610937` at commit `9f680b0d8790c7bc472e8352e6675d606f706ee7`. The forward-compatible Attempt 4 lifecycle then passed Repository Policy `35961362802` and Level 1 validation `35961362869`.

Attempt 4 is now separately authorized as a full two-node Level 1 rerun. KIO uses `6.30.0-0supralinux4`; KXMLGui uses `6.30.0-0supralinux3`. The pre-result canonical snapshot remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED** and Attempt 3's two FAIL records remain immutable campaign history.

Level 2 remains unauthorized until the new KIO/KXMLGui binary evidence is reviewed and promoted under PASS / FAIL / BLOCKED semantics.

## Current canonical state — Attempt 4 closed / round 9 pending

Level 1 Attempt 4 workflow `35961584503` completed **0 SUCCESS / 2 real FAIL**, with no canonical promotion. Both nodes used shared rootfs artifact `10792995587`, artifact SHA-256 `c9ed6500670e092f8fe6e0ec531857afb51c5587f9a56bef083af2267c268ce3`, inner rootfs SHA-256 `46fd06c2725ce8f10efba3c577da62f3a0dd5cb96e59683ca9fc988bed28c3a8`.

KIO improved to **67/69 upstream CTest targets PASS**. Only `kdirmodeltest` and `knewfilemenutest` remain; their first failures are empty `QIcon::fromTheme()` names. Round 9 keeps the proven D-Bus/HOME/KDECI/serial/network environment, replaces Qt offscreen with XCB under isolated Xvfb, and selects Breeze through `QT_QPA_SYSTEM_ICON_THEME=breeze`.

KXMLGui improved to **6/7 upstream test targets PASS**. Only `ktoolbar_unittest` remains; upstream performs its toolbar-style notification through the Qt D-Bus session bus. Round 9 keeps offscreen and the full `dh_auto_test` suite, adding only `dbus-daemon <!nocheck>` plus an isolated `dbus-run-session`.

Round 9 candidates are KIO `6.30.0-0supralinux5` and KXMLGui `6.30.0-0supralinux4`. Binary Level 1 execution is paused until both source materializations PASS and their evidence is validated. Level 2 remains unauthorized.

## Current canonical state — round 9 source PASS / Attempt 5 planning validation

Round 9 source materialization workflow `35965579279` completed **2/2 PASS** at commit `8380856c8161dccc9de9c12745012c555baa26b0`. KIO `6.30.0-0supralinux5` is artifact `10794251210` (SHA-256 `45eac20aca30ca6a5ef78d8a94d15ee5408a8bed39c8fa72c6c8823134ffa0b2`); KXMLGui `6.30.0-0supralinux4` is artifact `10793229286` (SHA-256 `44b9cf9d0ad12f06b12bda37c291fcda5ecf933e25cfdd61c42d9df6e11b0093`).

This is source-only evidence. Canonical package state remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**. Level 1 stays paused with `execution_authorized=false`; Attempt 5 is not authorized until Repository Policy and the Level 1 planner validate the refreshed round-9 source/campaign pins. Level 2 remains unauthorized.

## Current canonical state — Attempt 5 planning gates PASS / activation paused

The promoted round-9 source inputs and regenerated campaign passed Repository Policy `35990068378` and the paused Level 1 planner `35990068382` at commit `45675c1fb5a43f95204c2cf0c5c15df0ef703832`. The Level 1 workflow intentionally skipped the shared rootfs and both binary builds, so **Attempt 5 has not executed**.

Before changing execution authority, the validators are extended to recognize the future round-9 / Attempt-5 active lifecycle and to bind it to those exact planning-validation runs. This transition remains validator/documentation-only: canonical package state stays **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**, `execution_authorized=false`, and Level 2 remains unauthorized.

## Current canonical state — Attempt 5 active

Round-9 source promotion passed the planning gates at commit `45675c1fb5a43f95204c2cf0c5c15df0ef703832`: Repository Policy `35990068378` and paused Level 1 `35990068382`. The forward-compatible Attempt-5 lifecycle then passed Repository Policy `35990715536`, Level 1 `35990715990`, and materialization `35990715302` at commit `6ed2f38cdc0e092b6bf639a8a5b0b2461057784a`, with all package builds still skipped.

A separate activation now authorizes the complete two-node Level 1 Attempt 5. KIO uses `6.30.0-0supralinux5` artifact `10794251210`; KXMLGui uses `6.30.0-0supralinux4` artifact `10793229286`. The pre-result canonical snapshot remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**.

Level 2 remains unauthorized until Attempt 5 completes and its KIO/KXMLGui evidence is reviewed under PASS / FAIL / BLOCKED semantics. Binary PASS does not imply stable publication.

## Current canonical state — Attempt 5 closed / round 10 pending

Level 1 Attempt 5 workflow `35991007820` at commit `3197c1988e1ab86ec5010cb693064db949bfe6b0` completed **0 workflow SUCCESS / 2 real FAIL**, with no canonical promotion. Both nodes used shared rootfs artifact `10804620493`, artifact SHA-256 `0855a64addfe52eb38ae3f71b4e7a8c3c1a08c5351dfa677ba03e0933426ca21`, inner rootfs SHA-256 `ecc2df763b7dd14b8812bfebedecb1ff3c532dd970cb3f1f5b2973b750d9740c`.

KIO again reached **67/69 CTest PASS**. The decisive new evidence is that KDE 6.30 itself assigns `QT_QPA_PLATFORM=offscreen` in the CTest `ENVIRONMENT` property of `kiowidgets-kdirmodeltest` and `kiofilewidgets-knewfilemenutest`. That per-test property overrode round 9's outer `QT_QPA_PLATFORM=xcb`, so the intended XCB/Breeze environment never reached the two failing tests. Round 10 preserves all 69 tests and all proven test providers, but overrides only those two test properties to XCB/Breeze under the existing isolated Xvfb server.

KXMLGui compiled and passed **7/7 upstream CTest targets**; the round-9 D-Bus/offscreen remediation is therefore proven. Its job failed later on packaging evidence: `libkf6textwidgets-dev` is modeled as the upstream `test_required` predecessor but was not declared in Build-Depends, so it was absent from `Installed-Build-Depends`; additionally Resolute emitted the private template symbol `_ZSt19piecewise_construct@Base`, which dpkg-gensymbols versioned with the current Debian revision and Lintian rejected. Round 10 adds the test-only KTextWidgets Build-Depends and treats that symbol as optional at upstream version `6.30.0`, matching the already-proven KJobWidgets policy.

Round 10 candidates are KIO `6.30.0-0supralinux6` and KXMLGui `6.30.0-0supralinux5`. Binary Level 1 execution is paused until both rematerializations PASS and their evidence is validated. Level 2 remains unauthorized.

## Current canonical state — round 10 source PASS / Attempt 6 planning validation

Round 10 source materialization workflow `36002910277` completed **2/2 PASS** at commit `c0774e5514fd83995aad3c86e1f6a5b106b001a3`. KIO `6.30.0-0supralinux6` is artifact `10809231495` (SHA-256 `5a0c2db21af5a87d4bd5ee2b02ebff7bce4dd98c66622398f00c67ef7210227b`); KXMLGui `6.30.0-0supralinux5` is artifact `10808294092` (SHA-256 `bccf76b46d0c9619e4306f1fe704ff5b501b9554a63f7968093e3afd4beb0d86`).

This is source-only evidence. Canonical package state remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**. Level 1 remains paused with `execution_authorized=false`; Attempt 6 is not authorized until Repository Policy and the Level 1 planner validate the refreshed round-10 source/campaign pins. Level 2 remains unauthorized.

## Current canonical state — Attempt 6 planning gates PASS / activation paused

The promoted round-10 source inputs and regenerated campaign passed Repository Policy `36032425645` and the paused Level 1 planner `36032425729` at commit `0fee159ac1f24dc160e1edd9976a7708f89d657d`. The Level 1 workflow intentionally skipped the shared rootfs and both binary builds, so **Attempt 6 has not executed**.

Before changing execution authority, the validators are extended to recognize the future round-10 / Attempt-6 active lifecycle and to bind it to those exact planning-validation runs. This transition remains validator/documentation-only: canonical package state stays **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**, `execution_authorized=false`, and Level 2 remains unauthorized.
