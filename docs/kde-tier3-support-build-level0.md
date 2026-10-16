# KDE Tier 3 support build level 0

Status: **PASS**

Reviewed: **2026-09-22**

This is the first real binary-package gate for the Tier 3 support components.

Level 0 contains two independent nodes:

- Breeze Icons `4:6.30.0-0supralinux1`;
- KDocTools `6.30.0-0supralinux1`.

KDED was explicitly **BLOCKED**, not FAIL, while level 0 was pending. KDocTools is now PASS, so KDED is unblocked for level 1.

## Inputs

Both nodes consume the promoted materialized source artifacts from run `35698463205`.

The clean Resolute build uses only retained PASS KDE artifacts where KDE 6.30 is required:

- Extra CMake Modules `6.30.0-0supralinux3`;
- KArchive `6.30.0-0supralinux4` for KDocTools;
- KI18n `6.30.0-0supralinux1` for KDocTools.

The workflow validates every retained binary package name, version and SHA-256 before sbuild, and proves the selected development packages in the resulting `.buildinfo`.

## PASS gates

A node becomes PASS only after:

- clean `sbuild` on Ubuntu 26.04 Resolute;
- a positive non-zero upstream CTest summary;
- exact binary-package set and version;
- SONAME and non-empty ABI export validation;
- Lintian with no errors;
- install/upgrade closure plus `apt-get check`;
- CMake consumer configure/build/run against the installed 6.30 development package;
- node-specific payload validation.

Breeze additionally verifies its primary package payload, RCC payload, Breaks/Replaces transition and dependency-only Ubuntu-name transitional packages.

KDocTools verifies `meinproc6`, `checkXML6` and the installed DocBook customization payload.

Artifacts retain `.deb`, `.ddeb`, `.changes`, `.buildinfo`, source package files, logs and SHA-256 evidence.

PASS makes a node downstream-eligible for the next DAG level. It does not authorize promotion to the stable repository; stable still requires explicit user confirmation.


## PASS evidence — 2026-09-22

Workflow run `35700002095` completed both independent nodes from commit `ae9885dc0bf03447c9550b3a511466e2234e8f8c`.

- **Breeze Icons** — job `106656021938`, artifact `10682012012`, artifact SHA-256 `daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577`; 4/4 upstream tests PASS; Lintian PASS-errors; `apt-get check` PASS; consumer smoke PASS; Breeze primary/RCC/Ubuntu-transition payload contract PASS; SONAME `libKF6BreezeIcons.so.6`, 1 exported symbol.
- **KDocTools** — job `106656022342`, artifact `10682066198`, artifact SHA-256 `6daeb6beed63ba7b7e441dba4dfd356be3ad48a9f3ae75acddae0945c36a683d`; 3/3 upstream tests PASS; Lintian PASS-errors; `apt-get check` PASS; consumer smoke PASS; `meinproc6` / `checkXML6` / DocBook payload contract PASS; SONAME `libKF6DocTools.so.6`, 6 exported symbols.

Both builds used the same clean Resolute rootfs SHA-256 `e649388bcf5e02372714f59dde3579cf0c9c9f2e42a2f94bd4a358f9a8a8811e`. KDocTools' buildinfo proves `libkf6archive-dev=6.30.0-0supralinux4` and `libkf6i18n-dev=6.30.0-0supralinux1`; both builds prove ECM `6.30.0-0supralinux3`.

Breeze Icons and KDocTools are now downstream-eligible. KDED advances from BLOCKED to **READY** for support build level 1.
