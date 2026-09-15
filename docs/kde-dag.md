# KDE stable dependency DAG

Status: **ECM root PASS; 10 Frameworks Tier 1 PASS; 19 Tier 1 pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-15**

## Authority

KDE upstream stable defines the desktop and its requirements. Ubuntu 26.04 is platform, provider and compatibility target. Packaging from another distribution is technical reference only and never selects the KDE version for SupraLINUX.

Selected snapshot at this closure point:

- Plasma 6.7.5;
- KDE Frameworks 6.30.0;
- KDE Gear 26.08.1;
- KDE-selected Qt series 6.10;
- Ubuntu Resolute Qt 6.10.2: hosted preflight PASS;
- final Qt provider certification: pending.

Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1. That is a technical packaging reference only; KDE upstream 6.30.0 remains authority for ECM.

## DAG semantics

- `PASS`: the defined gate was actually attempted and completed.
- `FAIL`: the node was actually attempted and failed for its own cause.
- `BLOCKED`: the node is not attempted because a required predecessor is FAIL.
- `pending`: not yet attempted.

BLOCKED is never counted as FAIL. Historical FAILs remain evidence after a later PASS. A hosted PASS does not replace later KVM/JIT/system/compatibility gates.

## Extra CMake Modules 6.30.0 — PASS

Source SHA-256 `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`.

Validated package `extra-cmake-modules 6.30.0-0supralinux3`:

- run `34694951158`;
- job `103556722010`;
- artifact `10298635300`;
- artifact SHA-256 `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`;
- `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- result PASS.

Earlier ECM FAIL attempts remain recorded in the manifest and are not erased.

## Tier 1 PASS

### Attica

`6.30.0-0supralinux2`, run `34706416753`, artifact `10301851297`, artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`, tests 6/6 PASS, consumer smoke PASS.

### Batch 1 — 3/3 PASS

- KCodecs `6.30.0-0supralinux4`.
- KDBusAddons `6.30.0-0supralinux3`.
- ThreadWeaver `6.30.0-0supralinux3`.

KCodecs retains reviewed `(optional=toolchain)` handling for implementation symbols rather than treating compiler/libstdc++ internals as mandatory public ABI.

### Batch 2 — 3/3 PASS

Final workflow `34884764702`, commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75`:

- KTextTemplate `6.30.0-0supralinux3`: job `104112549851`, artifact `10363863115`, SHA-256 `7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9`, tests 10/10 PASS.
- KArchive `6.30.0-0supralinux4`: job `104112549742`, artifact `10364726750`, SHA-256 `0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e`, tests 5/5 PASS.
- KHolidays `6.30.0-0supralinux4`: job `104112549858`, artifact `10364169061`, SHA-256 `62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a`, tests 8/8 PASS.

### Batch 3 — 3/3 PASS

KItemModels and KPlotting passed the first Batch 3 campaign; BluezQt required one reviewed symbols remediation.

- KItemModels `6.30.0-0supralinux1`: run `34896417969`, job `104151531993`, artifact `10369501432`, SHA-256 `b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732`, tests 13/13 PASS.
- KPlotting `6.30.0-0supralinux1`: run `34896417969`, job `104151532320`, artifact `10369086459`, SHA-256 `f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8`, tests 5/5 PASS.
- BluezQt `6.30.0-0supralinux2`: run `34945979836`, job `104305337324`, artifact `10387429776`, SHA-256 `db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed`, tests 18/18 PASS, Lintian/SONAME/consumer smoke PASS.

BluezQt attempt 1 at `6.30.0-0supralinux1` remains a historical real FAIL caused by the symbols/Lintian gate. It is not BLOCKED.

## Infrastructure incidents

Run `34716761551` selected already-PASS KDBusAddons and ThreadWeaver because the original semantic fingerprint included descriptive metadata. Both aborted at campaign validation before package build. This has no package-state effect; the fingerprint was narrowed to runner-consumed inputs.

Run `34884049556` exposed missing preservation of `.ddeb` referenced by `.changes` before the reinforced standalone Lintian gate. This was an infrastructure evidence-completeness issue, not a package FAIL; run `34884764702` validates the fix.

Repository Policy run `34945979830`, job `104305336760`, exposed a Batch 3 validator false positive. The validator matched the target `override_dh_makeshlibs:` as though it were execution of `dh_makeshlibs`, even though the real recipe already applied the symbols transform first. The validator now identifies actual Make recipe command lines and checks transform-before-command semantics. This incident also has no package-state effect.

## Current state

Tier 1 is **10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED**.

Only retained PASS artifacts may feed dependents.

## Next expansion

Before opening Batch 4, revalidate current KDE upstream stable metadata. Then select the next independent group among the 19 pending nodes, compile all ready nodes in parallel, continue past independent FAILs, and reserve BLOCKED strictly for nodes whose required predecessor is FAIL.

KConfig remains deferred until the package runner explicitly supports its multi-library ABI/symbol contract.

PR #1 remains Draft. No merge is authorized.
