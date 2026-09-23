# KDE Frameworks 6.30 — Tier 3 discovery

Status: **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**

Last reviewed: **2026-09-22**

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
