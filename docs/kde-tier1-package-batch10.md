# KDE Frameworks Tier 1 — Batch 10 QML/multisurface package campaign

Status: **implementation ready; package state not promoted**

As of 2026-09-18, KDE Frameworks 6.30.0 remains the selected upstream stable series. Batch 10 covers the remaining Tier 1 QML-heavy pair: Kirigami and KQuickCharts. Canonical Tier 1 before this campaign is **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**.

## Authority and provider model

KDE upstream defines source, defaults, Qt floor and framework behavior. Ubuntu 26.04 Resolute is a dependency provider only. Debian 6.28 packaging is retained strictly as a technical baseline for Debian-family package names, splits and symbol metadata.

Selected sources:

- Kirigami 6.30.0: SHA-256 `6de811e559c20dc1086c0cf2c34bb98712dbe4d45f960c62c3c3f887332c95f8`.
- KQuickCharts 6.30.0: SHA-256 `9fe8c0c78ffd23ccfb99cc36477550a229c114ad057def938f38cdec35f82ab1`.
- retained ECM predecessor: `6.30.0-0supralinux3`.

## Non-promoting source diagnostic evidence

Global source diagnostic run `35138333645` remains discovery evidence only:

- Kirigami: job `104936243949`, artifact `10464419377`, artifact SHA-256 `f83a7e508fa2031dcf5401a7590e9598ab3d5888230af60b153c4b77d4b53185`, `44/44 PASS`.
- KQuickCharts: job `104936243779`, artifact `10463808939`, artifact SHA-256 `5d1023d260fe167d846a8b3f16310c6771bb08f79688095bd27ba5ea79798a28`, `8/8 PASS`.

DIAG_PASS does not promote package state or make a node downstream-eligible.

## Retained technical references

- packaging trees: run `34708030450`, artifact `10301938362`, ZIP SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`, `snapshot.json` SHA-256 `f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345`;
- binary contracts: run `34704117024`, artifact `10301282501`, ZIP SHA-256 `9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97`, `binary-contracts.json` SHA-256 `e44507d0dd73db913a91bd4852c452f783618aab0bd6a3790e4c4f4c40707b7b`.

Active `.symbols` files are not committed. The runner materializes the retained hash-pinned Debian 6.28 baselines into the ephemeral source package and validates total, optional, non-applicable-amd64 and required-amd64 export counts before using the required amd64 floor.

## Package surfaces

Kirigami starts at `6.30.0-0supralinux1` with 19 binary packages, 15 runtime ABI libraries and one bundled QML package. Its 6.30 DIAG install surface is fully covered by the retained split manifests. QCH is OFF under the common SupraLINUX Frameworks profile. Upstream defaults are preserved: shared libraries ON, desktop ON, examples OFF, Ubuntu Touch OFF, DBus ON, tests ON.

KQuickCharts starts at `6.30.0-0supralinux1` with 4 binary packages, 2 runtime ABI libraries and one QML package. The retained split manifests also cover the full 6.30 DIAG install surface. Tests remain mandatory; the Debian architecture-specific `|| true` suppression is explicitly rejected.

## Kirigami / KQuickCharts dependency semantics

Both nodes have `kde_framework_build_dependencies=[]`. KQuickCharts 6.30 source DIAG built and tested without a Kirigami or KF6Declarative Framework build predecessor.

However, the packaged QuickCharts QML runtime imports `org.kde.kirigami`. Therefore full KQuickCharts **package validation** requires a retained/current SupraLINUX Kirigami PASS artifact. This is represented as a `package_validation_dependency` and must never be rewritten as a KDE Framework build edge.

Initial ordering is:

`Kirigami package PASS -> KQuickCharts full package validation`

If Kirigami is attempted and FAILs, KQuickCharts is not attempted and is recorded as BLOCKED. If Kirigami is already retained PASS and scope-skips, KQuickCharts downloads that retained artifact. KQuickCharts consumer/runtime closure must verify that `qml6-module-org-kde-kirigami` resolves to the exact SupraLINUX Kirigami campaign version rather than Ubuntu's KDE package.

## Runner gates

Batch 10 requires, per attempted node:

- exact KDE upstream tarball SHA-256;
- exact retained ECM PASS;
- clean Ubuntu 26.04 Resolute `sbuild` rootfs;
- exact source/binary package version and package split;
- mandatory upstream CTest count (`44/44` Kirigami, `8/8` KQuickCharts);
- Lintian error gate;
- all ABI SONAMEs and architecture-aware retained symbol floors;
- no unreviewed symbol acquiring a `0supralinux` minimum;
- dynamic enumeration of every packaged QML `qmldir` module plus `qmlimportscanner` resolution;
- exact local-package APT installation and `apt-get check`;
- CMake/C++ consumer smoke;
- for KQuickCharts, exact local Kirigami QML runtime provenance.

Kirigami's consumer uses the upstream-supported `KF6::KirigamiPlatform` target. QuickCharts consumer validation requires the exported `KF6::QuickCharts` and `KF6::QuickChartsControls` targets and invokes both QML registration symbols.

## Current state

The Batch 10 attempt ledger is intentionally empty before the first real package run. No node is promoted by this preparation commit. Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**.


## Preparation infrastructure incident — scope-test ShellCheck

Repository Policy run `35388377180`, job `105740650985`, stopped at `Lint shell scripts` before the Batch 10 scope test or preparation validator could run. ShellCheck `SC2251` rejected three negative assertions in `test-kde-tier1-package-batch10-scope.sh` because bare `! command` under `set -e` can bypass errexit semantics.

Classification: **infrastructure / package_state_effect=none**. No Kirigami or KQuickCharts package state is created by this failure. The test is rewritten with explicit `if command; then ... exit 1; fi` assertions. The shared selector also records its exit contract (`0=rebuild`, `1=intentional skip`) so the corrective commit deliberately revalidates both Batch 10 package gates after Repository Policy passes.
