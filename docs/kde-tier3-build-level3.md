# KDE Frameworks 6.30 — Tier 3 build Level 3

Status: **Attempt 1 closed FAIL; remediation definition pending**

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


## Attempt 1 active

Planning validation PASS is bound to Repository Policy run `36606233220` (job `109535845900`) and router plan job `109535845121` at commit `87099ae7fa83a41edde584c60cea0d2880e22d4c`. The forward-compatible active lifecycle validator then passed Repository Policy run `36606727079` (job `109537541705`) at commit `8812f744e21ab3833ebd162594a805a30ce9e294`.

A separate activation now sets `state=active-pending-ci`, `execution_authorized=true`, and `next_gate=tier3-build-level3-attempt1`. The runnable set is exactly KTextEditor + Purpose, scheduled independently with `fail-fast=false` and `max-parallel=2`.

This activation itself does not consume a Package Attempt. Each node consumes Attempt 1 only when its runner reaches valid `sbuild` execution. A pre-sbuild runner/rootfs/transport failure remains infrastructure evidence rather than package FAIL.


## Attempt 1 closure — 2 real FAIL

Level 3 Attempt 1 ran in PR CI router workflow `36607647059` from commit `2692489bdb861520181df486c524efb9cdf47d60`. Repository Policy passed first. The Level 3 plan and shared Resolute rootfs also passed. Rootfs evidence: job `109541198352`, artifact `11051807633`, SHA-256 `08eb26b3d264c79e26dd0f5e1cb6fe543a16e1f2be0f713bab5fee45cabdbd83`.

Both independent nodes reached valid `sbuild`, so each consumed Package Attempt 1 and each is a real package **FAIL**:

- KTextEditor `6.30.0-0supralinux1`: job `109541487937`, artifact `11052302105`, SHA-256 `d66ad916ef3f4e38e2ab3dc436fba3ac7dcb6f1e59603399c5debaebfa6a5458`. CTest reached 64/77 PASS. Twelve encoding diff tests failed and `katedocument_test::testAboutToSave()` timed out at 300000 ms.
- Purpose `6.30.0-0supralinux1`: job `109541487871`, artifact `11052225512`, SHA-256 `cff8b75aac023985ba5f4c3c4d429665b268cd65865d65969724408ec2cc5122`. CTest reached 1/3 PASS. `alternativesmodeltest` observed KIO `Unknown protocol 'file'`; `menutest` aborted because Qt xcb could not connect to a display.

The canonical snapshot is now **18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED**. Execution is closed with `execution_authorized=false`. No root cause beyond the observed test failures is asserted by this closure. The next gate is `tier3-build-level3-attempt1-remediation-definition`; Attempt 2 is not authorized.
