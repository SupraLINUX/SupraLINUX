# KDE Frameworks 6.30 — Tier 3 discovery

Status: **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**

Last reviewed: **2026-09-22**

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
