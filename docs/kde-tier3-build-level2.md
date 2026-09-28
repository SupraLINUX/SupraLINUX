# KDE Frameworks Tier 3 — build Level 2

Status: **Attempt 1 active; binary execution authorized after planning PASS** as of 2026-09-28.

Level 2 contains Baloo, KCMUtils, KNotifyConfig and KParts. Its precondition is closed Level 1 Attempt 10: KIO `6.30.0-0supralinux10` and KXMLGui `6.30.0-0supralinux5` are canonical PASS, with Tier 3 at **13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED**.

The Level 2 manifest freezes each source-only materialization, all direct Frameworks 6.30 Build-Depends, the recursive SupraLINUX provider closure, exact predecessor versions/artifact IDs/SHA-256 values, selected build profiles and QML payload checks. Every Level 2 sbuild remains network-disabled.

```text
state = active-pending-ci
execution_authorized = true
current_attempt = 1
next_gate = tier3-build-level2-attempt1
```

Planning was validated by Repository Policy `36443524514` and Level 2 workflow `36443524497` at commit `b07c6c0a0b3072a76e57cf52d679001de2985d3c`. That run executed the planner and intentional skip only; rootfs and package jobs were skipped as required.

Attempt 1 is now separately authorized for Baloo, KCMUtils, KNotifyConfig and KParts. Canonical package state remains unchanged until real build evidence is consumed.

KNewStuff remains `pending/runtime-validation-required`. A KCMUtils PASS only enables its separate runtime-validation gate; it never auto-promotes KNewStuff.

PASS, FAIL, BLOCKED and INFRA retain their existing semantics. Independent Level 2 nodes use fail-fast=false. Stable promotion still requires explicit user approval.
