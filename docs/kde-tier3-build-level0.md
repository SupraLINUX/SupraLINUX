# KDE Frameworks Tier 3 — build Level 0

Status: **attempt 2 complete — remediation round 2 selective materialization pending** as of 2026-09-22.

Level 0 is the first real binary-build campaign for the 20 canonical Tier 3 Frameworks. It contains **12 independent nodes**:

- KBookmarks
- KConfigWidgets
- KDAV
- KDESu
- KIconThemes
- KJobWidgets
- KNewStuff
- KPeople
- KRunner
- KSvg
- KTextWidgets
- KWallet

The build topology comes from the validated `manifests/kde-tier3-build-campaign.json`. Level 0 execution is controlled separately by `manifests/kde-tier3-build-level0.json`. After attempt 1, Level 0 is deliberately paused (`execution_authorized=false`) while five source packages are rematerialized; Levels 1–3 remain unauthorized.

## Build environment and retained inputs

All nodes build on Ubuntu 26.04 Resolute using one shared clean `mmdebstrap --variant=buildd` rootfs for the workflow run. Each matrix job independently downloads only the prior SupraLINUX artifacts it needs.

Every retained artifact is pinned by GitHub artifact ID and SHA-256. The runner verifies the outer artifact digest, exact binary-package set and exact package version before making it available to sbuild. Direct build predecessors must also appear at their exact version in the resulting `.buildinfo`.

KIconThemes additionally consumes the already-PASS **Breeze Icons** support artifact because KDE upstream selects Breeze Icons in its default Linux build profile.

## PASS / FAIL / BLOCKED

The campaign preserves the project DAG semantics:

- **PASS**: the node was really built and all required gates completed successfully.
- **FAIL**: the node was really attempted and failed for a node-owned cause.
- **BLOCKED**: the node is not attempted because a required predecessor failed. Level 0 has no Tier 3 predecessors, so no Level 0 node starts BLOCKED.
- A failure in one Level 0 node does not stop the other independent nodes; the workflow uses `fail-fast=false`.

Failures before sbuild are classified as infrastructure/input failures rather than package FAIL. The package attempt begins immediately before sbuild.

## Required gates

A normal Level 0 PASS requires:

- clean sbuild against the shared Resolute buildd rootfs;
- a positive, non-zero upstream CTest summary;
- exact expected binary package names and package version;
- selected KDE profile flags proven in the build log;
- exact direct predecessor versions proven in `.buildinfo`;
- Lintian with errors fatal;
- ELF SONAME `.so.6` plus non-empty exported symbols for every versioned runtime library package;
- APT runtime closure and `apt-get check`;
- installed CMake package-config consumer discovery from the built development package;
- QML `qmldir` payload validation where a QML binary is declared;
- Python import validation where upstream Python bindings are declared.

KJobWidgets specifically requires `BUILD_PYTHON_BINDINGS=ON`, exact `python3-kcoreaddons` build-provider proof and `import KJobWidgets`.

KDESu specifically requires the documented Ubuntu-family integration profile `KDESU_USE_SUDO_DEFAULT=ON`.

## KNewStuff deferred runtime gate

KNewStuff is intentionally special. It can compile at Level 0 without KCMUtils, but KDE's runtime-validation contract requires KCMUtils.

A successful KNewStuff build therefore records `RUNTIME_PENDING`, not canonical PASS, and remains `downstream_eligible=false`. After KCMUtils becomes PASS in Level 2, a dedicated KNewStuff/KCMUtils runtime-validation gate must close before KNewStuff can be promoted to PASS.

This keeps runtime semantics accurate without inventing a false KNewStuff → KCMUtils build edge.

## Repository policy

The canonical Tier 3 package snapshot remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** until real Level 0 evidence is reviewed and promoted. No Level 1 node may consume a Level 0 package until that predecessor is promoted as PASS.

PASS packages can later be published to the SupraLINUX `testing` repository under the project publication workflow. Promotion to `stable` is never automatic and always requires explicit user approval.


## Attempt 1 — retained partial campaign

Workflow run `35755924197` executed all 12 Level 0 nodes against the same clean Resolute rootfs (rootfs SHA-256 `9966d46bef42083aeecd9016cb002b64fc23d60fae3098a8849b70e977873f68`). Repository Policy passed. The matrix finished with **7 successful workflow jobs / 5 FAIL** and no canonical promotion.

The successful build evidence is retained for KBookmarks (2/2 tests), KConfigWidgets (8/8), KDESu (3/3), KPeople (4/4), KSvg (5/5) and KTextWidgets (6/6). KNewStuff also completed its binary build with 5/5 tests, but correctly recorded `RUNTIME_PENDING` and `downstream_eligible=false` because KCMUtils has not yet passed its later Level 2 gate.

The five real FAIL causes are:

- **KIconThemes**: Debian's 6.30 packaging introduced `libkf6configwidgets-dev` as both a mandatory Build-Depends and a public `libkf6iconthemes-dev` dependency, although KDE upstream 6.30 neither requires nor exports KConfigWidgets. Its retained package-provider closure also lacked KCoreAddons needed by the selected 6.30 KGuiAddons package, and Debian rules excluded two upstream tests. Remediation removes the false edge, completes the package-provider closure and restores the full upstream tests.
- **KDAV**: Debian's `kio6` / `libkf6kio-dev` test-provider Build-Depends created a false KDAV → KIO build edge. KDE upstream 6.30 CMake/autotests require CoreAddons and I18n, not KIO. Those relations are removed.
- **KWallet**: Debian made `libkf6doctools-dev` mandatory, while KDE upstream uses a non-`REQUIRED` KDocTools lookup only for optional documentation. The mandatory packaging relation is removed.
- **KJobWidgets**: upstream `BUILD_PYTHON_BINDINGS=ON` reached `ECMGeneratePythonBindings`, which requires the Python `build` module. Resolute's `python3-build` is added as the provider.
- **KRunner**: compilation and 8/8 executed tests passed, then `dpkg-gensymbols` rejected two libstdc++ shared_ptr template implementation symbols that disappeared on Resolute amd64. Only those two entries become `optional=templinst`, preserving their existing architecture tag. Debian's separate `skip-flaky-test.patch`, which injected `QSKIP()`, is reversed and removed so the next campaign executes the upstream test rather than suppressing it.

Because these are packaging/source-package changes, the affected five revisions advance to **`6.30.0-0supralinux2`**. Their source materialization is rerun selectively; the other 15 Tier 3 materializations remain retained. Once the five new materialization artifacts pass and are promoted, the complete 12-node Level 0 campaign is rerun, including the seven nodes that already produced successful attempt-1 evidence.

Canonical Tier 3 package state therefore remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED** while remediation is in progress. Historical attempt FAILs remain evidence; they are not converted into BLOCKED or erased.

No package is promoted to `stable`; stable promotion always requires explicit user approval.


## Remediation materialization PASS

Selective materialization run `35759443440` completed **5/5 SUCCESS** from commit `0c23204d90b8a40ebf078ba41667c2292673ea81`. It produced new `6.30.0-0supralinux2` source artifacts for KIconThemes, KDAV, KWallet, KRunner and KJobWidgets. The other 15 Tier 3 source materializations remain unchanged.

The five promoted materialization pins are now the inputs of the generated build campaign and Level 0 manifest. This promotion has `package_attempted=false` and does not change canonical package PASS state.

Level 0 remains deliberately paused while this promotion commit is validated by Repository Policy. After that validation succeeds, a separate activation commit will set `execution_authorized=true` and rerun **all 12 Level 0 nodes**, not only the five remediated packages.


## Level 0 attempt 2 activated

Promotion validation passed in Repository Policy run `35769883615`. Level 0 is therefore reactivated as **attempt 2** with `execution_authorized=true`.

All 12 Level 0 nodes run again. The five remediated nodes consume their promoted `6.30.0-0supralinux2` source artifacts; the seven nodes that succeeded in attempt 1 are intentionally rebuilt as full-campaign revalidation rather than being silently carried forward.

The DAG semantics are unchanged: independent jobs continue after unrelated FAILs, KNewStuff still transitions only to `RUNTIME_PENDING` on build success, and no result is promoted until attempt 2 evidence is reviewed.


## Attempt 2 — 9 SUCCESS / 3 FAIL

Workflow run `35770505868` completed all 12 Level 0 jobs. No result is promoted yet.

Attempt 2 successfully revalidated KBookmarks, KConfigWidgets, KDESu, KPeople, KSvg and KTextWidgets; KNewStuff again completed its build but remains `RUNTIME_PENDING`. It also proved that the round-1 corrections for **KDAV** and **KRunner** are valid: both now build successfully at `6.30.0-0supralinux2`.

Three real package FAILs remain:

- **KIconThemes**: the full upstream test suite is now running. `kiconloader_unittest` and `kiconengine_unittest` fail specifically on SVG image loading/rendering. Resolute splits the QImage SVG format handler into `qt6-svg-plugins`; round 2 adds it as a nocheck test-environment provider. No test is disabled or ignored.
- **KJobWidgets**: `python3-build` launches the wheel build, but the selected legacy setuptools backend cannot be imported. Round 2 adds `python3-setuptools` while keeping `BUILD_PYTHON_BINDINGS=ON`.
- **KWallet**: build and **3/3 upstream tests PASS**. Packaging then fails because `usr/share/man/man1/kwallet-query.1` is absent. Round 2 uses the already-PASS KDocTools 6.30 artifact as the optional documentation provider required by the selected payload. This is a provider relationship, not a KDE Tier 3 build edge.

These three packages advance to `6.30.0-0supralinux3`. Level 0 is paused with `execution_authorized=false` while only those three source packages are rematerialized. A successful round-2 materialization will be promoted and validated before a complete **attempt 3** reruns all 12 Level 0 nodes.

The canonical package snapshot remains **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**. Historical FAIL evidence is retained in the attempt ledger.
