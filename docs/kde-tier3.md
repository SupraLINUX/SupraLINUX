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

This distinction matters. For example, KNotifyConfig needs KXMLGui for its test executable but not for the library build, while KIO's password server treats KWallet as optional in source and KDE's Linux CI explicitly selects it.

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
