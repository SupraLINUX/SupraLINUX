# KDE Frameworks 6.30 Tier 1 — package batch 3

Status: **REMEDIATION — BluezQt attempt 2 pending**

Last reviewed: **2026-09-15**

## Selection

Batch 3 contains three independent Tier 1 nodes:

- `kitemmodels`;
- `bluez-qt`;
- `kplotting`.

All depend only on retained ECM `6.30.0-0supralinux3` inside the KDE DAG; none depends on another KDE Framework.

KDE Frameworks `6.30.0` remains the selected stable upstream release and KDE upstream remains the source/build authority. Ubuntu Resolute is the compatibility target/provider. Debian sid 6.28 packaging is used only as a technical ABI/packaging reference.

## Why these nodes

The current package runner models one primary ABI library, one SONAME and one symbols baseline per node. KItemModels, BluezQt and KPlotting fit that model and have contained external dependency profiles.

`KConfig` remains intentionally deferred. It exports multiple ABI libraries/symbol files (`ConfigCore`, `ConfigGui`, `ConfigQml`), so packaging it correctly requires an explicit multi-library extension of the runner rather than forcing it into a single-library model.

## Packaging policy

KItemModels and KPlotting remain at revision `6.30.0-0supralinux1` after passing attempt 1. BluezQt moves to `6.30.0-0supralinux2` for the reviewed symbols remediation.

Debian-family binary package names and Multi-Arch contracts are preserved as compatibility inputs.

The retained Debian 6.28 symbols files are injected from workflow `34708030450`, artifact `10301938362`; they do not select the KDE version. Any KDE 6.30 ABI delta is reviewed from a real build.

QCH is disabled in the current common Frameworks profile. Documentation package names are retained as compatibility stubs and do not claim QCH payload.

Upstream autotests remain enabled.

## Attempt 1 — run 34896417969

The three independent nodes were actually attempted from commit `806d16476b034e796658ea1ab9028eb3a9a14e1b`.

### KItemModels — PASS

- job `104151531993`;
- package `6.30.0-0supralinux1`;
- artifact `10369501432`;
- artifact SHA-256 `b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732`;
- upstream tests `13/13 PASS`;
- Lintian error gate PASS;
- SONAME `libKF6ItemModels.so.6` PASS;
- consumer CMake/build/runtime smoke PASS;
- consumed ECM `6.30.0-0supralinux3`.

### KPlotting — PASS

- job `104151532320`;
- package `6.30.0-0supralinux1`;
- artifact `10369086459`;
- artifact SHA-256 `f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8`;
- upstream tests `5/5 PASS`;
- Lintian error gate PASS;
- SONAME `libKF6Plotting.so.6` PASS;
- consumer CMake/build/runtime smoke PASS;
- consumed ECM `6.30.0-0supralinux3`.

### BluezQt — real FAIL, not BLOCKED

- job `104151532330`;
- attempted package `6.30.0-0supralinux1`;
- artifact `10369725265`;
- artifact SHA-256 `ab85b1c2eeef6bf2dc9d622d6695b95427cca6e246ac13a0f825034e9e63d195`;
- upstream build succeeded;
- upstream tests `18/18 PASS`;
- failure stage: `sbuild` Lintian gate.

The sole Lintian error was `symbols-file-contains-current-version-with-debian-revision` for `_ZSt19piecewise_construct@Base` in `libKF6BluezQt.so.6`. `dpkg-gensymbols` observed this libstdc++ implementation/toolchain export in the KDE 6.30 build and assigned the package revision `6.30.0-0supralinux1` as its minimum version. The five older `_Rb_tree` template-instantiation symbols missing from the build are already optional in the retained Debian baseline and are not the failure cause.

BluezQt is therefore a real independent FAIL. KItemModels and KPlotting remain valid PASS results; neither is invalidated or reclassified.

## BluezQt remediation for attempt 2

The fix is deliberately limited to symbols policy; no KDE dependency or upstream source change is justified by the evidence.

`debian/apply-symbols-delta.py` verifies the exact retained Debian 6.28 baseline SHA-256 `b72bea28842160da234b3bbab7975623616cd58f3e522b1e5d8705a279eef4f7`, inserts exactly one reviewed line:

`(optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0`

and verifies the transformed symbols file SHA-256 `0fd10c9d93b303fa48aa5cd66aaf4727fbc27f4b784926f5ce5f8d20606bf37a` before replacing the build-time symbols file. The transform itself has SHA-256 `6e7f4a36c5b5b71c80728c23da82180af0772b4d9abf2f3feb834ffda0007565`.

This follows the already proven SupraLINUX policy used for reviewed implementation/toolchain symbols: implementation-only exports are not promoted into a mandatory public ABI contract, while the Debian 6.28 public ABI baseline remains intact.

BluezQt revision `6.30.0-0supralinux2` must pass a fresh clean build, all upstream tests, Lintian, SONAME checks and consumer smoke before it can become PASS.

## CI scope

The Batch 3 delta detector fingerprints only inputs consumed by each node. Recording PASS/FAIL evidence does not rebuild unrelated nodes. The BluezQt package revision and package metadata change affect only the BluezQt fingerprint, so KItemModels and KPlotting are intentionally skipped on the remediation commit.

## Canonical Tier 1 state before Batch 3 closure

The per-node attempt ledger now contains two valid PASS results and one current FAIL/remediation, but canonical promotion remains atomic at Batch 3 closure. Therefore the canonical Tier 1 manifest remains **7 PASS / 22 pending / 0 current FAIL / 0 BLOCKED** until all three Batch 3 nodes have valid PASS evidence.

If BluezQt attempt 2 passes and the closure validators pass, Batch 3 can be promoted to **10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED**. The BluezQt attempt-1 FAIL remains preserved as historical evidence.
