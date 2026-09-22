# KDE Tier 3 support build level 0

Status: **pending CI**

Reviewed: **2026-09-22**

This is the first real binary-package gate for the Tier 3 support components.

Level 0 contains two independent nodes:

- Breeze Icons `4:6.30.0-0supralinux1`;
- KDocTools `6.30.0-0supralinux1`.

KDED is explicitly **BLOCKED**, not FAIL: its binary build is not attempted until KDocTools has produced a real downstream-eligible PASS artifact.

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
