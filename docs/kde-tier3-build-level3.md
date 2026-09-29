# KDE Frameworks 6.30 — Tier 3 build Level 3

Status: **planning validation PASS; activation still paused**

Level 3 is the fourth and final topological build level already recorded by the KDE-upstream dependency DAG. It contains exactly KTextEditor `6.30.0-0supralinux1` and Purpose `6.30.0-0supralinux1`.

The canonical pre-plan snapshot is **18 PASS / 2 pending / 0 current FAIL / 0 BLOCKED**. KNewStuff runtime validation is already closed PASS and is not reopened.

## Dependency inputs

KTextEditor directly consumes KIO, KParts, KArchive, KConfig, KGuiAddons, KI18n, Sonnet, Syntax Highlighting, KColorScheme and KAuth. Its Tier 3 ordering edges are KIO + KParts.

Purpose directly consumes KIO, KCMUtils, KCoreAddons, KI18n, KConfig, Kirigami, KNotifications, KService, Prison and KItemModels. KIO is its build-order edge and KCMUtils is its required QML edge.

All direct and transitive KDE inputs are pinned to existing canonical PASS artifacts. Breeze Icons and KDocTools remain exact support/solver-closure artifacts; they are not invented Build-Depends.

## Gate semantics

- `state=planned-pending-activation`
- `execution_authorized=false`
- `current_attempt=1`
- `next_gate=tier3-build-level3-planning-validation`

The planning definition consumes **no Package Attempt**. A Package Attempt begins only immediately before valid `sbuild` execution. Pre-sbuild infrastructure failures remain infrastructure failures.

The reusable Level 3 workflow is invoked only through the single PR CI router. Repository Policy validates the definition and planner first; package execution requires a separate activation.

GitHub-hosted Ubuntu 26.04 remains preflight evidence. Release-relevant final certification still requires the authoritative Ubuntu 26.04 KVM lane.

No stable publication is implied or authorized by this gate.


## Planning validation PASS / activation paused

The paused Level 3 definition passed the single PR router at commit `87099ae7fa83a41edde584c60cea0d2880e22d4c`. PR CI router run `36606233220` completed PASS; its Repository Policy job `109535845900` and router plan job `109535845121` both passed.

Repository Policy explicitly passed the Level 3 planner/runner scope and Level 3 definition checks, plus the retained KNewStuff runtime closure, historical-evidence boundary and closed Round 11 validator. The router did **not** schedule the Level 3 reusable build because `execution_authorized=false`, so the shared rootfs and both package jobs did not run and no Package Attempt was consumed.

Before activation, the Level 3 validator is made forward-compatible with `state=active-pending-ci` and binds that future state to the exact planning-validation evidence above. This checkpoint changes no package state and does not authorize execution. A later activation is valid only if it references this PASS evidence exactly.
