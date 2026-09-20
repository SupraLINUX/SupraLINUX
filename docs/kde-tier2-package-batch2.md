# KDE Frameworks Tier 2 — package Batch 2

Status: **replacement materialization PASS; clean-build remediation queued**  
Date: **2026-09-20**

Batch 2 covers KCrash, KNotifications, KStatusNotifierItem, KUnitConversion and Syndication. The five nodes remain package-state `pending`; canonical Tier 2 is still **1 PASS / 14 pending / 0 current FAIL / 0 BLOCKED**.

Run `35530953084` was the first real clean-build campaign. KCrash, KNotifications, KStatusNotifierItem and Syndication crossed the `sbuild` boundary but all converged at `install-deps` on the same unsatisfied `debhelper-compat (= 14)` requirement inherited from the Debian 6.30 technical-reference packaging. This is recorded as a real execution with result **INFRA**, not four node-owned package FAILs.

KUnitConversion did not reach `sbuild`: retained KI18n validation found a single incorrectly transcribed SHA-256 for `libkf6i18n-data`. The campaign pin is corrected to the hash verified from the retained PASS artifact. That incident is pre-attempt INFRA.

Ubuntu Resolute is the provider for packaging tooling. The active provider exposes debhelper compatibility level 13, while the Debian 6.30 reference tree requests 14. SupraLINUX therefore applies an explicit packaging-tooling adaptation from compatibility level 14 to 13 during deterministic materialization. This adaptation has **no KDE feature-profile effect**: KDE upstream still defines the selected CMake/features contract.

The old materialization PASS is preserved as historical evidence but is no longer build-consumable. Until the five trees are regenerated and pinned, the generated build queue is empty and Batch 2 package jobs are intentionally skipped.

A real package attempt begins immediately before clean `sbuild`. Crossing that boundary records a real execution, but it does **not** automatically make the result a canonical FAIL. Post-boundary failures require root-cause classification; **FAIL requires a node-owned cause**. Shared infrastructure/provider failures retain package-state effect `none`.

The matrix remains **fail-fast: false**. PASS still requires non-zero upstream CTest success, exact binary set, Lintian error gate, expected SONAME, APT runtime closure and an external CMake consumer, plus Python/QML smoke where applicable.

No Batch 2 result publishes automatically. PASS may later be evaluated for `testing`; promotion to `stable` requires explicit user approval.


## Replacement materialization PASS

Materialization run `35534384634` completed **5/5 PASS** using the explicit Resolute `debhelper-compat 14 -> 13` packaging-tooling adaptation. The generated tree/debian-tree/source-package hashes and artifact digests are pinned in the package-contract and Batch 2 campaign manifests.

The five nodes return to `build-ready`; Batch 2 resumes as `remediation-pending-build` with `fail-fast: false`. The corrected KI18n predecessor hash is part of the campaign input.

Raw runner evidence now uses `ATTEMPT_FAILURE` for a post-`sbuild` failure until root-cause classification is complete. Only a node-owned cause may be promoted to canonical `FAIL`.
