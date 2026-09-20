# KDE Frameworks 6.30 — Tier 2 Batch 1 (KAuth)

Status: **prepared; first package attempt pending**  
Date: **2026-09-20**

Batch 1 deliberately contains only KAuth. KMime remains independently gated by ADR-0002 and does not block this runnable DAG node.

## Selected profile

- KAuth upstream: 6.30.0, SHA-256 `60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9`.
- ECM predecessor: retained SupraLINUX `6.30.0-0supralinux3`.
- KCoreAddons predecessor: retained SupraLINUX `6.30.0-0supralinux4`, artifact `10457958023`.
- KWindowSystem predecessor: retained SupraLINUX `6.30.0-0supralinux4`, artifact `10428130399`.
- Linux authorization backend: `POLKITQT6-1`.
- Helper backend: `DBUS`.
- Fake backend fallback: rejected for this profile.

The runner passes the retained Framework packages to the clean Resolute sbuild as exact local package inputs, so Ubuntu cannot satisfy the KAuth build by silently substituting an older KCoreAddons/KWindowSystem.

## Debian compatibility reference

Debian `kf6-kauth 6.30.0-1` is used only as a technical package-contract reference. Its `debian.tar.xz` is pinned at SHA-256 `f304bd772cf958ca9dccab78ad33e12f8e2f7bf0b038999e629cf270bb068fc3`. The runner imports the exact `libkf6authcore6.symbols` file from that pinned tarball before source-package assembly.

SupraLINUX keeps the Ubuntu/Debian binary package names:
`libkf6auth-data`, `libkf6auth-dev`, `libkf6auth-dev-bin`, `libkf6auth-doc`, `libkf6authcore6`.

## Gates

A PASS requires:
- non-zero upstream CTest suite fully passing under Xvfb + D-Bus session;
- real Polkit backend and DBus helper plugin present;
- `KF6AuthConfig.cmake` recording the selected backend profile;
- SONAME `libKF6AuthCore.so.6` and non-empty exported ABI;
- pinned symbols contract;
- development-contract audit;
- Lintian error gate;
- exact APT runtime closure using built packages plus retained predecessor packages;
- external CMake consumer compile/run.

No PASS evidence exists yet; this document is preparation state only.
