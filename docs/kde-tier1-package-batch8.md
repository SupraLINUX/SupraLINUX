# KDE Frameworks Tier 1 Batch 8 — KGuiAddons

Status: **prepared; real hosted build pending**  
Date: **2026-09-17**  
Frameworks: **6.30.0**

## Scope

Batch 8 contains one pending Tier 1 node: `kguiaddons`.

KDE upstream 6.30.0 is authoritative. The selected source is:

- URL: `https://download.kde.org/stable/frameworks/6.30/kguiaddons-6.30.0.tar.xz`
- SHA-256: `e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d`
- initial SupraLINUX revision: `6.30.0-0supralinux1`

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

## Build/test gate

The hosted non-authoritative Batch 8 lane must prove all of the following before KGuiAddons may become downstream-eligible:

1. exact upstream source SHA-256;
2. exact retained ECM `6.30.0-0supralinux3` input;
3. clean Resolute `sbuild --chroot-mode=unshare`;
4. non-zero CTest summary with 100% PASS;
5. Lintian source+binary errors gate;
6. expected seven-package binary contract and Multi-Arch fields;
7. SONAME `libKF6GuiAddons.so.6`;
8. Python `KGuiAddons` import from the exact built package;
9. APT runtime/development closure using exact built KGuiAddons packages plus the retained KCoreAddons development surface;
10. consumer CMake build using `KF6::GuiAddons` and `KF6::CoreAddons`, including the `KImageCache` public header;
11. no KCoreAddons package in the KGuiAddons Build-Depends closure.

A failure in this real attempt will be recorded as KGuiAddons `FAIL` only if KGuiAddons was actually attempted and failed for its own package/build/test cause. Other nodes are unaffected; `BLOCKED` remains distinct from `FAIL`.

## Promotion rule

Preparation is not PASS evidence. Until the real Batch 8 build completes successfully:

- canonical `manifests/kde-frameworks-tier1.json` remains `kguiaddons: pending`;
- KGuiAddons is not downstream-eligible;
- the Tier 1 canonical count remains `21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED`.

If the first real build fails, preserve the failure evidence, fix the identified cause incrementally, bump the package revision where required, rerun, and only promote after a real PASS.
