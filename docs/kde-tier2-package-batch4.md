# KDE Tier 2 Package Batch 4

Status: **prepared for clean-build campaign**

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
