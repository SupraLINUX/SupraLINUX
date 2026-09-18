# KDE Frameworks Tier 1 — Batch 10 QML/multisurface package campaign

Status: **attempt 1 recorded; Kirigami remediation pending; package state not promoted**

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

## Attempt 1 — Kirigami real FAIL, KQuickCharts BLOCKED

Repository Policy run `35389029819` passed completely. PR CI run `35389030840` then executed the first real Batch 10 package cycle on commit `67a6558513a82d4a1b4426a9b705eafdadbd3bf4`.

Kirigami `6.30.0-0supralinux1` is a real **FAIL**:

- job `105742841430`;
- artifact `10565625878`;
- artifact ZIP SHA-256 `58b5bc72f81cdd26ea368cf810d1e1727fbdfc521203fe889bca005aa2f9aca8`;
- rootfs SHA-256 `445ce98267d53ec58a98bed3ee74343f04f2465bdccf258efa95e709551ff7b1`;
- package build successful;
- upstream tests `44/44 PASS`;
- failure stage: Lintian inside `sbuild`.

Lintian rejected 38 newly emitted symbols across `libkirigamicontrols6`, `libkirigamidelegates6`, `libkirigamiformsprivatecards6`, `libkirigamiformsprivateflat6` and `libkirigamitemplates6` because `dpkg-gensymbols` assigned the current Debian revision. This is packaging/ABI metadata failure, not infrastructure.

KQuickCharts was **not attempted**. Job `105745672521` recorded **BLOCKED** with artifact `10565780756`, SHA-256 `118afc6b702b4ec9fee050898fcbc381f5beaf2131013b619973c85e81f27ef8`, `blocked_by=kirigami`. It is not a KQuickCharts FAIL.

## Attempt 1 remediation — Kirigami 6.30.0-0supralinux2

The 38 exports are C++ template-instantiation/toolchain ABI noise, not new public Kirigami APIs. KDE bug 519452 documents the exact nine QMetaType/QMetaSequence symbols as dependent on build parallelism and recommends `optional=templinst`; Debian `dpkg-gensymbols` policy likewise supports optional tags for private template instantiations. The two `std::_Rb_tree<QString,QVariant>` exports are handled as template instantiations for the same reason.

Revision `6.30.0-0supralinux2` uses a deterministic `debian/apply-symbols-delta.py` immediately before `dh_makeshlibs`. It verifies each retained Debian 6.28 baseline hash, inserts only the reviewed optional symbols at an exact anchor, then verifies the complete transformed file hash. No active `.symbols` file is committed.

| Symbols surface | Added optional symbols | Minimum used | Transformed SHA-256 |
| --- | ---: | --- | --- |
| Controls | 9 | 6.30.0 (first observed here) | `71cc0b7a2622f7b9b98c9d87dfa5e7824743025ff8960fdb5ef28da9ffe67f38` |
| Delegates | 9 | 6.23.0 (KDE bug 519452 exact set) | `7b2f50807ea409c91094e36605a37cf8190910e0be23f8e472a051d9bcbb9954` |
| FormsPrivateCards | 9 | 6.30.0 (first observed here) | `4483ccb4b6cc376bb28e5ac408147b8cf3f190b9a394f1b38326d7500671925f` |
| FormsPrivateFlat | 9 | 6.30.0 (first observed here) | `75c25d52c7415502d200b57f4dea7d9a8405aa3df20a2d5ea03349d5812fcc61` |
| Templates | 2 | 6.30.0 (first observed here) | `b60af9408ad63c919775ce099d040a5207069dd972e5daee98c974336e038582` |

Only Delegates claims the externally documented 6.23.0 minimum. For the other affected libraries SupraLINUX deliberately uses 6.30.0 as the conservative first-observed package minimum rather than inventing an earlier per-library introduction. `python3:any` is added to Build-Depends because `debian/rules` executes the delta helper.

Reference: https://bugs.kde.org/show_bug.cgi?id=519452

Canonical Tier 1 is intentionally unchanged at **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until separate promotion. Operational Batch 10 history records Kirigami attempt 1 FAIL and KQuickCharts BLOCKED; the remediation candidate makes Kirigami runnable at `-2`, while KQuickCharts remains package-validation-dependent on a Kirigami PASS.


## Preparation infrastructure incident — scope-test ShellCheck

Repository Policy run `35388377180`, job `105740650985`, stopped at `Lint shell scripts` before the Batch 10 scope test or preparation validator could run. ShellCheck `SC2251` rejected three negative assertions in `test-kde-tier1-package-batch10-scope.sh` because bare `! command` under `set -e` can bypass errexit semantics.

Classification: **infrastructure / package_state_effect=none**. No Kirigami or KQuickCharts package state is created by this failure. The test is rewritten with explicit `if command; then ... exit 1; fi` assertions. The shared selector also records its exit contract (`0=rebuild`, `1=intentional skip`) so the corrective commit deliberately revalidates both Batch 10 package gates after Repository Policy passes.


## Preparation infrastructure incident — validator scope assumption

Repository Policy run `35388572182`, job `105741309585`, passed ShellCheck, the Batch 10 semantic scope test and global discovery validation, then failed only in the Batch 10 preparation validator. The validator incorrectly required a literal `packages/kde/kquickcharts/*` token even though the selector intentionally uses the generic `packages/kde/${NODE}/*`, and it searched for `package_validation_dependencies` in selector/workflow text rather than in the campaign manifest where that metadata belongs.

Classification: **infrastructure / package_state_effect=none**. The validator now tests the actual generic selector contract and the campaign metadata separately. The shared selector receives a documentation-only contract clarification so the next PR CI deliberately rebuilds both Batch 10 nodes after Repository Policy passes.


## First Policy-valid package run — runner behavior-guard incident

Repository Policy `35388829511` passed completely on commit `5b985ead70bef19dc3727b549f01ee550cd85520`. PR CI run `35388829761` then selected Kirigami, but job `105742185938` aborted at campaign validation before source/rootfs build. Artifact `10564903426`, SHA-256 `07e820838fb1192118c207cbbb919ad0246987ae973781c72f67acda013a3534`.

The shared runner recursively grepped all `debian/` metadata for forbidden downstream behavior tokens. That incorrectly matched the package documentation which explicitly records those rejected overrides and could also match legitimate `|| true` cleanup in the X fixture. Classification: **infrastructure / package_state_effect=none**; this is not Kirigami attempt 1 and does not create a package FAIL.

The guard is narrowed to executable behavior only: forbidden feature flags are checked in `debian/rules`, and only a `dh_auto_test ... || true` suppression is rejected across the test command files. Documentation is no longer interpreted as executable policy.
