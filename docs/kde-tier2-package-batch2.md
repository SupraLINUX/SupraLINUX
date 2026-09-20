# KDE Frameworks Tier 2 — package Batch 2

Status: **prepared; first real clean-build campaign pending CI**  
Date: **2026-09-20**

Batch 2 consumes the five generated `build-ready` nodes: KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. They are independent in the current Tier 2 DAG, so the matrix uses **fail-fast: false** and continues unaffected nodes after a peer failure.

A single **shared Resolute rootfs** is created once per workflow run and reused read-only by all five matrix jobs. Each node receives only retained PASS artifacts for ECM and its required Tier 1 predecessor. The exact artifact identities and every predecessor `.deb` SHA-256 are pinned in the campaign manifest.

The attempt boundary is explicit: failures before `sbuild` are INFRA and have no package-state effect. The runner sets `package_attempted=true` immediately before invoking clean `sbuild`; a failure after that boundary is a real package FAIL.

PASS requires a non-zero upstream CTest success summary, the exact binary package set, Lintian error gate, expected SONAME, APT runtime closure and an external CMake consumer. Python-enabled nodes additionally require import smoke; KNotifications additionally requires a QML payload smoke.

No Batch 2 PASS is published automatically. PASS may later become eligible for the SupraLINUX `testing` repository. Promotion to `stable` remains blocked until explicit user approval.
