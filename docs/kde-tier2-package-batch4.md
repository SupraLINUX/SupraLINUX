# KDE Tier 2 Package Batch 4

Status: **closed — 3/3 PASS**

Batch 4 contains exactly **KDeclarative, KFileMetaData and KService** from KDE Frameworks 6.30.0. Canonical Tier 2 remains **11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until clean-package evidence is promoted.

All three source trees are deterministic materialization PASS and remain `package_attempted=false`. Batch 4 is the first real package-attempt lane for these materializations.

## Dependency inputs

The clean builds consume only retained SupraLINUX PASS artifacts plus Ubuntu Resolute non-KDE platform dependencies.

- **KDeclarative:** KI18n, KConfig, KGuiAddons, KGlobalAccel and KWidgetsAddons are direct KDE predecessors. **KCoreAddons is an explicit package-level closure input** because the retained `libkf6guiaddons-dev` package depends on `libkf6coreaddons-dev`.
- **KFileMetaData:** KI18n, KCoreAddons, KCodecs, KArchive and KConfig. No additional KDE package closure is required.
- **KService:** KConfig, KCoreAddons and KI18n. No additional KDE package closure is required.

ECM `6.30.0-0supralinux3` is shared by all nodes. Every retained `.deb` is validated by exact Package, Version and SHA-256 before sbuild. The resulting `.buildinfo` must prove the exact retained dev-package versions, including the KCoreAddons closure for KDeclarative.

## Required gates

A node reaches PASS only after:

- clean Ubuntu Resolute `sbuild`;
- a positive non-zero upstream CTest summary;
- exact expected binary package set;
- Lintian with no errors;
- primary ABI/SONAME validation with non-empty exports;
- APT runtime closure and `apt-get check`;
- external CMake consumer build/run;
- exact predecessor buildinfo proof;
- exact package-level closure buildinfo proof when applicable.

KDeclarative has two additional gates:

1. all four declared QML packages must contain a `qmldir` payload;
2. `libkquickcontrolsprivate0` must contain an ELF with SONAME `libkquickcontrolsprivate.so.0` and non-empty exports.

The campaign uses `fail-fast: false`. A pre-sbuild infrastructure failure is **INFRA**, not package FAIL. **BLOCKED is not FAIL**. Package FAIL requires a real sbuild attempt and a node-owned root cause.

PASS only makes a package eligible for the testing repository. Promotion to the **stable** APT channel always requires explicit user approval.


## First clean-build campaign — classification

Run `35676553259` used one validated retained-input bundle and one shared clean Resolute rootfs.

**KFileMetaData PASS**
- job `106584347249`
- artifact `10673811173`
- artifact SHA-256 `1ecb8d7a94650ee810a6424d9eeffb9d176d0a30ad9b75ed6b3257538fa1ba30`
- **31/31 upstream tests PASS**
- SONAME `libKF6FileMetaData.so.3`, 193 exports
- Lintian PASS-errors
- APT closure and external CMake consumer PASS
- exact KI18n, KCoreAddons, KCodecs, KArchive and KConfig buildinfo proof PASS.

KFileMetaData is promoted immediately and downstream-eligible.

**KDeclarative INFRA / package state unchanged**

The clean package build itself succeeded, **1/1 upstream test passed**, Lintian had no errors, and exact predecessor plus KCoreAddons package-closure proofs passed. The post-build extra-ABI gate incorrectly followed the `libkquickcontrolsprivate.so.0` symlink and counted the symlink and its versioned target as two ELF files.

The validator is corrected rather than changing the package: it now requires exactly one SONAME symlink, verifies that its target exists, skips symlinks during ELF scanning, and requires exactly one real ELF with SONAME `libkquickcontrolsprivate.so.0` and non-empty exports. KDeclarative is retried with the same deterministic materialization.

**KService INFRA / selective rematerialization**

The clean package build succeeded with **7/7 upstream tests PASS** and primary ABI `libKF6Service.so.6` with 299 exports. Lintian then rejected `_ZSt19piecewise_construct@Base` because the Resolute C++ toolchain emits this standard-library implementation symbol while the Debian 6.30 baseline does not list it; `dpkg-gensymbols` consequently assigned the current SupraLINUX Debian revision.

The remediation is explicit and narrow:

`(optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0`

This follows the already validated SupraLINUX policy used for toolchain-emitted libstdc++ symbols: the symbol is optional/toolchain-dependent and receives the upstream Frameworks version, never a Debian revision minimum. KService is rematerialized and rebuilt; no KDE feature is disabled.

After promoting KFileMetaData, canonical Tier 2 is **12 PASS / 3 pending / 0 current FAIL / 0 BLOCKED**. Neither infrastructure/integration incident changes KDeclarative or KService to FAIL.


## KDeclarative retry PASS and KService rematerialization PASS

The corrected post-build ABI gate was exercised by run `35677466571`, job `106587017706`.

KDeclarative `6.30.0-0supralinux1` is now **PASS**:
- artifact `10673008440`
- artifact SHA-256 `8433514ef2032988d815a7577431395489d7a62ad57b250aefb90e0982acb44d`
- **1/1 upstream test PASS**
- primary SONAME `libKF6CalendarEvents.so.6`, 50 exports
- Lintian PASS-errors
- APT closure and external CMake consumer PASS
- exact direct-predecessor and KCoreAddons package-closure buildinfo proofs PASS
- all four declared QML packages contain `qmldir`
- `libkquickcontrolsprivate0` has SONAME symlink `libkquickcontrolsprivate.so.0 -> libkquickcontrolsprivate.so.6.30.0`
- the real private ELF has SONAME `libkquickcontrolsprivate.so.0` and 11 exports.

KService selective rematerialization also passed in run `35677466559`, job `106586918751`, artifact `10673841912`, SHA-256 `c75ae3d4fd2960333fc9db6403282631140cbc9a81031934d04717092aeadf0b`. The reviewed toolchain symbol baseline is now part of the deterministic Debian tree. No package attempt occurred during materialization.

Canonical Tier 2 is therefore **13 PASS / 2 pending / 0 current FAIL / 0 BLOCKED**. KService is build-ready; KMime remains decision-gated.


## Final KService clean build — PASS

Run `35681046106`, job `106598026738`, closes Batch 4.

KService `6.30.0-0supralinux1`:
- artifact `10674773768`
- artifact SHA-256 `5777d006748c9560b2e0c0935d0e20a31226c79106f3bd28c523c4c8b39b8d0d`
- rootfs artifact `10675063037`, artifact SHA-256 `e56a788c91b67ff196010f0c2affaf7af74ebabb8dab4d1f9210361a0758d432`
- rootfs SHA-256 `5135c9e4142d6378f4f824b8cf206532b8ff223e9f549305cabd04c1f71b0c2b`
- **7/7 upstream tests PASS**
- SONAME `libKF6Service.so.6`, 299 exports
- Lintian PASS-errors
- APT closure and external CMake consumer PASS
- exact KConfig `6.30.0-0supralinux4`, KCoreAddons `6.30.0-0supralinux4` and KI18n `6.30.0-0supralinux1` buildinfo proof PASS
- the reviewed `(optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0` symbols baseline is present in the built source tree.

Batch 4 is therefore **3/3 PASS**: KDeclarative, KFileMetaData and KService are downstream-eligible. Their earlier INFRA events remain historical evidence and are not rewritten as package FAIL.

Canonical Tier 2 is now **14 PASS / 1 pending / 0 current FAIL / 0 BLOCKED**. The sole pending node is KMime under ADR-0002.
