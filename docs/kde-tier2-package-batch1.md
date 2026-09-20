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

## Attempt 1 — source-package FAIL

Run `35496293561`, job `106039776267`, artifact `10600690671`, SHA-256 `8387279d8cdadd05cf73c2c16177f1d2635a331648638ca3397cef77d04c1ac3`.

The attempt failed in `dpkg-source` before sbuild. The helper-install-dir patch declared a seven-line hunk but ended after six context lines, so quilt rejected it as malformed. Retained predecessor artifacts, source SHA, backend profile and Debian symbols reference all validated before this failure.

Classification: **real package FAIL**, `package_attempted=true`, stage `source-package`, `sbuild_started=false`. Revision `6.30.0-0supralinux2` fixes only the quilt hunk structure.

## Attempt 2 — symbols contract FAIL after tests PASS

Run `35496445770`, job `106040197856`, artifact `10601410551`, ZIP SHA-256 `4ea7588f1749ce7588cc06fc6bc9dc80350d7fc270bb30688ef173ee6262cfc9`, rootfs SHA-256 `bf90d45c1b750369d482757a4521ea3578a5ef8e10835bf008b258ffad49cbcf`.

The corrected source package built through configuration/compilation and upstream CTest reported **6/6 PASS**. Both selected plugins were installed: PolkitQt6-1 authorization backend and DBus helper backend. Packaging then failed in `dh_makeshlibs`.

The pinned Debian 6.30 symbols template SHA-256 is `77ab200ea8f5e9335831ef021dd2e446598b95d886d13237e91ea69e25812259`. Two missing C++ template instantiations were already tagged `optional=templinst` and were not causal. The only mandatory missing entries were RTTI/vtable symbols for `KAuth::AuthBackend::Private`, which is defined only in `src/AuthBackend.cpp`.

Revision `6.30.0-0supralinux3` keeps the complete Debian 6.30 symbols baseline and changes exactly those two implementation-private entries to `optional=private`. No public ABI symbol is weakened.
