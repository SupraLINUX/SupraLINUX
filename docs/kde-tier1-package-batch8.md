# KDE Frameworks Tier 1 Batch 8 — KGuiAddons

Status: **remediation pending; first real hosted attempt failed before source build**  
Date: **2026-09-17**  
Frameworks: **6.30.0**

## Scope

Batch 8 contains one pending Tier 1 node: `kguiaddons`.

KDE upstream 6.30.0 is authoritative. The selected source is:

- URL: `https://download.kde.org/stable/frameworks/6.30/kguiaddons-6.30.0.tar.xz`
- SHA-256: `e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d`
- SupraLINUX revision: `6.30.0-0supralinux1`

The Debian 6.28.0 packaging tree retained by run `34708030450`, artifact `10301938362`, is a technical reference only. It does not define the KDE version, required Qt version, enabled features or SupraLINUX package policy.

## Upstream defaults

KGuiAddons 6.30.0 requires Qt >= 6.9.0 and ECM 6.30.0. On Linux upstream enables by default:

- Wayland support;
- X11 support;
- DBus support;
- the `geo:` scheme handler;
- Python bindings;
- tests when `BUILD_TESTING` is enabled by the build profile.

SupraLINUX preserves those functional defaults. The common Frameworks packaging profile keeps QCH disabled, matching the current Batch 7 profile, but does not disable runtime or binding functionality.

## KCoreAddons distinction

KGuiAddons remains a KDE Frameworks **Tier 1** node. Its root CMake build does not use `find_package(KF6CoreAddons)` and Batch 8 therefore does **not** add `libkf6coreaddons-dev` to KGuiAddons `Build-Depends`.

There is nevertheless a real public development-surface relationship: upstream `KImageCache` includes `kshareddatacache.h` from KCoreAddons. Consequently `libkf6guiaddons-dev` depends on `libkf6coreaddons-dev (>= 6.30.0~)` so consumers of that public header receive the required development surface.

This is deliberately modeled as:

```text
KGuiAddons build DAG: Qt/external dependencies only
KGuiAddons -dev consumer surface: KCoreAddons development package required
```

It must not be rewritten as a false Framework build edge.

For the consumer smoke, Batch 8 uses the retained SupraLINUX KCoreAddons PASS:

- version `6.30.0-0supralinux4`;
- workflow run `35122522242`;
- artifact `10457958023`.

The runner verifies the retained `.deb` hashes before installation and checks that KCoreAddons did not enter KGuiAddons' sbuild Build-Depends closure.

## Binary contract

The preparation expects seven binary packages:

- `libkf6guiaddons-bin`;
- `libkf6guiaddons-data`;
- `libkf6guiaddons-dev`;
- `libkf6guiaddons-doc`;
- `libkf6guiaddons6`;
- `qml6-module-org-kde-guiaddons`;
- `python3-kguiaddons`.

The Python package is a SupraLINUX addition relative to the Debian 6.28 reference because KDE upstream 6.30 enables `BUILD_PYTHON_BINDINGS` by default and SupraLINUX does not disable that feature merely because the reference distribution did.

The runtime SONAME gate is `libKF6GuiAddons.so.6`.

## First real attempt — retained FAIL

The first real Batch 8 attempt ran from head `64585a32ce481350df188237b71b5354d9aec4a7` in PR router run `35182478592`, job `105077454579`.

The retained failure artifact is:

- artifact ID: `10480782714`;
- artifact digest: `sha256:690e29e1c44835c1568eaca7f950393fbd3487f03be050d1f4f47880bb107b9e`;
- result: `FAIL`;
- stage: `campaign-validation`;
- package revision: `6.30.0-0supralinux1`.

The failure happened before source-package creation and before compilation. The materialized `packages/kde/kguiaddons/debian/upstream/signing-key.asc` was the KCoreAddons reference key rather than the KGuiAddons reference key.

Expected KGuiAddons key SHA-256:

`86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d`

Incorrect materialized key SHA-256:

`5a0228357021204326d88472f29689b0ba25b29cd9ea4c97dab898a0aa4614d8`

This is classified as a **node preparation FAIL before source build**. It is not evidence of a KGuiAddons compile failure, upstream defect, dependency failure or KCoreAddons build-edge requirement.

Because no source package or binary package was produced, the remediation keeps revision `6.30.0-0supralinux1`.

## Remediation

The remediation replaces the incorrect key with the exact Debian KGuiAddons reference key from the retained packaging-tree artifact. The manifest-pinned hash remains unchanged because it was already correct.

Repository Policy is also hardened so `validate_kde_tier1_package_batch8.py` hashes the materialized signing key and requires it to match the manifest before an expensive Batch 8 build may run. This prevents the same preparation error from reaching the package runner again.

The attempt itself remains permanently recorded in `manifests/kde-tier1-package-batch8-attempts.json`; remediation does not erase or rewrite FAIL evidence.

## Second real attempt — retained FAIL

After the signing-key remediation, head `6df438c345a10e679bc4f52d3bcfd427cb4fa603` passed Repository Policy run `35183197615` including the new materialized signing-key hash gate. The second real Batch 8 attempt ran in PR router run `35183198027`, job `105079635248`.

Retained failure evidence:

- artifact ID: `10481500636`;
- artifact digest: `sha256:0011def5c3111d67266edc95bbd91b178057d3e65f8ff571e09e112d1658bf61`;
- result: `FAIL`;
- stage: `retained-input-validation`;
- package revision: `6.30.0-0supralinux1`.

The signing key, ECM predecessor, packaging-tree snapshot, KGuiAddons symbols reference and copyright reference all verified successfully. The failure occurred while validating the retained KCoreAddons PASS packages. Batch 8 had copied incorrect inner SHA-256 values for two files even though it referenced the correct retained artifact.

The authoritative retained KCoreAddons artifact remains workflow run `35122522242`, artifact `10457958023`, digest `sha256:c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`. Its own `artifact-sha256.txt` records:

- `libkf6coreaddons-dev_6.30.0-0supralinux4_amd64.deb`: `9f6fa1d04c303a2466322c86b14dee9a301a442a34c26dd77e99440f186c9636`;
- `libkf6coreaddons6_6.30.0-0supralinux4_amd64.deb`: `015b8f19a909a2a7431b45235187f280c32790258052c8c08659e6ce510b11cb`;
- `qml6-module-org-kde-coreaddons_6.30.0-0supralinux4_amd64.deb`: `8c6f82ac7c0de500b8bda6c88d912b3fd8cb6b254cece402227d38d1fb782345`.

The first two values replace the incorrect Batch 8 pins `b91b0fbb…` and `ce8063e6…`; the QML hash was already correct. The retained artifact itself did not change.

This is classified as a **retained-predecessor hash-pinning FAIL before source build**, not a KGuiAddons compilation, upstream, dependency or test failure. No source package was produced, so the package revision remains `6.30.0-0supralinux1`.

Repository Policy is hardened again: the Batch 8 validator now pins the retained KCoreAddons workflow run, artifact ID, artifact digest and all three exact package SHA-256 values so this class of copied-evidence error fails before an expensive build. Attempt 2 is preserved in the append-only Batch 8 ledger.

## Build/test gate

The hosted non-authoritative Batch 8 lane must prove all of the following before KGuiAddons may become downstream-eligible:

1. exact upstream source SHA-256;
2. exact KGuiAddons signing-key SHA-256;
3. exact retained ECM `6.30.0-0supralinux3` input;
4. clean Resolute `sbuild --chroot-mode=unshare`;
5. non-zero CTest summary with 100% PASS;
6. Lintian source+binary errors gate;
7. expected seven-package binary contract and Multi-Arch fields;
8. SONAME `libKF6GuiAddons.so.6`;
9. Python `KGuiAddons` import from the exact built package;
10. APT runtime/development closure using exact built KGuiAddons packages plus the retained KCoreAddons development surface;
11. consumer CMake build using `KF6::GuiAddons` and `KF6::CoreAddons`, including the `KImageCache` public header;
12. no KCoreAddons package in the KGuiAddons Build-Depends closure.

A later build failure is KGuiAddons `FAIL` only when the node was actually attempted and failed for its own package/build/test cause. Other nodes are unaffected; `BLOCKED` remains distinct from `FAIL`.

## Promotion rule

The first real attempt is retained FAIL evidence, not PASS evidence. Until a later Batch 8 run succeeds:

- canonical `manifests/kde-frameworks-tier1.json` remains `kguiaddons: pending`;
- KGuiAddons is not downstream-eligible;
- the Tier 1 canonical count remains `21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED` because the canonical snapshot is not promoted from a failed preparation attempt;
- the Batch 8 operational state is `remediation-pending-build`.

Only a real PASS may promote KGuiAddons into the canonical Tier 1 manifest.
