# KDE Frameworks Tier 1 — Batch 10 QML/multisurface package campaign

Status: **Kirigami retained PASS; KQuickCharts remediation pending; canonical state not promoted**

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

## Validation cycle 2 — consumer harness false negative

Repository Policy run `35392233427`, job `105752975995`, passed all policy gates including the Batch 10 validator. PR CI run `35392233659` rebuilt Kirigami `6.30.0-0supralinux2`.

Kirigami job `105753009458` reached the final consumer smoke after the package itself had already built successfully. Artifact `10565524699`, ZIP SHA-256 `b5676f429fcc10d57676e8d489ab651e5aadafffebbaccd6febf7c97cad3c3f5`, rootfs SHA-256 `93928deec54c2410944410c4bb52eaab8b70723fea50271f51aa3cc0b70d8384`.

Validated before the false-negative abort:

- upstream tests: `44/44 PASS`;
- Lintian source+binary error gate: PASS;
- reviewed `optional=templinst` symbols remediation: PASS;
- architecture-aware ABI floors: PASS across all 15 runtime surfaces;
- QML module/import validation: PASS;
- exact local-package APT installation and `apt-get check`: PASS.

The failure was in the repository consumer harness, not the package. `packages/kde/kirigami/consumer/CMakeLists.txt` requested `find_package(KF6 6.30 ...)`, which searches for a nonexistent umbrella `KF6Config.cmake`. The built `libkirigami-dev` correctly installs `KF6KirigamiPlatformConfig.cmake` and exports `KF6::KirigamiPlatform`; that config in turn declares the required Qt6 Core/Qml/Quick dependencies.

Classification: **INFRA / package_state_effect=none**. This validation cycle is not appended as a Kirigami package FAIL and does not certify PASS because the consumer gate did not execute successfully. Kirigami remains at `6.30.0-0supralinux2`; only the consumer harness changes to `find_package(KF6KirigamiPlatform 6.30 REQUIRED CONFIG)`.

KQuickCharts job `105755393521` was again not attempted. It recorded **BLOCKED** with artifact `10566446188`, SHA-256 `23e45810ba579c997a6c6c3ab46e34d53fd8f2360713cc8f38dae353ea7f8e3d`. This is a second BLOCKED validation event, not a KQuickCharts FAIL.

Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until retained full package PASS evidence is separately promoted.

## Validation cycle 3 — Kirigami PASS, KQuickCharts attempt 1 FAIL

Repository Policy run `35398956303` passed the corrected Batch 10 policy before package interpretation. PR CI run `35398956698` then validated the campaign on commit `25af7164a76a925f27814aabe1986727a53d49bf`.

Kirigami `6.30.0-0supralinux2` is now a retained **PASS**:

- job `105774229788`;
- artifact `10569258322`;
- artifact ZIP SHA-256 `6a008366edda84f8c285e5cf0a6b18a4b1089fc88e530d6e61b0f4f885dd7e30`;
- rootfs SHA-256 `8a1e3d09d8788ad38c81cb7071f7149c114f3582ee3c59d489114c3b81497a35`;
- tests `44/44 PASS`;
- Lintian error gate PASS;
- all 15 ABI surfaces satisfy their amd64 floors;
- exact local APT closure/check PASS;
- QML import validation PASS;
- corrected `KF6KirigamiPlatform` consumer configure/build/run PASS;
- downstream-eligible inside the Batch 10 campaign.

The generated ABI export counts are: Kirigami `12`, Controls `28`, Delegates `10`, Dialogs `1`, Forms `1`, FormsPrivateCards `10`, FormsPrivateFlat `10`, FormsPrivateTemplates `1`, Layouts `26`, LayoutsPrivate `1`, Platform `435`, Polyfill `1`, Primitives `11`, Private `10`, Templates `3`.

The same run therefore released KQuickCharts for its **first real package attempt**. Job `105776448807` downloaded the current-run Kirigami PASS artifact and verified all 19 Kirigami binary packages at exactly `6.30.0-0supralinux2`, proving the package-validation dependency was satisfied by SupraLINUX rather than Ubuntu.

KQuickCharts `6.30.0-0supralinux1` then produced a real **FAIL**:

- artifact `10570203712`;
- artifact ZIP SHA-256 `1f4a4a65e3e534d000b0507ff583f8ef657eb5836d0db840ef405d5ab501f12e`;
- rootfs SHA-256 `7da69856573c2d320f7e8a345d53fff793c39e0e8fe1e0e144bed73fcf3765d2`;
- tests `8/8 PASS`;
- failure stage: `sbuild` / `dh_makeshlibs`.

`dpkg-gensymbols` reported three missing retained-baseline symbols. The `std::_Rb_tree::find` symbol was already `optional=templinst` and is not causal. The two causal entries are the `std::_Sp_counted_ptr<QQuickItem *>` RTTI/vtable exports `_ZTI...` and `_ZTV...`, both retained as mandatory on `arch=!riscv64`. They are private libstdc++ template-instantiation details rather than public KQuickCharts API.

### KQuickCharts attempt-1 remediation

KQuickCharts moves to `6.30.0-0supralinux2`. A deterministic `debian/apply-symbols-delta.py` verifies the retained Debian 6.28 baseline SHA-256 `ed06cd19136bc5a1bfb10fb7e5c93070fdb4f76ca81f8536243666297e8193e6`, changes **only** the two RTTI/vtable entries from `arch=!riscv64` to `optional=templinst|arch=!riscv64`, preserves their historical `6.0.0` minimum, and verifies transformed SHA-256 `f1ba9c4d179d7dc3638f82fe5879c6ecea43455f520eff686aad508c4e32702e`.

The already-optional `std::_Rb_tree::find` line is deliberately unchanged. No active `.symbols` file is committed. `python3:any` is declared because `debian/rules` invokes the deterministic helper before `dh_makeshlibs`.

Kirigami remains retained PASS and does not need a rebuild. The next semantic scope should skip Kirigami and make KQuickCharts resolve the retained Kirigami artifact through campaign `pass_evidence`.

Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**. Canonical promotion remains separate until both Batch 10 nodes have retained PASS evidence.

## Validation cycle 4 — retained Kirigami reuse, KQuickCharts dh_qmldeps FAIL

Repository Policy run `35400585217` passed. PR CI run `35400585402` scope-skipped Kirigami and correctly reused retained Kirigami PASS artifact `10569258322` from run `35398956698` for KQuickCharts.

KQuickCharts `6.30.0-0supralinux2` was therefore attempted for the second time and is a real package **FAIL**, not BLOCKED: job `105779442087`, artifact `10570720119`, ZIP SHA-256 `edbcef8faf5801ae9a5c95b59270f7726a2abbbc1a5268d994816bf731eb7066`, rootfs SHA-256 `413b2fabd4248a9a11a4ec47792873c4c730a9c8c4aa15336f73be4acc79bec8`. Upstream tests are `8/8 PASS`; the reviewed symbols delta also completed. The later failure is `dh_qmldeps`: `org.kde.kirigami` was available through the retained local artifact but was not installed in the build chroot because the QML module was absent from `Build-Depends`.

Revision `6.30.0-0supralinux3` adds only `qml6-module-org-kde-kirigami (>= 6.30.0~)` as a Debian/QML metadata-generation Build-Depends. It does not add `libkirigami-dev`, does not alter upstream CMake requirements, and does not create a KDE Framework build dependency. The runner continues to require retained/current SupraLINUX Kirigami PASS evidence and exact-version runtime provenance.

Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until KQuickCharts obtains retained PASS evidence and Batch 10 is separately promoted.

## Validation cycle 5 — ABI harness false negative

Repository Policy `35403143742` passed. PR CI run `35403143944` re-used retained Kirigami PASS evidence and built KQuickCharts `6.30.0-0supralinux3`. The package build itself completed successfully: upstream tests `8/8 PASS`, the reviewed symbols remediation completed, `dh_qmldeps` resolved `org.kde.kirigami`, the generated QML package depends on `qml6-module-org-kde-kirigami`, and Lintian completed without errors.

The later `abi-contract` gate produced a repository validation false negative. Evidence: job `105787263585`, artifact `10570704785`, ZIP SHA-256 `7ddc766a2664c0af20fd7e265afc396ad5a0e210bc101bf151272c5ff0ff799a`, rootfs SHA-256 `b6f02804169e2347e6c4e11adfbd799887c02e238961ad5e0be76fa621644720`. The runner searched for `SONAME + ".*"`; KQuickCharts correctly packages the exact `libQuickCharts.so.1` SONAME symlink pointing to `libQuickCharts.so.6.30.0`, so that glob could never find the payload.

Classification is **INFRA / package_state_effect=none**. This is not KQuickCharts attempt 3 and does not bump the package revision: `6.30.0-0supralinux3` remains the validation candidate. The shared Batch 10 runner now resolves the exact packaged SONAME path. Because the runner is shared, the next validation cycle deliberately revalidates both Kirigami and KQuickCharts.

Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**.

## Validation cycle 6 — effective ABI floor after reviewed symbols remediation

Repository Policy `35403657994` passed. PR CI `35403658149` rebuilt both Batch 10 nodes because the ABI runner changed. Kirigami `6.30.0-0supralinux2` revalidated PASS in job `105788851422`, artifact `10571533917`, ZIP SHA-256 `b0da3c39920ffaa46ddc481a0eacbeee737e9d0f08ebd39ba8a79ff647152fa3`, rootfs SHA-256 `053c2cb7e3d1f71591192f4551ad0e69f6d28eb32d9c972d649015268507e9e2`, with `44/44 PASS` and Lintian PASS.

KQuickCharts `6.30.0-0supralinux3` then consumed that same-run Kirigami PASS and built successfully with `8/8 PASS`, `dh_qmldeps` PASS and Lintian PASS. Its job `105790735337`, artifact `10570804457`, ZIP SHA-256 `8ba90bdf3514dc89e1d5ffac82c285ed089d9b8e038dee3c3cddf676b9f519f6`, rootfs SHA-256 `7b207b2d11d7fbbba430714ac49b8216a7d8c738d1e88a7a456b31fbe38e6b9d`, stopped only at the repository ABI floor check.

The retained Debian 6.28 QuickCharts baseline contains 393 exports, including 2 optional exports and 9 non-optional exports inapplicable on amd64, giving the historical pre-remediation required floor 382. The reviewed KQuickCharts symbols overlay converts two existing amd64 `std::_Sp_counted_ptr<QQuickItem *>` RTTI/vtable exports from required to `optional=templinst|arch=!riscv64`. Therefore the **effective required amd64 floor is 380**, while the historical reference floor remains 382. The built package emitted 381 exports; it satisfies the remediated ABI contract.

Cycle 6 is classified **INFRA / package_state_effect=none**. It is not KQuickCharts attempt 3 and does not bump the package beyond `6.30.0-0supralinux3`. The manifest now records both `reference_required_export_count_amd64=382` and `effective_required_export_count_amd64=380`, and the runner uses the effective floor only when an explicitly reviewed override exists.

Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** pending successful revalidation and separate Batch 10 promotion.

## Validation cycle 7 — exported ECM development dependency

Repository Policy `35406143702` passed. PR CI `35406143858` rebuilt Batch 10 with the reviewed effective ABI floor. Kirigami `6.30.0-0supralinux2` revalidated PASS and supplied a current-run predecessor artifact to KQuickCharts.

KQuickCharts `6.30.0-0supralinux3` passed build, `8/8` upstream tests, Lintian, `dh_qmldeps`, both ABI contracts including QuickCharts `381 >= 380`, QML import validation and exact local-package APT closure. It then failed at `consumer-smoke`: job `105797738652`, artifact `10572841006`, ZIP SHA-256 `87c84de4c44bcf7bf6dfad958e85ea755dd34ae014dd85508c250e596b4b4563`, rootfs SHA-256 `bc109e0dd164e30611fa519db43aef659eba2346b1a3f3a1b8e5ce61a3aead92`.

The installed `libquickcharts-dev` exports `KF6QuickChartsConfig.cmake`, and that KDE 6.30 config explicitly calls `find_dependency(ECM 6.30.0)` before loading `ECMFindQmlModule.cmake`. The binary development package did not depend on `extra-cmake-modules`, so a clean consumer could not configure. This is a real packaging FAIL: the package's exported development contract was incomplete.

Revision `6.30.0-0supralinux4` adds `extra-cmake-modules (>= 6.30.0~)` to **libquickcharts-dev Depends**. It does not add a KQuickCharts Framework build dependency; `kde_framework_build_dependencies=[]` remains unchanged. Consumer validation now installs and verifies the retained SupraLINUX ECM `6.30.0-0supralinux3` artifact alongside the local QuickCharts/Kirigami packages, preventing Ubuntu's older ECM from satisfying the exported config.

KQuickCharts now has three real FAIL attempts; cycles 5 and 6 remain infrastructure incidents only. Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until a retained QuickCharts PASS and separate promotion.
