# KDE Tier 3 support build level 1

Status: **pending CI**

Reviewed: **2026-09-22**

Level 1 contains only **KDED 6.30.0**. It became runnable only after KDocTools reached a real downstream-eligible PASS in support level 0.

## Dependency model

Direct KDE build predecessors are kept separate from package-install closure:

- direct: KConfig, KCoreAddons, KCrash, KDBusAddons, KService, KDocTools;
- package closure needed to install those exact 6.30 artifacts: KArchive and KI18n;
- common build-system root: Extra CMake Modules.

KArchive and KI18n are not promoted to direct KDED dependency edges merely because Debian package relationships require them transitively.

All inputs are retained SupraLINUX PASS artifacts with exact binary-package version and SHA-256 validation before sbuild.

## KDED-specific PASS gates

KDED does not ship a Framework library. The gate therefore does not invent a SONAME contract.

PASS requires:

- clean Resolute sbuild;
- positive non-zero upstream CTest summary;
- exact binary set: `kded6` + `kded6-dev`;
- buildinfo proof for all direct and closure development packages;
- executable ELF validation for `/usr/bin/kded6`;
- payload proof for systemd user service, DBus interface/service, desktop file, logging categories and documentation/manpage;
- proof that no KDED library unexpectedly appears;
- Lintian with no errors;
- installation closure and `apt-get check`;
- `kded6 --version` smoke;
- CMake consumer `find_package(KF6KDED 6.30 REQUIRED)` and live `KDED_DBUS_INTERFACE` path validation.

A KDED PASS closes the three-component support sub-DAG and allows Tier 3 package-contract/build planning to proceed. Stable publication remains gated by explicit user approval.
