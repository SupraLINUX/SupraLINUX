# KDE Tier 2 package contracts

Status: **five contract drafts; technical reference capture pending**  
Date: **2026-09-20**

The first contract batch contains KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. All five already passed the Ubuntu Resolute provider audit and remain package-state `pending`.

Ubuntu 26.04 and Debian packaging are a **technical reference** only. KDE upstream 6.30.0 defines the actual feature/API contract; SupraLINUX owns the package contract.

Compatibility source/binary names are preserved where Ubuntu already exposes them. KNotifications also preserves the QML split because upstream builds that surface when a QML provider is available.

Upstream 6.30.0 enables Python bindings on Linux for KNotifications, KStatusNotifierItem and KUnitConversion. Ubuntu's current source packages do not expose corresponding Python binary packages, so SupraLINUX must not silently disable the feature. The draft adds:
- `python3-kf6notifications` providing module `KNotifications`;
- `python3-kf6statusnotifieritem` providing module `KStatusNotifierItem`;
- `python3-kf6unitconversion` providing module `KUnitConversion`.

The reference-capture workflow records the current Ubuntu Resolute and Debian sid source records, Build-Depends, binary sets and source-file SHA-256 values. This stage is **not a package PASS** and does not authorize publication.
