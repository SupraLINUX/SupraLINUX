# KDE Frameworks 6.30 — Tier 2 discovery

Status: **KAuth PASS; KMime compatibility decision pending**  
Date: **2026-09-20**

KDE API classifies exactly two current Tier 2 Frameworks: **KAuth** and **KMime**. Tier 2 may depend on Tier 1 Frameworks. SupraLINUX starts this phase only after the canonical Tier 1 closure at **29 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

## KAuth

Upstream 6.30.0 SHA-256: `60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9`.

The always-required Framework predecessor is KCoreAddons. On Linux, upstream probes PolkitQt6-1; when present it selects the real Polkit backend and also requires KWindowSystem and Qt DBus. Resolute provides `libpolkit-qt6-1-dev 0.200.0-4ubuntu1`, above upstream's 0.112.0 minimum.

SupraLINUX therefore selects:
- KCoreAddons retained PASS;
- KWindowSystem retained PASS;
- `POLKITQT6-1` auth backend;
- `DBUS` helper backend;
- no silent Fake-backend fallback.

KAuth is **PASS/downstream-eligible** as `6.30.0-0supralinux3`. The retained package evidence is run `35497461178`, job `106043001431`, artifact `10601382235`: 6/6 tests, Lintian error gate, ABI, APT closure, development contract and external consumer all pass.

## KMime

Upstream 6.30.0 SHA-256: `2969a5ef484e98f91bf78e88c98a9d613bdd3bb86ac154ceece0557b70f373bc`.

Its Tier 1 build predecessor is KCodecs, already retained PASS. The technical blocker is compatibility architecture, not dependency availability.

Ubuntu Resolute still packages PIM KMime `25.12.3-0ubuntu1` as `libkpim6mime6` / `libkmime-dev`. Frameworks KMime changed the CMake and runtime namespace from `KPim6Mime` / `KPim6::Mime` / `libKPim6Mime.so.6` to `KF6Mime` / `KF6::Mime` / `libKF6Mime.so.6`.

Therefore KMime is **compatibility-decision-required** under ADR-0002. No package attempt is valid before that decision.

## Authority/provider boundary

KDE upstream selects KAuth/KMime 6.30.0 and their dependencies. Ubuntu may supply PolkitQt/Qt and remains the compatibility reference for Debian package contracts; Ubuntu's older KDE/PIM versions do not select the SupraLINUX KDE version.

## KAuth Batch 1 preparation

KAuth's retained PASS package is `kf6-kauth 6.30.0-0supralinux3`. The clean Resolute build consumes retained ECM, KCoreAddons and KWindowSystem PASS artifacts as explicit local sbuild inputs and uses the real PolkitQt6-1 + DBus backend profile.

The source package imports only the `libkf6authcore6.symbols` contract from Debian `6.30.0-1` after verifying the complete Debian tarball SHA-256. This is technical-reference use, not authority transfer.

## Current Tier 2 canonical state

**1 PASS / 1 pending / 0 current FAIL / 0 BLOCKED**.

KAuth is now present in the canonical KDE DAG and can feed later dependency tiers. KMime remains pending because ADR-0002 requires a compatibility architecture decision; it is not BLOCKED by a failed predecessor.
