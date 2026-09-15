# KDE Frameworks 6.30 Tier 1 — package Batch 5

Status: **prepared; package attempts pending**  
Last reviewed: **2026-09-15**

## Selection

Batch 5 selects three independent Tier 1 nodes whose only KDE DAG predecessor is the retained ECM PASS and whose ABI surface fits the current single-primary-library runner:

- KIdleTime;
- ModemManagerQt;
- NetworkManagerQt.

This is a campaign preparation state. None of these nodes is promoted to canonical PASS until a real clean `sbuild` attempt completes all package gates and its evidence is retained.

Canonical Tier 1 therefore remains **13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED** while the batch is open.

## Why these nodes

Each selected node has one primary shared-library SONAME and one Debian symbols baseline. The existing runner already supports multiple binary packages around that primary ABI, so NetworkManagerQt's QML binary package does not require a multi-library ABI extension.

Deferred from this batch:

- KConfig: multiple ABI libraries/symbol files;
- KI18n: multiple ABI libraries/symbol files;
- Sonnet: multiple libraries plus plugin surface;
- KCoreAddons, KGuiAddons and KWidgetsAddons: default-enabled Python binding surface while simpler nodes remain;
- Kirigami and KQuickCharts: QML/Quick-heavy package surfaces better handled in a later lane.

## Provider inputs

KDE upstream 6.30.0 remains authority. Ubuntu Resolute only supplies providers.

The ModemManager mapping was revalidated before opening this batch. KDE requests `ModemManager >= 1.0` through pkg-config module `ModemManager`; Ubuntu Resolute supplies that interface with `modemmanager-dev`.

Targeted provider evidence:

- workflow run `35012023822`;
- job `104526071758`;
- commit `48fd01bfa7b254b5e5c8447b3d609f76a91f786f`;
- artifact `10414525047`;
- artifact SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`;
- result: PASS;
- authority claim: none; provider-availability evidence only.

## Package profiles

### KIdleTime

Retains KDE's Linux X11 and Wayland defaults. The clean build includes the XSync/XScreenSaver and Wayland provider surfaces used by upstream. QCH is disabled by the common SupraLINUX Frameworks profile; autotests run under Xvfb rather than being disabled.

Primary ABI: `libKF6IdleTime.so.6`.

### ModemManagerQt

Uses `modemmanager-dev` as the Ubuntu provider for KDE's `ModemManager >= 1.0` requirement. Tests run under a private D-Bus session. QCH alone is disabled.

Primary ABI: `libKF6ModemManagerQt.so.6`.

### NetworkManagerQt

Keeps the upstream QML module enabled and preserves the established `qml6-module-org-kde-networkmanager` binary package contract. `libnm` and GIO are explicit direct build inputs because KDE's CMake calls both pkg-config modules directly.

Only `managertest`, `settingstest` and `activeconnectiontest` are excluded in the isolated package lane because they require a live NetworkManager service. All other upstream tests remain enabled. This is an integration constraint, not a KDE feature disablement.

Primary ABI: `libKF6NetworkManagerQt.so.6`.

## Gates

Every node must independently complete:

1. KDE 6.30.0 source SHA-256 verification;
2. retained ECM PASS verification;
3. retained Debian 6.28 symbols/copyright reference verification;
4. source package creation;
5. clean Ubuntu 26.04 `sbuild` with tests;
6. exact binary package contract checks;
7. SONAME check;
8. source/binary Lintian error gate;
9. downstream CMake + `dlopen` consumer smoke;
10. retained artifact/evidence upload.

A failed node is `FAIL` only if it was actually attempted and failed by its own cause. Independent nodes continue. No node in this open batch is `BLOCKED` unless a required predecessor becomes FAIL.

PR #1 remains Draft. No merge is authorized.
