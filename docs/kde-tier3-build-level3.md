# KDE Frameworks 6.30 — Tier 3 build Level 3

Status: **Attempt 2 closed FAIL; Attempt 3 remediation definition pending**

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


## Attempt 1 remediation definition

Attempt 1 closure is Policy-validated. Attempt 2 remains unauthorized while exactly two source packages are rematerialized as revision `6.30.0-0supralinux2`.

KTextEditor remediation is test-only. Attempt 1 proved all twelve encoding `*_create` tests PASS while their paired `*_diff` tests raced them under parallel CTest, so the complete unfiltered suite is serialized with `dh_auto_test --no-parallel`. The remaining `testAboutToSave()` timeout is remediated by a deterministic autotest-only patch that copies `__FILE__` into a writable `QTemporaryFile` before testing the normal save signals. Production KTextEditor code is unchanged.

Purpose remediation adds the missing test runtime provider `kio6 (>= 6.30.0~) <!nocheck>`, because the retained KIO 6.30 package provides the `file` and `http` workers that Attempt 1 could not find. The GUI `menutest` runs with `QT_QPA_PLATFORM=offscreen`; no Purpose production source change is required.

The Level 3 solver/support closure also gains the already-PASS KDED `6.30.0-0supralinux1` artifact `10691372157`. This prevents KIO runtime resolution from mixing the selected KDE 6.30 stack with Ubuntu's older KDED provider. KDED remains a solver/support input, not an invented KDE dependency or a synthetic `.buildinfo` edge.

This gate authorizes **source materialization only**. `package_execution_authorized=false`; no Package Attempt 2 can begin until both rematerializations PASS and a later planning/activation gate is validated.


## Attempt 2 planning, activation and closure — 2 real FAIL

The remediated source inputs were closed source-only PASS before execution: KTextEditor `6.30.0-0supralinux2` is artifact `11064709291` (SHA-256 `606f9e22f162382f60b9499654248ebb8ac9e7970f47934b11457757a832becf`), while Purpose `6.30.0-0supralinux2` retains artifact `11054941469` (SHA-256 `b7fa3f20bacbc6b142f18596cc6cabd3a670a86f9246f39f7307be905dac16c7`). The KTextEditor-only rerun followed one pre-package `INFRA_INVALID` validator incident; it did not consume an extra package Attempt.

Attempt 2 planning passed PR CI router `36638763826` at commit `53189d094b89afecbd6e382fe8fd4054334c1a0e`; Repository Policy job `109645765290` and router-plan job `109645764969` passed with binary execution paused. Attempt 2 was then activated separately. The first activation-policy failure remained pre-build and consumed no package Attempt; after the lifecycle handoff fix, PR CI router `36639418961` at commit `9fd5041053a176fdafcb3939e57a0ff2dd26d91e` passed Repository Policy and entered the reusable Level 3 build.

The shared Resolute rootfs passed in job `109648205853`: artifact `11066320451`, SHA-256 `d6ec90546a42d24d6561e49c9684ca03716b9c0ce4b98d7d95415571e3f4bb85`.

Both nodes reached valid `sbuild`, so both consumed Package Attempt 2 and are real package **FAIL**:

- KTextEditor `6.30.0-0supralinux2`: job `109648411937`, artifact `11066168089`, SHA-256 `74fd2819b9110d7a8ce35ca2a2c8a89fb1a9b31548e32e05de2cb0e9426234e6`. CTest improved from 64/77 to **76/77 PASS**. Serialization fixed the twelve encoding create/diff races. The only remaining failure is `KateDocumentTest::testAboutToSave()`: the remediation attempted to open `__FILE__`, but the reproducible build exposes it as a relative source path from the test working directory.
- Purpose `6.30.0-0supralinux2`: job `109648412196`, artifact `11066102772`, SHA-256 `adf13dd09a0ebd4b001f51c83cfe2b19360fa482b6c73c1a1ab579e7914e0a19`. CTest remains **1/3 PASS**, but the previous blockers changed: the KIO file worker is present and Qt offscreen works. `alternativesmodeltest` and `menutest` now fail while accessing their upstream literal `http://kde.org` URL inside the intentionally network-disabled `sbuild` environment.

Canonical Tier 3 therefore remains **18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED**. No package is promoted, execution is paused, and Attempt 3 is not authorized. The next gate is `tier3-build-level3-attempt2-remediation-definition`.
