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

- PASS: **22**;
- pending: **7**;
- current FAIL: **0**;
- BLOCKED: **0**.

Only retained PASS artifacts may feed downstream nodes.

## Next work

Batch 8 canonically promotes KGuiAddons `6.30.0-0supralinux2` from run `35185562846`, job `105086774400`, artifact `10482007092`, ZIP SHA-256 `71d32ecb50f6617ba198325a552e68e995c20c9050c7ae21f6a69d5b680184ca`; tests are `9/9 PASS`, Lintian passes the error gate, Python import/APT closure/consumer smoke pass, and the runtime SONAME is `libKF6GuiAddons.so.6`. KCoreAddons remains a public-header/consumer provider only, not a KGuiAddons Framework build dependency.

The seven canonical pending nodes remain `kconfig`, `ki18n`, `sonnet`, `kirigami`, `kquickcharts`, `kuserfeedback` and `prison`. Batch 9 attempt 1 is complete: KI18n `6.30.0-0supralinux1` is retained package PASS, while KConfig and Sonnet are real independent symbols/Lintian FAILs now remediated as `6.30.0-0supralinux2`. The earlier source run `35138333645` remains DIAG_PASS only. No Batch 9 result is canonically promoted until the remediation run completes and a separate promotion commit is made.

PR #1 remains Draft. No merge is authorized.
