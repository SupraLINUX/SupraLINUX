# KDE Tier 2 provider audit

Status: **Python/Clang provider revalidation pending; previous batch PASS retained**  
Reviewed: **2026-09-20**

## Scope

The provider audit is the cheap gate between upstream dependency discovery and package-contract materialization. It checks the selected Linux profile against Ubuntu 26.04 Resolute providers before any clean package build.

It is **not a package PASS** and it never changes a node to FAIL merely because the package itself has not been attempted.

The first generated batch is KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication.

## Upstream-selected profiles

KCrash keeps `WITH_X11=ON` and `BUILD_TESTING=ON`. X11 is therefore a selected provider, not an optional SupraLINUX feature.

KNotifications keeps Linux DBus support and Python bindings enabled. Canberra is required by the upstream Linux profile. Qt QML remains an optional upstream component and is reported separately rather than promoted to a hard dependency.

KStatusNotifierItem keeps DBus enabled, does not set `WITHOUT_X11`, and keeps Python bindings enabled.

KUnitConversion keeps Python bindings and tests enabled.

Syndication keeps tests enabled; its test surfaces add Qt Test and Network to the provider audit.

## Provider registry

Qt and common external provider mappings are inherited from the already validated Tier 1 dependency registry. Tier 2 adds only providers not already represented there; the current addition is `libcanberra-dev`.

## Evidence contract

The hosted Ubuntu 26.04 audit records manifest/input SHA-256 values, apt candidate and installed versions, selected Linux profiles and retained Tier 1 predecessors, Qt/PySide alignment, Canberra discovery, Python build providers, a CMake discovery probe, and `result.json` with `package_state_effect=none`.

Only after this provider audit is PASS may these nodes become package-contract-ready. A later real clean package build is still required for PASS.


## Batch 1 PASS evidence

Ubuntu Resolute provider audit run `35524034558`, job `106112947247`: **PASS**.

- artifact: `10609298463`
- artifact SHA-256: `8418ca46593df82cdfb6ac306bcebbf97cde44f79db133f704b09e525f01a63d`
- Qt: `6.10.2`
- PySide6/Shiboken6: `6.10.2`
- X11 provider: `libx11-dev 2:1.8.13-1`
- Canberra provider: `libcanberra-dev 0.30-18ubuntu3`
- optional Qt QML provider was available but remained optional
- package state effect: **none**

KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication are now **package-contract-ready**. All five remain package-state `pending`.


## Supplemental Shiboken/Clang provider revalidation

The clean Batch 2 run proved that `llvm-dev` alone is insufficient for Shiboken: `llvm-config` becomes visible, but `/usr/lib/llvm-21/lib/clang` has no versioned builtin-resource directory. Resolute's provider closure is extended with `libclang-common-21-dev`.

The revalidation scope is only KNotifications, KStatusNotifierItem and KUnitConversion. CI must prove both `llvm-config` and `/usr/lib/llvm-21/lib/clang/21/include/stddef.h`. KDE's `BUILD_PYTHON_BINDINGS=ON` remains unchanged.


## Provider audit batch 2 — next five pending Tier 2 nodes

After Batch 2 package closure, the next generated provider-audit batch is `kpty`, `kcolorscheme`, `kcompletion`, `kcontacts` and `kpackage`. The audit remains provider/profile validation only: it verifies Ubuntu 26.04 Resolute can supply the Qt/external packages selected by KDE upstream 6.30.0 and that all retained Tier 1 predecessors are downstream-eligible PASS.

KDE Frameworks 6.30.0 remains the current upstream stable series as checked against KDE's official announcements and stable download index on 2026-09-21. The batch is recorded as `tier2-provider-audit-2`; provider-audit batch identifiers are now sequential instead of being hard-coded to the first batch.

A provider-audit PASS remains valid after a node later moves from package-contract/build-ready to retained package PASS. This fixes ownership of historical provider evidence without weakening the requirement that every currently audited node be in the generated campaign path.


### Batch 2 profile materialization correction

Provider-audit run `35597828609` did **not** prove a provider failure. It stopped in definition validation before APT probing because the five newly selected nodes still had only Framework dependency edges and no materialized Qt/external Linux profile.

The profile is now taken directly from KDE upstream v6.30.0 CMake:

- KPty: Qt Core; Qt Test for tests; UTEMPTER selected on Linux.
- KColorScheme: Qt Gui; Qt GuiPrivate selected because the Resolute provider is Qt 6.10.x; Qt Test for tests.
- KCompletion: Qt Widgets; native `BUILD_DESIGNERPLUGIN=ON` with Qt UiPlugin available; Qt Test for tests.
- KContacts: Qt Gui + Qml, upstream `USE_QML=ON`, QtQuick selected for the QML module dependency/integration surface, Qt Test for tests.
- KPackage: Qt Core, Linux-default `USE_DBUS=ON`, Qt Test for tests. Optional KF6DocTools is deliberately not supplied by an older Ubuntu KDE package.

The provider runner now generates its CMake probe from the active batch's mandatory Qt component set instead of probing a fixed first-batch component list. Private Qt components are checked through their dedicated CMake packages. KPty additionally probes the selected UTEMPTER header and library.


### Batch 2 active-profile rerun — runner optional-probe correction

Provider-audit run `35598315301`, job `106328176979`, reached real APT provider installation. The selected batch providers were available and installed, including `libutempter-dev 1.2.1-4build1`, Qt DBus/QML/Quick/Designer development surfaces and the Qt 6.10 private-Gui provider.

The run then failed in a stale first-batch-only runner assertion: it unconditionally queried `libshiboken6-dev` and `libpyside6-dev` even though neither package is part of this non-Python batch. This is **INFRA / audit-runner optional-probe leakage**, not a provider failure; `package_state_effect=none`.

Provider-specific probes are now conditional on membership in the active batch's generated `mandatory-packages.txt`. The same applies to the Python `build`/setuptools binding probe. This keeps the audit generic across later Tier 2 batches instead of carrying hidden requirements from the first Python-binding batch.
