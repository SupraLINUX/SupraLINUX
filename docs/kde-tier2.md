# KDE Frameworks 6.30 — Tier 2 discovery

Status: **1 PASS / 14 pending / 0 current FAIL / 0 BLOCKED**  
Date: **2026-09-20**

KDE upstream classifies **15** Frameworks in Tier 2 for the current Frameworks API set:

- KAuth
- KColorScheme
- KCompletion
- KContacts
- KCrash
- KDeclarative
- KFileMetaData
- KNotifications
- KPackage
- KPty
- KService
- KStatusNotifierItem
- KUnitConversion
- Syndication
- KMime

Tier 2 may depend on Tier 1 Frameworks. SupraLINUX entered this phase only after the canonical Tier 1 closure at **29 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

## Inventory correction

The first Tier 2 discovery incorrectly materialized only KAuth and KMime. That was an inventory error: KDE upstream currently lists 15 Tier 2 Frameworks.

The correction does not invalidate KAuth's retained PASS. It adds 13 previously omitted nodes as **pending** and changes the current canonical Tier 2 package state from the incomplete **1 PASS / 1 pending** view to **1 PASS / 14 pending / 0 current FAIL / 0 BLOCKED**.

No newly discovered node has been assigned a package version or package PASS/FAIL result. Their source identities and upstream v6.30.0 dependency edges are discovery evidence only until a package contract and real build lane are materialized.

## KAuth — retained PASS

Upstream 6.30.0 SHA-256: `60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9`.

KCoreAddons is always required. For the selected Linux production profile, PolkitQt6-1 is available, so KWindowSystem is also selected and the real Polkit backend is used rather than Fake.

SupraLINUX selects:

- retained KCoreAddons PASS;
- retained KWindowSystem PASS;
- `POLKITQT6-1` auth backend;
- `DBUS` helper backend;
- no silent Fake-backend fallback.

KAuth is **PASS/downstream-eligible** as `6.30.0-0supralinux3`. Retained evidence: run `35497461178`, job `106043001431`, artifact `10601382235`; 6/6 tests, Lintian error gate, ABI/symbols, APT closure, development contract and external consumer all PASS.

## Pending Tier 2 nodes that do not depend on KMime

The other 13 non-KMime pending Frameworks are not blocked by KMime. Their required KDE build edges in upstream `v6.30.0` terminate in retained Tier 1 nodes:

| Framework | Required Tier 1 Framework predecessors |
| --- | --- |
| KColorScheme | KConfig, KGuiAddons, KI18n |
| KCompletion | KCodecs, KConfig, KWidgetsAddons |
| KContacts | KI18n, KConfig, KCodecs |
| KCrash | KCoreAddons |
| KDeclarative | KI18n, KConfig, KGuiAddons |
| KFileMetaData | KI18n |
| KNotifications | KConfig |
| KPackage | KArchive, KI18n, KCoreAddons |
| KPty | KCoreAddons, KI18n |
| KService | KConfig, KCoreAddons, KI18n |
| KStatusNotifierItem | KWindowSystem |
| KUnitConversion | KI18n |
| Syndication | KCodecs |

KDeclarative additionally has conditional KGlobalAccel/KWidgetsAddons surfaces. KFileMetaData has optional/conditional KArchive/KCoreAddons/KConfig/KCodecs surfaces plus several external extractors. Those profiles must be audited before package materialization rather than silently disabling upstream-capable features.

KPackage and KService can optionally use KDocTools; that optional higher-tier documentation edge must not be confused with a required Tier 2 build predecessor.

All 13 are currently **package-lane-pending**, not FAIL and not BLOCKED.

## KMime — architecture decision required

Upstream 6.30.0 SHA-256: `2969a5ef484e98f91bf78e88c98a9d613bdd3bb86ac154ceece0557b70f373bc`.

Its Tier 1 build predecessor is KCodecs, already retained PASS. The blocker is compatibility architecture, not dependency availability.

Ubuntu Resolute still packages PIM KMime `25.12.3-0ubuntu1` as `libkpim6mime6` / `libkmime-dev`. Frameworks KMime changes the CMake and runtime namespace from `KPim6Mime` / `KPim6::Mime` / `libKPim6Mime.so.6` to `KF6Mime` / `KF6::Mime` / `libKF6Mime.so.6`.

Therefore KMime remains **compatibility-decision-required** under ADR-0002. No package version, Provides/Replaces/Breaks policy or package attempt is authorized before that human decision.

## Authority/provider boundary

KDE upstream defines the Tier 2 inventory, versions, dependencies and feature contracts. Ubuntu 26.04 may provide Qt, Polkit and other general dependencies when they satisfy those requirements. Ubuntu's older KDE packages do not define the SupraLINUX Frameworks version or node set.

## Next non-blocked work

Materialize package contracts for the 13 non-KMime pending nodes in DAG-friendly batches. Prefer simple nodes with already retained Tier 1 predecessors first, while provider-heavy/conditional nodes receive a profile audit before packaging.

KMime remains independent and decision-gated; it does not stop the rest of Tier 2.
