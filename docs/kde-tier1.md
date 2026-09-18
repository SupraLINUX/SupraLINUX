# KDE Frameworks 6.30 — Tier 1

Status: **29-node source set fixed; 22 hosted package PASS; 7 package nodes pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-18**

## Authority and scope

Tier membership and source requirements come from KDE upstream. SupraLINUX selects KDE Frameworks **6.30.0**. Ubuntu Resolute provides platform, general dependencies and compatibility; Ubuntu and Debian are technical packaging references and do not select the KDE version.

Frameworks 6.30 requires Qt >= **6.9.0**. Ubuntu Resolute Qt **6.10.2** remains the current provider candidate and its hosted preflight is PASS; final provider certification remains a separate gate.

## Prerequisite

Extra CMake Modules remains the build-system root:

- package `extra-cmake-modules 6.30.0-0supralinux3`;
- run `34694951158`;
- artifact `10298635300`;
- `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- state **PASS**;
- downstream eligible.

## Tier 1 set

The manifest contains exactly 29 nodes:

`attica`, `bluez-qt`, `karchive`, `kcalendarcore`, `kcodecs`, `kconfig`, `kcoreaddons`, `kdbusaddons`, `kglobalaccel`, `kguiaddons`, `kholidays`, `ki18n`, `kidletime`, `kirigami`, `kitemmodels`, `kitemviews`, `kplotting`, `kquickcharts`, `syntax-highlighting`, `ktexttemplate`, `kuserfeedback`, `kwidgetsaddons`, `kwindowsystem`, `modemmanager-qt`, `networkmanager-qt`, `prison`, `solid`, `sonnet`, `threadweaver`.

Every node is pinned to KDE 6.30.0 and to the KDE-published source SHA-256. A Tier 1 node does not depend on another KDE Framework; all depend only on the ECM root inside the KDE DAG.

## Reference evidence

- provider availability: run `34700048774`, artifact `10299608166`;
- source packaging reference: run `34701132721`, artifact `10299579234`;
- binary-contract reference: run `34704117024`, artifact `10301282501`;
- generic packaging tree: run `34708030450`, artifact `10301938362`.

These gates are non-authoritative references and cannot promote package state by themselves.

## Canonical PASS nodes

### Attica

`6.30.0-0supralinux2`, run `34706416753`, artifact `10301851297`, 6/6 tests PASS, consumer smoke PASS.

### Batch 1

- KCodecs `6.30.0-0supralinux4`: run `34716761551`, job `103615297758`, artifact `10305050385`, artifact SHA-256 `d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45`, 8/8 tests PASS.
- KDBusAddons `6.30.0-0supralinux3`: run `34713034164`, job `103605147881`, artifact `10304340428`, 3/3 tests PASS.
- ThreadWeaver `6.30.0-0supralinux3`: run `34713034164`, job `103605147772`, artifact `10303986419`, 8/8 tests PASS.

### Batch 2

Final workflow `34884764702`:

- KTextTemplate `6.30.0-0supralinux3`: job `104112549851`, artifact `10363863115`, SHA-256 `7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9`, 10/10 tests PASS.
- KArchive `6.30.0-0supralinux4`: job `104112549742`, artifact `10364726750`, SHA-256 `0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e`, 5/5 tests PASS.
- KHolidays `6.30.0-0supralinux4`: job `104112549858`, artifact `10364169061`, SHA-256 `62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a`, 8/8 tests PASS.

All three pass Lintian, SONAME and consumer-smoke gates.

### Batch 3

- KItemModels `6.30.0-0supralinux1`: run `34896417969`, job `104151531993`, artifact `10369501432`, SHA-256 `b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732`, 13/13 tests PASS.
- KPlotting `6.30.0-0supralinux1`: run `34896417969`, job `104151532320`, artifact `10369086459`, SHA-256 `f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8`, 5/5 tests PASS.
- BluezQt `6.30.0-0supralinux2`: run `34945979836`, job `104305337324`, artifact `10387429776`, SHA-256 `db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed`, 18/18 tests PASS, Lintian and consumer smoke PASS.

BluezQt attempt 1 at `6.30.0-0supralinux1` remains a historical real FAIL. It is not BLOCKED and is not erased by the later PASS.

### Batch 4

- KItemViews `6.30.0-0supralinux1`: run `34999449194`, job `104483912528`, artifact `10409267184`, 2/2 tests PASS.
- KGlobalAccel `6.30.0-0supralinux2`: run `35006477086`, job `104507372240`, artifact `10412320520`, 1/1 tests PASS; its `-1` missing-`LinguistTools` attempt remains historical FAIL evidence.
- KSyntaxHighlighting `6.30.0-0supralinux2`: run `35006477086`, job `104507371855`, artifact `10411888269`, 8/8 tests PASS; its `-1` missing-`LinguistTools` attempt remains historical FAIL evidence.

### Batch 5

- KIdleTime `6.30.0-0supralinux1`: run `35014875475`, job `104535671033`, artifact `10414598079`, 1/1 tests PASS.
- ModemManagerQt `6.30.0-0supralinux3`: run `35021323444`, job `104557423664`, artifact `10417683848`, 11/11 tests PASS; two earlier real FAIL attempts remain historical evidence.
- NetworkManagerQt `6.30.0-0supralinux1`: run `35014875475`, job `104535671250`, artifact `10414714325`, 38/38 tests PASS.

### Batch 6

Final shared-runner revalidation workflow `35047623320`:

- KWindowSystem `6.30.0-0supralinux4`: job `104640833059`, artifact `10428130399`, ZIP SHA-256 `9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272`, 14/14 tests PASS, Lintian/SONAME/consumer runtime closure PASS.
- Solid `6.30.0-0supralinux2`: job `104640833295`, artifact `10427653865`, ZIP SHA-256 `cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389`, 5/5 tests PASS, Lintian/SONAME/consumer runtime closure PASS.

Both are downstream-eligible. KWindowSystem's four prior FAIL attempts and Solid's earlier FAIL plus historical PASS remain retained as evidence; current node state is PASS.

## ABI and packaging policy

KCodecs uses Debian 6.28 as the closest technical symbols baseline. Fifteen `std::format`-related compiler/libstdc++ implementation symbols are retained as `(optional=toolchain)` at upstream minimum `6.30.0` rather than being promoted to public ABI.

Batch 2 preserves its reviewed deterministic ABI transforms and Debian-family compatibility package names. Documentation stubs do not claim QCH payload when none is built.

BluezQt uses the same reviewed implementation-symbol policy for `_ZSt19piecewise_construct@Base`. The deterministic transform preserves the Debian 6.28 public ABI baseline and marks only that implementation/toolchain export optional at upstream minimum `6.30.0`.

## CI evidence semantics

A node is FAIL only after a real attempted build fails for its own cause. BLOCKED is reserved for a node not attempted because a required predecessor is FAIL. Historical FAILs remain evidence after later PASS results.

Changes to state, evidence or documentation must not rebuild retained PASS packages. Infrastructure selector/validator failures do not create package FAILs.

Repository Policy run `34945979830` exposed such an infrastructure-only issue: the validator matched `override_dh_makeshlibs:` as if it were a real `dh_makeshlibs` invocation. The validator now identifies actual Make recipe commands and checks the real execution order.

## Current state

- PASS: **25**;
- pending: **4**;
- current FAIL: **0**;
- BLOCKED: **0**.

Only retained PASS artifacts may feed downstream nodes.

## Next work

Batch 8 canonically promotes KGuiAddons `6.30.0-0supralinux2` from run `35185562846`, job `105086774400`, artifact `10482007092`, ZIP SHA-256 `71d32ecb50f6617ba198325a552e68e995c20c9050c7ae21f6a69d5b680184ca`; tests are `9/9 PASS`, Lintian passes the error gate, Python import/APT closure/consumer smoke pass, and the runtime SONAME is `libKF6GuiAddons.so.6`. KCoreAddons remains a public-header/consumer provider only, not a KGuiAddons Framework build dependency.

Batch 9 is now canonically promoted 3/3: KConfig `6.30.0-0supralinux4`, KI18n `6.30.0-0supralinux1` and Sonnet `6.30.0-0supralinux3` are PASS/downstream-eligible in both Tier 1 and the package DAG. KConfig final evidence is run `35360530830`, job `105650448776`, artifact `10554715051`, SHA-256 `bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e`, with `90/90 PASS`, Lintian, architecture-aware ABI, APT, QML and consumer smoke PASS. Final promotion precheck Repository Policy run `35365719747` passed and all three Batch 9 jobs scope-skipped, proving no rebuild was needed for promotion. Four canonical pending nodes remain: `kirigami`, `kquickcharts`, `kuserfeedback` and `prison`. The earlier source run `35138333645` remains DIAG_PASS only.

PR #1 remains Draft. No merge is authorized.


### Batch 10 preparation

The QML/multisurface lane is implementation-ready without changing canonical state: **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**. Kirigami is runnable. KQuickCharts remains a Tier 1 source with no KDE Framework build dependency on Kirigami; however, its full package QML/runtime closure is ordered after a retained SupraLINUX Kirigami PASS. If Kirigami fails, KQuickCharts package validation is BLOCKED rather than recorded as a package FAIL.

### Batch 10 attempt 1

Repository Policy `35389029819` passed. PR CI `35389030840` produced a real Kirigami `6.30.0-0supralinux1` FAIL at Lintian after successful build and `44/44 PASS` tests (job `105742841430`, artifact `10565625878`, SHA-256 `58b5bc72f81cdd26ea368cf810d1e1727fbdfc521203fe889bca005aa2f9aca8`). KQuickCharts was not attempted and is recorded BLOCKED by Kirigami (job `105745672521`, artifact `10565780756`).

Kirigami remediation `6.30.0-0supralinux2` classifies the 38 newly emitted Qt/libstdc++ template-instantiation symbols as deterministic hash-pinned `optional=templinst` entries before `dh_makeshlibs`; KDE bug 519452 documents the exact QMetaType/QMetaSequence set as parallel-build-dependent. Canonical Tier 1 remains 25 PASS / 4 pending until a separate promotion.

### Batch 10 validation cycle 2

Kirigami `6.30.0-0supralinux2` passed build, `44/44` tests, Lintian, the reviewed template-symbol remediation, ABI, QML and APT gates in run `35392233659`, then hit a repository consumer-harness false negative at `consumer-smoke`: the test requested nonexistent umbrella `KF6Config.cmake` instead of the installed `KF6KirigamiPlatformConfig.cmake`.

This is retained as **INFRA / package_state_effect=none**, not a package FAIL. The package revision remains `-2`. KQuickCharts remained unattempted/BLOCKED. Canonical Tier 1 remains 25 PASS / 4 pending until a full PASS cycle and separate promotion.

### Batch 10 validation cycle 3

Kirigami `6.30.0-0supralinux2` is retained PASS from run `35398956698`, job `105774229788`, artifact `10569258322`, SHA-256 `6a008366edda84f8c285e5cf0a6b18a4b1089fc88e530d6e61b0f4f885dd7e30`, rootfs `8a1e3d09d8788ad38c81cb7071f7149c114f3582ee3c59d489114c3b81497a35`, with `44/44 PASS` and all Lintian/ABI/APT/QML/consumer gates PASS.

KQuickCharts then consumed the exact Kirigami PASS and produced its first real package FAIL at `dh_makeshlibs`: job `105776448807`, artifact `10570203712`, tests `8/8 PASS`. QuickCharts moves to `6.30.0-0supralinux2` with two private `std::_Sp_counted_ptr<QQuickItem *>` RTTI/vtable entries marked `optional=templinst|arch=!riscv64` by deterministic hash-verified transformation.

Kirigami is campaign-downstream-eligible but remains canonical pending until Batch 10 promotion. Canonical Tier 1 stays 25 PASS / 4 pending.

### Batch 10 validation cycle 4

Repository Policy `35400585217` passed. PR CI `35400585402` reused retained Kirigami PASS evidence and attempted KQuickCharts `6.30.0-0supralinux2`. Job `105779442087` is a real package FAIL at `dh_qmldeps`, artifact `10570720119`, ZIP SHA-256 `edbcef8faf5801ae9a5c95b59270f7726a2abbbc1a5268d994816bf731eb7066`, rootfs `413b2fabd4248a9a11a4ec47792873c4c730a9c8c4aa15336f73be4acc79bec8`, with `8/8 PASS` tests and successful symbol remediation before the failure.

KQuickCharts moves to `6.30.0-0supralinux3`. The added `qml6-module-org-kde-kirigami (>= 6.30.0~)` Build-Depends exists only so Debian `dh_qmldeps` can resolve the packaged QML import. No `libkirigami-dev` dependency is added and `kde_framework_build_dependencies=[]` remains unchanged. Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until separate promotion.

### Batch 10 validation cycle 5

KQuickCharts `6.30.0-0supralinux3` completed its real package build in PR CI `35403143944`: `8/8 PASS`, symbols remediation PASS, `dh_qmldeps` PASS with retained Kirigami `6.30.0-0supralinux2`, and Lintian without errors. Job `105787263585` then stopped at the repository `abi-contract` gate, artifact `10570704785`, SHA-256 `7ddc766a2664c0af20fd7e265afc396ad5a0e210bc101bf151272c5ff0ff799a`.

This is **INFRA / package_state_effect=none**. The package does contain `libQuickCharts.so.1`; the harness incorrectly required a filename beginning `libQuickCharts.so.1.` even though the exact SONAME is a symlink to `libQuickCharts.so.6.30.0`. The generic Batch 10 ABI check now opens the exact packaged SONAME. QuickCharts stays at `-3`, real attempts stay at two, and canonical Tier 1 remains 25 PASS / 4 pending pending revalidation and separate promotion.

### Batch 10 validation cycle 6

Repository Policy `35403657994` passed. PR CI `35403658149` revalidated Kirigami `6.30.0-0supralinux2` PASS and then built KQuickCharts `6.30.0-0supralinux3` successfully. Kirigami artifact `10571533917` has SHA-256 `b0da3c39920ffaa46ddc481a0eacbeee737e9d0f08ebd39ba8a79ff647152fa3` and `44/44 PASS`. KQuickCharts artifact `10570804457` has SHA-256 `8ba90bdf3514dc89e1d5ffac82c285ed089d9b8e038dee3c3cddf676b9f519f6`, with `8/8 PASS`, `dh_qmldeps` PASS and Lintian PASS before the ABI gate.

The gate used the historical Debian required floor 382 even though the reviewed symbols remediation had made two existing amd64 template-instantiation exports optional. The manifest now distinguishes `reference_required_export_count_amd64=382` from `effective_required_export_count_amd64=380`; the package emitted 381 exports. This is **INFRA / package_state_effect=none**, not a new package FAIL or revision bump.

Canonical Tier 1 stays at **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until revalidation completes and Batch 10 is promoted separately.

### Batch 10 validation cycle 7

PR CI `35406143858` confirms the effective ABI correction: KQuickCharts `6.30.0-0supralinux3` passed `8/8`, Lintian, `dh_qmldeps`, QuickCharts ABI `381 >= 380`, QML imports and exact APT closure. The package then produced real FAIL attempt 3 at `consumer-smoke`: job `105797738652`, artifact `10572841006`, SHA-256 `87c84de4c44bcf7bf6dfad958e85ea755dd34ae014dd85508c250e596b4b4563`, rootfs `bc109e0dd164e30611fa519db43aef659eba2346b1a3f3a1b8e5ce61a3aead92`.

The exported `KF6QuickChartsConfig.cmake` requires ECM 6.30, but `libquickcharts-dev` did not depend on `extra-cmake-modules`. KQuickCharts moves to `6.30.0-0supralinux4` with `extra-cmake-modules (>= 6.30.0~)` in the development package Depends. Consumer validation also installs and verifies the retained SupraLINUX ECM `6.30.0-0supralinux3` provider.

This does not create a KDE Framework build edge. Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**.
