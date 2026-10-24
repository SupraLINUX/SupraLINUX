# KDE Tier 2 Package Batch 5

Status: **closed — PASS**

Batch 5 contains exactly **KMime** from KDE Frameworks 6.30.0. Canonical Tier 2 is now **15 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

The authoritative package is `kf6-kmime 6.30.0-0supralinux1`, producing `libkf6mime-data`, `libkf6mime-dev` and `libkf6mime6`. Its development/runtime contract is `KF6Mime` / `KF6::Mime` / `libKF6Mime.so.6`. KCodecs 6.30 is the only retained KDE predecessor.

Batch 5 uses the deterministic materialization PASS from run `35684824744`, artifact `10675444852`. A real package attempt begins immediately before `sbuild`; failures before that point are INFRA, not KMime FAIL.

PASS requires the standard clean-build gates plus the ADR-0002 compatibility gates. The built KF6Mime packages must not claim legacy `libkpim6mime6`, `libkmime-dev` or `libkmime-data` through fake `Provides`, `Replaces` or `Breaks`. After installing the built Frameworks packages, CI must install Ubuntu's legacy runtime `libkpim6mime6` + `libkmime-data` on demand and prove that both `libKF6Mime.so.6` and `libKPim6Mime.so.6` remain installed with a clean APT dependency state. The legacy development package is not installed by this runtime compatibility gate.

A Batch 5 PASS makes KMime downstream-eligible and eligible for the SupraLINUX **testing** repository only. Promotion to **stable** always requires explicit user approval.

## Activation

Batch 5 is **armed** for the real KMime clean build. The required **co-installation** gate explicitly tests the Frameworks runtime beside Ubuntu legacy KPim6Mime without claiming ABI equivalence. Arming the lane changes no package state; KMime remains pending until real build evidence is promoted.


## Attempt 1 — INFRA after successful KDE build

Run `35686463559`, job `106614505106`, made the first real KMime package attempt. KDE compiled and **17/17 upstream tests passed**. The package then stopped in `dh_makeshlibs` because Resolute GCC 15 emits a different set of C++ template/toolchain implementation symbols from the Debian 6.30 technical-reference baseline.

This is retained as **INFRA/post-sbuild**, not a canonical KMime FAIL: no KDE API or test failure was observed. The reviewed adaptation marks two `std::shared_ptr` RTTI/vtable template instantiations as `optional=templinst` while preserving their `arch=!riscv64` condition, and adds `_ZSt19piecewise_construct@Base` as `optional=toolchain` at upstream version `6.30.0`. No KDE feature is disabled.

Evidence artifact `10676184483`, SHA-256 `ab8027ff456dc8d7570fe17b90da2cfadec88d7763eeb04373d5ff8dcbdc4994`. Shared rootfs artifact `10676632838`, SHA-256 `3ef7c2ef0ce33dead1686293fa15003cda137001cd244d5fd527a31fe4737603`.

## Replacement materialization PASS

The first selective materialization attempt in run `35687009946` was interrupted before transformation by `curl (35) Recv failure: Connection reset by peer`; it is retained as network INFRA and changed no package state.

Run `35687009946`, attempt 2, job `106616152530` then produced the reviewed replacement tree: **PASS**, `package_attempted=false`.

- artifact `10677073138`, SHA-256 `539745b0f656efeed14c703f6cfb23670bfc8f79d07d270991dde5eafe2f6ea4`
- tree SHA-256 `eecfc8d314ff8ff9715c561c7c9be1c2c4c5f239ca6c563214eeaee33bf50ba6`
- Debian tree SHA-256 `65f384007ae703c2480b297cea68843fe32d11f5c6deb51eee9e2dc911559820`
- `.dsc` SHA-256 `f646a30a01e0bfce647cceb2869bb3316a2414f09a16c3d7c4f965690fd1a7b3`
- Debian tar SHA-256 `fa598699697f8a835f69935aab534da3e664f1eec955e6d56273495c8be878f3`
- KDE authority orig SHA-256 `2969a5ef484e98f91bf78e88c98a9d613bdd3bb86ac154ceece0557b70f373bc`.

KMime is again **build-ready** and remains package-state `pending`. Batch 5 is re-armed with only this replacement materialization.


## Attempt 2 — Frameworks build PASS, stock legacy provider blocks co-installation

Run `35687831684`, attempt 2, job `106619132039`, consumed the corrected replacement materialization.

The **KF6Mime side passed**:
- clean `sbuild` completed successfully;
- **17/17 upstream tests PASS**;
- Lintian completed with no errors;
- exact Frameworks binary set was produced;
- `libKF6Mime.so.6` ABI gate passed;
- APT runtime closure and external `KF6::Mime` CMake consumer passed;
- the no-fake-legacy-`Provides/Replaces/Breaks` gate passed.

The final compatibility gate exposed the actual remaining blocker. Requesting Ubuntu Resolute `libkpim6mime6 + libkmime-data` made APT remove `libkf6mime-data`, `libkf6mime-dev` and `libkf6mime6`. Therefore the stock Ubuntu legacy provider **cannot satisfy ADR-0002 co-installation as packaged**.

This is retained as **INFRA/integration compatibility evidence**, not a KMime source FAIL. Artifact `10677716050`, SHA-256 `ffd9f73bc684c4ca7e42f90448694381917dfd1d4ccf5f99f2d0629b17e6eb36`. KMime remains canonical `pending` and moves to `compatibility-provider-required`.

The next step is a provider audit of Ubuntu's exact binary metadata and payload overlap. No further Frameworks rebuild is valid until that audit identifies the minimal compatibility packaging adaptation.


## Compatibility audit and provider resolution

The integration incident from attempt 2 remains retained as historical `INFRA`; it was not rewritten as a successful stock-Ubuntu co-installation.

Compatibility audit run `35690284355`, job `106625630885`, artifact `10678073973`, SHA-256 `7b0c9175b1e0f48eb1d18e9ceb1af03381c4de8d0b322bc619dd7be224307c5b` proved that the conflict was confined to the data-package transition. `libKF6Mime.so.6` and `libKPim6Mime.so.6` are independent runtime payloads.

The selected provider was then built from the real legacy source as `25.12.3-0ubuntu1+supralinux1`. Run `35691309612`, build job `106628834481`, artifact `10679420779`, SHA-256 `f77517f13eab6a282d6050cb738f78b233a9392c076a23d54131073468d2ad4b` passed:
- clean sbuild and Lintian;
- exact legacy runtime/dev binary contract with no duplicate `libkmime-data`;
- co-installation beside the already-built KF6Mime packages;
- clean APT dependency state;
- legacy `KPim6::Mime` consumer;
- Frameworks `KF6::Mime` consumer.

## Batch 5 closed — KMime PASS

The final KMime package PASS is a **composite evidence claim**:
1. Frameworks build run `35687831684`, attempt 2, job `106619132039`, artifact `10677716050`, SHA-256 `ffd9f73bc684c4ca7e42f90448694381917dfd1d4ccf5f99f2d0629b17e6eb36` proves KF6Mime itself: 17/17 tests, Lintian, ABI, APT closure and `KF6::Mime` consumer.
2. The compatibility audit identifies the stock-provider root cause.
3. The SupraLINUX legacy provider proves real `libKPim6Mime.so.6` coexistence without changing the authoritative KF6Mime family.

KMime is therefore canonical **PASS/downstream-eligible**, and Tier 2 closes at **15 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

This closure authorizes eligibility for `testing` only. It does **not** authorize promotion to `stable`.
