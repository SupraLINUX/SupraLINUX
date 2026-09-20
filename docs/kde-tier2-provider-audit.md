# KDE Tier 2 provider audit

Status: **first batch PASS; package contracts not yet materialized**  
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
