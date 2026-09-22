# KDE Frameworks 6.30 — Tier 3 discovery

Status: **0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED**

Last reviewed: **2026-09-22**

## Authority and precondition

KDE upstream is the authority for the Frameworks inventory, release version and dependency graph. Ubuntu 26.04 is the platform/provider and compatibility target; Ubuntu packaging does not select or limit the KDE Frameworks version.

Tier 3 begins only after canonical Tier 2 closed at **15 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

Upstream references:

- tier classification: `https://api.kde.org/`;
- selected stable release: `https://kde.org/info/kde-frameworks-6.30.0/`;
- selected Frameworks release: **6.30.0**.

KDE defines Tier 3 as Frameworks that may depend on Tier 1, Tier 2 and other Tier 3 Frameworks. This makes global dependency discovery mandatory before any packaging order is selected.

## Verified source inventory

The current upstream Tier 3 inventory contains exactly 20 Frameworks:

- Baloo
- KBookmarks
- KCMUtils
- KConfigWidgets
- KDAV
- KDESu
- KIconThemes
- KIO
- KJobWidgets
- KNewStuff
- KNotifyConfig
- KParts
- KPeople
- KRunner
- KSvg
- KTextEditor
- KTextWidgets
- KWallet
- KXMLGui
- Purpose

`manifests/kde-frameworks-tier3.json` records each KDE 6.30.0 release tarball and the SHA-256 published on the official KDE release-info page.

## Current lifecycle

All 20 nodes are canonical `pending` with readiness:

`dependency-discovery-required`

At this stage:

- no Ubuntu/Debian package version has been selected as authority;
- no SupraLINUX package revision is authorized;
- no provider audit is authorized;
- no package contract/materialization/build is authorized;
- no Tier 3 node is downstream-eligible;
- no pending Tier 3 node is inserted into the canonical PASS DAG.

The next operation is a **global KDE-upstream dependency discovery**. Required, conditional and profile-selected Framework edges must be derived from upstream stable metadata/source. Only after that DAG is validated may independent topological roots enter provider/profile audit.

The project rule remains: **KDE decides what KDE needs.**

PASS will make future packages eligible for `testing` only. Promotion to `stable` always requires explicit user approval.
