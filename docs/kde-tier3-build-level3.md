# KDE Frameworks 6.30 — Tier 3 build Level 3

Status: **planning gate defined; package execution not authorized**

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
