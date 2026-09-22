# KDE Frameworks Tier 3 — build Level 0

Status: **active / pending CI** as of 2026-09-22.

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

The build topology and artifact inputs come from the validated immutable `manifests/kde-tier3-build-campaign.json`. Level 0 itself is authorized by `manifests/kde-tier3-build-level0.json`; later levels remain unauthorized.

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
