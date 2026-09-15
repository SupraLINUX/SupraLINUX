# KDE Frameworks 6.30 — Tier 1

Status: **29-node source set fixed; 10 hosted package PASS; 19 package nodes pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-15**

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

## ABI and packaging policy

KCodecs uses Debian 6.28 as the closest technical symbols baseline. Fifteen `std::format`-related compiler/libstdc++ implementation symbols are retained as `(optional=toolchain)` at upstream minimum `6.30.0` rather than being promoted to public ABI.

Batch 2 preserves its reviewed deterministic ABI transforms and Debian-family compatibility package names. Documentation stubs do not claim QCH payload when none is built.

BluezQt uses the same reviewed implementation-symbol policy for `_ZSt19piecewise_construct@Base`. The deterministic transform preserves the Debian 6.28 public ABI baseline and marks only that implementation/toolchain export optional at upstream minimum `6.30.0`.

## CI evidence semantics

A node is FAIL only after a real attempted build fails for its own cause. BLOCKED is reserved for a node not attempted because a required predecessor is FAIL. Historical FAILs remain evidence after later PASS results.

Changes to state, evidence or documentation must not rebuild retained PASS packages. Infrastructure selector/validator failures do not create package FAILs.

Repository Policy run `34945979830` exposed such an infrastructure-only issue: the validator matched `override_dh_makeshlibs:` as if it were a real `dh_makeshlibs` invocation. The validator now identifies actual Make recipe commands and checks the real execution order.

## Current state

- PASS: **10**;
- pending: **19**;
- current FAIL: **0**;
- BLOCKED: **0**.

Only retained PASS artifacts may feed downstream nodes.

## Next work

Revalidate the current KDE stable release metadata before starting the next package batch, then select another independent group among the 19 pending nodes. Keep ABI contracts, optional features and tests explicit; extend the package runner when a Framework requires multiple ABI libraries instead of weakening the model.

PR #1 remains Draft. No merge is authorized.
