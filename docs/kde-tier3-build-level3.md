# KDE Frameworks 6.30 — Tier 3 build Level 3

Status: **PASS — hosted Frameworks preflight complete; authoritative KVM certification pending**

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


## Attempt 3 remediation definition — source materialization pending

Attempt 2 is closed as two real package **FAIL** with immutable evidence in workflow `36639418961`. Canonical Tier 3 remains **18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED**; no package is promoted.

KTextEditor `6.30.0-0supralinux3` keeps the serialized full upstream suite that removed the twelve encoding races. Its only source change is autotest-only: `testAboutToSave()` now creates and writes a self-contained `QTemporaryFile` before opening it as the document under test. This removes the reproducible-build-relative `__FILE__` assumption observed in Attempt 2 without touching production code.

Purpose `6.30.0-0supralinux3` retains the KIO worker test provider and `QT_QPA_PLATFORM=offscreen`. The two executing tests that previously used literal `http://kde.org` now create local source files and pass `file:` URLs into the same Save As/Menu flows. Attempt 2 already proved the `file` worker is available; external network reachability is not part of those test contracts, and `sbuild` remains network-disabled.

This gate authorizes **source materialization only** for KTextEditor and Purpose. `package_execution_authorized=false`; Package Attempt 3 cannot begin until both `-3` materializations PASS and a later planning/activation gate is validated.


## Attempt 3 source materialization — PASS

PR CI router `36643423967` at commit `91a493ffe10620d00350c404f37c13baa9fdbd45` passed Repository Policy and ran only the source-materialization lane. Package Level 3 remained skipped.

Both revision-`3` sources materialized **PASS** with `package_attempted=false` and `package_state_effect=none`:

- KTextEditor `6.30.0-0supralinux3`: job `109661057170`, artifact `11066929892`, ZIP SHA-256 `74afd833bcd1f35571e59a9983e5fa56bb8b774eff4210df9c4a5b6a93a321b5`. The materializer reproduced the self-contained `testAboutToSave()` patch hash `b4d9868777b7da55bf92b4196aa948671629f42c8827bade013f4a56926635b5`.
- Purpose `6.30.0-0supralinux3`: job `109661057232`, artifact `11067860328`, ZIP SHA-256 `988a4d2f21d152a938e17b802026a9c950fd2a91351ab2fbee6ae1300720945f`. Both local-source test patches reproduced their declared hashes.

Canonical package state remains **18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED** because source materialization does not promote packages. Package Attempt 3 is still unauthorized. The next gate is `tier3-build-level3-attempt3-planning-validation`.


### Repository tree recovery incident

Commit `d214ea22cbe7b9e0bc512121b3514dab724964ec` was created with an incomplete Git tree while recording the Attempt 3 source-materialization closure. This was a repository commit-construction incident, not package execution and not package evidence. No Package Attempt was consumed.

Commit `9d92876ce876791ac0922ffa1818802bac090530` restored the complete tree from `91a493ffe10620d00350c404f37c13baa9fdbd45` and reapplied only the intended Level 3 closure changes. A comparison from `91a493f...` to `9d92876...` confirmed exactly the intended 11 modified files. The noisy CI router event caused by comparing the incomplete tree to the restored tree is infrastructure-invalid for planning evidence and must not be used to authorize Package Attempt 3.


## Attempt 3 activation

Planning validation for Attempt 3 passed on clean PR CI router run `36644567893` at commit `691816b58bd631bc946cdfd617403971f3f6ef2e`.

- Router plan job: `109664829457` — PASS.
- Repository Policy job: `109664830010` — PASS.
- Level 3 planner/runner scope: PASS.
- Level 3 definition: PASS.
- Attempt 1 closure: PASS.
- Attempt 2 closure: PASS.
- Historical evidence boundary: PASS.
- All unrelated reusable CI lanes: skipped.

This authorizes Package Attempt 3 for KTextEditor and Purpose using the pinned `6.30.0-0supralinux3` source materializations. The canonical package state remains the two Attempt 2 FAILs until real Attempt 3 package evidence is classified.


## Attempt 3 closure — KTextEditor PASS, Purpose validation INFRA_INVALID

Attempt 3 ran in PR CI router workflow `36645760261` from commit `a9bb6b507cdf98bbf81f61524ed594a4f1e5e000`. Repository Policy and the Level 3 planner passed. Shared Resolute rootfs job `109668495106` produced artifact `11068855519` with SHA-256 `f3a25f7c68905b206281d023530031f01648228d6ca4974d6c478e0746cdc132`.

Both nodes reached valid `sbuild`, so both consumed Package Attempt 3.

- KTextEditor `6.30.0-0supralinux3` is a complete **PASS**: job `109668677528`, artifact `11068519665`, SHA-256 `96361a7771ea352dd01ffb9a032e37ed66399cb538f98137948c595ff043a69e`, CTest **77/77 PASS**, plus buildinfo predecessor proof, lintian, ABI, apt/runtime closure and CMake consumer checks. It is promoted and downstream-eligible.
- Purpose `6.30.0-0supralinux3` completed `sbuild` successfully with **3/3 CTest PASS**. Its job `109668677478` then failed only in the post-build `buildinfo-predecessor-proof` validator; artifact `11068364147`, SHA-256 `b76383545d2bd8eb7d64cf1fd27e57d081eb05b385f88529ad50069c1e0c49f3`. The plan incorrectly required `libkf6prison-dev`, while Purpose's actual source Build-Depends and generated buildinfo use `qml6-module-org-kde-prison (= 6.30.0-0supralinux1)`. This is classified **INFRA_INVALID** for the validation mechanism, not a Package FAIL.

Canonical Tier 3 becomes **19 PASS / 0 pending / 1 current FAIL / 0 BLOCKED**. Purpose retains its previous Attempt 2 FAIL canonically until a complete valid validation closes the `-3` build.

The remediation changes no Purpose source and does not rematerialize it. The Level 3 proof contract now validates the Prison QML binary actually consumed. The runner also captures successful package outputs before post-build validators, preventing a future validator defect from discarding usable build products.

Because Attempt 3's Purpose artifact predates that retention fix, its built `.deb/.buildinfo/.changes` outputs were not retained in the uploaded artifact. Completing the validation therefore requires a new valid package execution, which will be Package Attempt 4. Attempt 4 is scoped to Purpose only, keeps version `6.30.0-0supralinux3`, and is not yet authorized. Next gate: `tier3-build-level3-attempt4-planning-validation`.


## Attempt 4 active — Purpose only

The Attempt 3 PARTIAL closure and KTextEditor DAG promotion passed clean Repository Policy in PR CI router run `36655130391` at commit `b57f89b4506d300c2f5f1f9fca29afe3a11e477a`. Router-plan job `109697723905` and Repository Policy job `109697724136` passed. The Level 3 planner/runner scope, Level 3 live definition, immutable Attempt 3 closure and historical/live evidence boundary all passed; unrelated build lanes were skipped.

Package Attempt 4 is now authorized for **Purpose only**. KTextEditor remains canonical PASS and is excluded from the runnable matrix. Purpose reuses its existing `6.30.0-0supralinux3` source materialization; there is no source change or package revision bump.

The only remediation is the post-build proof contract: Prison is proven through `qml6-module-org-kde-prison`, matching Purpose's real Build-Depends, rather than the incorrect `libkf6prison-dev` expectation. The runner now retains successful build outputs before post-build validators execute.

Canonical Tier 3 remains **19 PASS / 0 pending / 1 current FAIL / 0 BLOCKED** until Attempt 4 produces valid Purpose evidence.


## Attempt 4 closure — Purpose PASS / Level 3 complete

Purpose-only Package Attempt 4 ran in PR CI router workflow `36655388053` from commit `cbfa17227fda156e5cccf598b910a36ed4bc8518`. The planner proved `runnable=purpose` and `planned_nodes=1`; KTextEditor was not rerun.

The shared Resolute rootfs passed in job `109698853580`, artifact `11072870340`, SHA-256 `345b669578c89f718f69038c0a8e1f0ef78406e802040bea8e6203a03d938172`.

Purpose `6.30.0-0supralinux3` completed PASS in job `109699029883`, artifact `11072881455`, SHA-256 `f9429216194b38e34fcd4ac36bb9638bf5c9b134965b445b8520e18ce667eb68`:

- CTest: **3/3 PASS**;
- corrected buildinfo predecessor proof: PASS, including `qml6-module-org-kde-prison (= 6.30.0-0supralinux1)`;
- Lintian: PASS-errors;
- ABI contract: PASS;
- APT/runtime closure: PASS;
- CMake consumer: PASS;
- QML payload: PASS;
- exact `.deb/.ddeb/.changes/.buildinfo` outputs retained.

Purpose is promoted and downstream-eligible. Together with the already-promoted KTextEditor, canonical Tier 3 is now **20 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**.

This closes the GitHub-hosted Frameworks build preflight. It does **not** certify release-relevant execution: hosted Ubuntu 26.04 remains non-authoritative. The next gate is `authoritative-kvm-runner-certification`, using the already-defined disposable Ubuntu 26.04 KVM runner path. No stable publication is authorized.
