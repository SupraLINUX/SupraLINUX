# KDE Frameworks Tier 2 dependency map

Status: **inventory corrected; KAuth PASS; 14 nodes pending**  
Series: **6.30.0**  
Date: **2026-09-20**

## Upstream scope

The current KDE Tier 2 inventory contains 15 Frameworks. The initial SupraLINUX discovery covered only KAuth and KMime; the dependency map is now expanded to the complete upstream Tier 2 set.

Required KDE Framework edges below are taken from the upstream `v6.30.0` CMake configuration. Conditional/optional dependencies are recorded separately because they require provider/profile decisions before packaging.

## Required Framework edges

| Node | Required KDE Framework dependencies | Conditional / selected Framework dependencies |
| --- | --- | --- |
| KAuth | KCoreAddons | KWindowSystem selected by the real PolkitQt6-1 Linux profile |
| KColorScheme | KConfig, KGuiAddons, KI18n | — |
| KCompletion | KCodecs, KConfig, KWidgetsAddons | — |
| KContacts | KI18n, KConfig, KCodecs | — |
| KCrash | KCoreAddons | — |
| KDeclarative | KI18n, KConfig, KGuiAddons | KGlobalAccel, KWidgetsAddons conditional |
| KFileMetaData | KI18n | KArchive, KCoreAddons, KConfig, KCodecs conditional |
| KNotifications | KConfig | provider/platform feature audit pending |
| KPackage | KArchive, KI18n, KCoreAddons | KDocTools optional |
| KPty | KCoreAddons, KI18n | UTEMPTER is an external optional provider |
| KService | KConfig, KCoreAddons, KI18n | KDocTools optional |
| KStatusNotifierItem | KWindowSystem | X11/platform surface is conditional |
| KUnitConversion | KI18n | Python bindings are conditional |
| Syndication | KCodecs | — |
| KMime | KCodecs | compatibility architecture decision required |

Every required KDE predecessor for the 13 newly discovered non-KMime nodes is already a retained Tier 1 PASS artifact. Consequently, KMime is not a build predecessor for them and its ADR-0002 decision does not make them BLOCKED.

## KAuth retained materialized edge

KAuth's selected build profile is:

`ECM -> KCoreAddons + KWindowSystem + Qt Gui/DBus + PolkitQt6-1 -> KAuth`.

Retained local inputs:

- ECM `6.30.0-0supralinux3`, artifact `10298635300`;
- KCoreAddons `6.30.0-0supralinux4`, artifact `10457958023`;
- KWindowSystem `6.30.0-0supralinux4`, artifact `10428130399`.

Resolute's `libpolkit-qt6-1-dev 0.200.0-4ubuntu1` satisfies upstream's minimum 0.112.0. The selected profile uses `POLKITQT6-1` + DBus and forbids silent Fake fallback.

KAuth `6.30.0-0supralinux3` is retained PASS/downstream-eligible from run `35497461178`, job `106043001431`, artifact `10601382235`.

## Conditional/provider audits still required

KDeclarative and KFileMetaData must not be materialized from their minimum required edges alone. Their upstream CMake exposes conditional Framework surfaces that may become enabled when the corresponding providers are available.

KNotifications, KFileMetaData, KPty, KStatusNotifierItem and KUnitConversion also expose platform/external optional capabilities. SupraLINUX must determine the intended upstream-compatible Linux profile from actual Resolute provider availability before freezing their package contracts.

Optional KDocTools use in KPackage/KService is not a required Tier 2 predecessor and must be treated according to the selected docs profile rather than converting those nodes to BLOCKED.

## KMime

KMime's direct build edge is:

`ECM -> KCodecs + Qt Core -> KMime`.

KCodecs is already retained PASS. ADR-0002 exists because the Frameworks 6.30 package/runtime namespace differs from Ubuntu Resolute's PIM KMime; this is a compatibility-transition problem, not a missing build predecessor.

No KMime packaging is authorized until that architecture decision is approved.

## Current state

Tier 2 is **1 PASS / 14 pending / 0 current FAIL / 0 BLOCKED**.

KAuth is the sole promoted Tier 2 node. Thirteen additional non-KMime nodes are package-lane-pending, and KMime is compatibility-decision-required.


## Provider profiles for audit batch 2

The next audit batch now has explicit upstream-derived provider profiles rather than placeholder Framework edges. The selected Linux profile preserves BUILD_TESTING for all five nodes; selects KPty UTEMPTER, KCompletion's native designer plugin, KContacts QML, and KPackage DBus; and follows KColorScheme's Qt 6.10+ GuiPrivate branch.

Ubuntu remains only the provider. In particular, KPackage's optional KF6DocTools probe is not allowed to pull an older Ubuntu KDE Framework into the 6.30 stack; the optional documentation path remains off until SupraLINUX has a compatible KDE-upstream provider.

The audit failure in run `35597828609` is classified as a pre-provider profile-definition incident with `package_state_effect=none`; no package and no provider availability claim was produced.


## 2026-09-21 — final provider-audit batch profile corrections

Upstream v6.30.0 was re-read before the final provider audit. Two dependency classifications are corrected:

- KDeclarative requires KGlobalAccel on Linux desktop platforms and KWidgetsAddons on non-Android builds; SupraLINUX selects both retained 6.30 providers.
- KFileMetaData marks KCoreAddons and KCodecs REQUIRED through its upstream feature summary. KArchive and KConfig remain optional upstream, but SupraLINUX selects them because compatible retained 6.30 providers are already available.

Provider audit batch 3 is KService + KDeclarative + KFileMetaData. KService audits Qt Xml/Concurrent/Test while refusing an older distro KDocTools provider. KDeclarative audits Qml/Quick/Gui/Test. KFileMetaData audits required Linux Xattr plus optional Poppler Qt6, TagLib, Exiv2, FFmpeg, EPub, CatDoc, QMobipocket6 and libappimage candidates. Optional extractor candidates remain optional until provider evidence exists.
