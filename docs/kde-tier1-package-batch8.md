# KDE Frameworks Tier 1 Batch 8 — KGuiAddons

Status: **remediation pending after successful package build / consumer-harness closure FAIL**  
Date: **2026-09-17**  
Frameworks: **6.30.0**

## Scope and authority

Batch 8 contains one pending Tier 1 node: `kguiaddons`. KDE upstream 6.30.0 is authoritative.

- source: `https://download.kde.org/stable/frameworks/6.30/kguiaddons-6.30.0.tar.xz`
- source SHA-256: `e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d`
- current package revision: `6.30.0-0supralinux2`

The retained Debian 6.28 packaging tree from run `34708030450`, artifact `10301938362`, is only a technical package-layout/symbols/copyright reference. It does not define KDE version, Qt selection or enabled upstream features.

## Upstream defaults

SupraLINUX preserves the KGuiAddons Linux feature profile: Wayland, X11, DBus, the `geo:` handler, Python bindings and tests are enabled. QCH remains disabled by the common Frameworks packaging profile.

## KCoreAddons relationship

KGuiAddons remains a Tier 1 Framework. KCoreAddons is not a KGuiAddons Framework build dependency and `libkf6coreaddons-dev` remains absent from KGuiAddons `Build-Depends`.

The public `KImageCache` header includes KCoreAddons' `kshareddatacache.h`, so `libkf6guiaddons-dev` depends on `libkf6coreaddons-dev (>= 6.30.0~)`. The consumer smoke therefore uses the retained SupraLINUX KCoreAddons PASS only as a development/runtime consumer surface.

Retained KCoreAddons evidence:

- version `6.30.0-0supralinux4`;
- workflow run `35122522242`;
- artifact `10457958023`;
- artifact digest `sha256:c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`.

For consumer validation the exact retained closure now pins four packages:

- `libkf6coreaddons-data_6.30.0-0supralinux4_all.deb`: `f05f55e3c6486af9d3ff48aa38215784bbb347aae1cd5fb760f5513760364908`;
- `libkf6coreaddons-dev_6.30.0-0supralinux4_amd64.deb`: `9f6fa1d04c303a2466322c86b14dee9a301a442a34c26dd77e99440f186c9636`;
- `libkf6coreaddons6_6.30.0-0supralinux4_amd64.deb`: `015b8f19a909a2a7431b45235187f280c32790258052c8c08659e6ce510b11cb`;
- `qml6-module-org-kde-coreaddons_6.30.0-0supralinux4_amd64.deb`: `8c6f82ac7c0de500b8bda6c88d912b3fd8cb6b254cece402227d38d1fb782345`.

## Binary contract

Batch 8 expects seven KGuiAddons binary packages: `libkf6guiaddons-bin`, `libkf6guiaddons-data`, `libkf6guiaddons-dev`, `libkf6guiaddons-doc`, `libkf6guiaddons6`, `qml6-module-org-kde-guiaddons`, and `python3-kguiaddons`.

Runtime SONAME gate: `libKF6GuiAddons.so.6`.

## Attempt history

### Attempt 1 — preparation FAIL

Head `64585a32ce481350df188237b71b5354d9aec4a7`, router run `35182478592`, job `105077454579`, artifact `10480782714`, digest `sha256:690e29e1c44835c1568eaca7f950393fbd3487f03be050d1f4f47880bb107b9e`.

The materialized signing key did not match the manifest-pinned KGuiAddons key. Failure occurred before source-package creation; revision remained `6.30.0-0supralinux1`.

### Attempt 2 — retained predecessor hash FAIL

Head `6df438c345a10e679bc4f52d3bcfd427cb4fa603`, Repository Policy `35183197615` PASS, router run `35183198027`, job `105079635248`, artifact `10481500636`, digest `sha256:0011def5c3111d67266edc95bbd91b178057d3e65f8ff571e09e112d1658bf61`.

The retained KCoreAddons artifact was correct, but two copied inner SHA-256 pins were wrong. Failure occurred before source-package creation; revision remained `6.30.0-0supralinux1`.

### Attempt 3 — successful compile / symbols-Lintian FAIL

Head `a5d3d047b9c54a91f1c31dfe7bfcfb437e0f6963`, Repository Policy `35183595001` PASS, router run `35183595245`, job `105080827688`, artifact `10480549680`, digest `sha256:eee95d50f04a8517eca828cff25cd52e0306684cfc61137569b15fb89d402fcd`.

`sbuild` completed successfully and CTest was `9/9 PASS`, but Lintian rejected two symbols that `dpkg-gensymbols` had versioned with `6.30.0-0supralinux1`.

KDE upstream `v6.29.0` exposes `KSystemClipboard::ownsSelection()` and `ownsClipboard()` with `since 6.29`; `v6.28.0` contains neither. SupraLINUX therefore added the exact symbols overlay at minimum version `6.29.0`. Because this changed package ABI metadata after a real package build, the revision advanced to `6.30.0-0supralinux2`.

### Attempt 4 — valid package build / consumer-harness closure FAIL

Head `1680cc2a049965152f595bc80c8520f16a6675d8`, Repository Policy `35184831519` PASS, router run `35184831705`, job `105084559971`, artifact `10481459177`, digest `sha256:453d3e2ae75d8ea8e20d8af634869dd0f83dc9469d545692783f3aab0d9e5358`.

The package itself passed the gates reached before consumer installation:

- `sbuild`: successful;
- CTest: `9/9 PASS`;
- symbols remediation: effective;
- Lintian: no blocking errors;
- seven `6.30.0-0supralinux2` binary packages produced.

The failure occurred later at `consumer-runtime-closure`. The runner passed local paths for retained `libkf6coreaddons6`, QML and development packages to APT, but omitted the exact retained `libkf6coreaddons-data (= 6.30.0-0supralinux4)` required by `libkf6coreaddons6`. APT therefore could not resolve the local retained KCoreAddons closure; subsequent solver complaints were cascading consequences.

This is classified as a **validation-harness retained-consumer-closure failure after a successful KGuiAddons package build**, not a KGuiAddons build, test, ABI or dependency-model defect. No package metadata changes are required, so the KGuiAddons revision stays `6.30.0-0supralinux2`.

## Attempt 4 remediation

The workflow now verifies the exact retained `libkf6coreaddons-data` package against SHA-256 `f05f55e3c6486af9d3ff48aa38215784bbb347aae1cd5fb760f5513760364908`, confirms package name/version, and installs it before the existing Batch 8 runner executes. The post-run evidence records the installed package version and hash in the Batch 8 artifact.

This remediation changes only the validation harness and retained consumer closure. It does not add KCoreAddons to KGuiAddons `Build-Depends`, does not rebuild KCoreAddons, and does not bump the KGuiAddons package revision.

## Build/test gate

A real PASS still requires exact source and retained-input hashes, clean Resolute `sbuild`, non-zero 100% CTest PASS, Lintian source+binary error gate, seven-package contract, SONAME, Python import, exact APT runtime/development closure, KImageCache consumer CMake smoke and proof that KCoreAddons did not enter KGuiAddons Build-Depends.

## Promotion rule

Until a later Batch 8 run is a real PASS:

- canonical `manifests/kde-frameworks-tier1.json` remains `kguiaddons: pending`;
- KGuiAddons is not downstream-eligible;
- canonical Tier 1 remains `21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED`;
- Batch 8 remains `remediation-pending-build`.

Only a real PASS may promote KGuiAddons into the canonical Tier 1 manifest.
