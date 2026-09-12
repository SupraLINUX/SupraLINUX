# KDE stable dependency DAG

Status: **ECM root PASS; 4 Frameworks Tier 1 PASS; 25 Tier 1 pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-12**

## Authority

KDE upstream stable defines the KDE desktop, Frameworks versions and their dependency requirements. Ubuntu 26.04 is the platform/provider and compatibility target. A distro reference can help implement Debian packaging, but it does not select the KDE version.

Current selected snapshot:

- Plasma 6.7.5;
- KDE Frameworks 6.30.0;
- KDE Gear 26.08.1;
- KDE-selected Qt series 6.10;
- Ubuntu Resolute Qt 6.10.2 provider baseline: hosted preflight PASS, final provider certification pending.

Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1. That is a **technical packaging reference only**; KDE upstream 6.30.0 remains authority for SupraLINUX ECM.

## DAG semantics

- `PASS`: actually attempted and completed the defined gate; the retained artifact may feed dependents.
- `FAIL`: actually attempted and failed for its own cause.
- `BLOCKED`: not attempted because a required predecessor is FAIL.
- `pending`: not attempted yet.

`BLOCKED` is never counted as `FAIL`. Historical FAIL attempts remain evidence after a later revision reaches PASS.

Hosted PASS proves only the hosted clean-package gate for that artifact. The authoritative KVM/JIT lane, system/runtime tests and Ubuntu/third-party compatibility work remain separate release gates.

## Extra CMake Modules 6.30.0 — PASS

Source SHA-256: `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`.

Validated package: `extra-cmake-modules 6.30.0-0supralinux3`.

Attempt history:

1. `6.30.0-0supralinux1`, run `34689672632`, artifact `10296512341`, artifact SHA-256 `d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558`: **FAIL** at `dh_auto_test` because `BUILD_TESTING=OFF` removed the Ninja test target.
2. `6.30.0-0supralinux2`, run `34690027788`, job `103543538213`, artifact `10296517706`, artifact SHA-256 `89ef0003fd8282965a4c253bcd0150b8f040fe134ca0385d1365cd8c31808239`: **FAIL** at consumer smoke after packaging findings; the Qt consumer also lacked `qtpaths6`.
3. `6.30.0-0supralinux3`, run `34694951158`, job `103556722010`, artifact `10298635300`, artifact SHA-256 `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`: **PASS**.

The successful revision makes `lintian --fail-on error` fatal, carries required runtime/copyright metadata and supplies `qtpaths6` to the consumer environment. Retained `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

The ECM hosted preflight does not claim the full upstream test suite; broader test coverage is a separate quality gate.

## Tier 1 package state

### Attica — PASS

Validated revision `6.30.0-0supralinux2`, run `34706416753`, artifact `10301851297`, artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`. Tests: **6/6 PASS**. SONAME `libKF6Attica.so.6`. Consumer smoke PASS. Downstream eligible.

Its historical attempt 1 remains FAIL evidence: run `34705165994`, artifact `10300903114`, SHA-256 `171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300`.

### Batch 1 — 3/3 PASS

All three nodes depend only on the retained ECM PASS root and were built independently with `fail-fast: false`.

- **KCodecs**: `6.30.0-0supralinux4`, run `34716761551`, job `103615297758`, artifact `10305050385`, artifact SHA-256 `d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45`; tests **8/8 PASS**; Lintian error gate PASS; SONAME `libKF6Codecs.so.6`; consumer smoke PASS.
- **KDBusAddons**: `6.30.0-0supralinux3`, run `34713034164`, job `103605147881`, artifact `10304340428`, artifact SHA-256 `2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799`; tests **3/3 PASS**; SONAME `libKF6DBusAddons.so.6`; consumer smoke PASS.
- **ThreadWeaver**: `6.30.0-0supralinux3`, run `34713034164`, job `103605147772`, artifact `10303986419`, artifact SHA-256 `6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8`; tests **8/8 PASS**; SONAME `libKF6ThreadWeaver.so.6`; consumer smoke PASS.

KCodecs uses the newer retained Debian 6.28 symbols reference because it already reflects the two removed `KCharsets` constructors. Fifteen compiler/libstdc++ implementation symbols emitted by KDE 6.30's `std::format` use were reviewed and tagged `(optional=toolchain)` with upstream minimum `6.30.0`; a Debian revision is not used as a symbols minimum.

## Scope incident — infrastructure only

Run `34716761551` also selected already-PASS KDBusAddons and ThreadWeaver due an over-broad first semantic fingerprint. Jobs `103615297686` and `103615297757` aborted at `campaign-validation` with “got PASS”, before source-package assembly or `sbuild`. Their tiny artifacts `10305410248` (`ce17097096841a500ce8b2e4f24171253b91ba1dce4a6560d0107d626eb32b1a`) and `10304955612` (`79e5393b892ae1ee3fb9a19c21e2f41bb691c7c55bf40487bb2d5de7c42fc507`) are retained as infrastructure-scope evidence and **do not create package FAILs**.

The corrected selector fingerprints only values actually consumed by the package runner. State, evidence, PASS hashes and descriptive metadata cannot request a rebuild.

## Current state and next expansion

Current Tier 1 totals are **4 PASS, 25 pending, 0 current FAIL, 0 BLOCKED**. Only retained PASS artifacts may feed later tiers.

Batch 2 should select another independent low-dependency group from the remaining 25 Tier 1 nodes, keeping package-specific symbols, binary contracts, optional features, tests and consumer smokes explicit.
