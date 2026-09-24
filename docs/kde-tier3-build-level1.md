# KDE Frameworks Tier 3 — build Level 1

Status: **Attempt 5 reviewed — 0 SUCCESS / 2 real FAIL; round 10 source remediation pending** as of 2026-09-24.

Level 1 contains exactly **KIO** and **KXMLGui** from the validated KDE-upstream 6.30.0 DAG. The execution authority is `manifests/kde-tier3-build-level1.json`; its initial state is `planned-pending-activation` with `execution_authorized=false`.

## Preconditions

Level 0 Attempt 5 closed with 11 canonical PASS nodes and KNewStuff runtime-pending. Repository Policy run `35825677329` validates the post-Level0 state plus the promoted KIO round-5 source remediation.

KIO is built from source materialization run `35825070347`, job `107064960565`, artifact `10735250819`, SHA-256 `8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106`, package revision `6.30.0-0supralinux2`.

KXMLGui retains its previously promoted `6.30.0-0supralinux1` source materialization artifact `10703925009`.

## DAG inputs

KIO consumes the promoted Tier 3 PASS artifacts for KBookmarks, KIconThemes, KJobWidgets and KWallet. Its external KDE inputs are pinned to canonical SupraLINUX PASS artifacts. KDocTools is retained as the CI/documentation provider; KDED is retained for runtime closure validation and is not treated as a KIO source-build edge.

KXMLGui consumes KConfigWidgets, KIconThemes and KTextWidgets from Level 0 plus its external PASS inputs. KTextWidgets remains a test-required edge, not an invented topology relation.

Only exact PASS artifacts may feed Level 1. FAIL means a real attempted node failure; BLOCKED means a node was not attempted because a required predecessor was not PASS. KIO and KXMLGui are independent at this level and use `fail-fast=false`.

## Required gates

Each real Level 1 PASS requires clean Resolute sbuild, a positive non-zero upstream CTest summary, exact binary set/version, selected-profile proof, exact predecessor versions in `.buildinfo`, Lintian error gate, ABI SONAME/export checks, APT runtime closure, installed CMake consumer discovery, and Python import validation where declared.

KIO explicitly proves `BUILD_TESTING=ON`, `WITH_WAYLAND=ON`, `BUILD_DESIGNERPLUGIN=ON` and `KDE_INSTALL_APP_TEMPLATES=ON`. KXMLGui proves `BUILD_TESTING=ON`, `BUILD_PYTHON_BINDINGS=ON`, `BUILD_DESIGNERPLUGIN=ON` and imports `KXmlGui`.

## Authorization boundary

This planning commit does **not** run KIO or KXMLGui. Repository Policy must first validate the Level 1 definition. A later, separate activation may set `execution_authorized=true`.

PASS may make packages eligible for the SupraLINUX `testing` channel. Promotion to `stable` is never automatic and always requires explicit user approval.


## Attempt 1 activation

Repository Policy run `35826072726` validated the complete Level 1 definition at commit `b96e925ee9f649c1b4b984ed6fed277ef911f2c2`. The planning workflow `35826072818` also validated the planner/runner and intentionally scheduled zero package jobs while `execution_authorized=false`.

A separate activation now sets `execution_authorized=true` for exactly KIO and KXMLGui. The canonical phase becomes `build-level1`; both jobs may execute independently with `fail-fast=false`. No other Tier 3 node is authorized.

No package is promoted by activation alone. PASS/FAIL is determined only by the real build artifacts and gates from Attempt 1.


## Attempt 1 — 0 SUCCESS / 2 FAIL, provider closure incomplete

Workflow `35826694664` ran both Level 1 nodes against the same Resolute rootfs (artifact `10735292514`, artifact SHA-256 `7f1bd21e77ca479dbb2e478467d61cf1aa2d71740a929eb92d2737a8252378c2`, inner rootfs SHA-256 `65b28559cd2e23c1a2b5968e12ca0b3e48fd518b791b069ac2217898b44bfbed`).

Both nodes were really attempted and therefore are **FAIL**, not BLOCKED:

- KIO job `107070288529`, artifact `10735576795`, SHA-256 `bbc1cb4caa351a335077e4b3dc0dcee7b2a7dfb96d85e6659d112ad87069c353`: sbuild stopped at install-deps. The retained input set omitted transitive provider closure. `dose3` first proved `libkf6archive-dev >= 6.30.0` unsatisfied.
- KXMLGui job `107070288573`, artifact `10734929331`, SHA-256 `9e14c20ddfed7bc1cb500e1c2544eac1469b97cc2862ed54a946fd0deb1161ed`: sbuild stopped at install-deps. `libkf6configwidgets-dev 6.30.0` could not satisfy its `libkf6codecs-dev >= 6.30.0` relation from the retained artifacts.

The root cause is the Level 1 **provider closure plan**, not either source package. No source revision changes and no rematerialization are justified.

The complete added closure is:

- KIO: KArchive, KCodecs, KNotifications.
- KXMLGui: KArchive, KCodecs, KColorScheme, KCompletion, Sonnet.

Each is an existing canonical SupraLINUX PASS artifact. They are marked `provider_closure`, not KDE DAG edges, and are intentionally excluded from direct predecessor `.buildinfo` proof unless the same component is independently a real direct input.

Level 1 is paused with `execution_authorized=false`. Repository Policy must validate this closure-only remediation before a separate Attempt 2 activation.


### Provider-closure classification is consumer-specific

A retained PASS artifact may be a direct input for one Level 1 node and only transitive provider closure for another. The global artifact pin therefore keeps its canonical PASS provenance; `provider_closure_input_ids` on each node determines whether that same artifact is closure-only for that consumer. This classification never changes the KDE DAG.


## Attempt 1 canonical classification and complete Attempt 2 closure

The raw Attempt 1 artifacts remain:
- KIO job `107070288529`, artifact `10735576795`, SHA-256 `bbc1cb4caa351a335077e4b3dc0dcee7b2a7dfb96d85e6659d112ad87069c353`;
- KXMLGui job `107070288573`, artifact `10734929331`, SHA-256 `9e14c20ddfed7bc1cb500e1c2544eac1469b97cc2862ed54a946fd0deb1161ed`.

Both jobs reported raw `FAIL` after entering sbuild, but they stopped in `install-deps` because the common Level 1 orchestration omitted package-provider closure. No node-owned compilation, test or package defect was established. The ledger therefore retains `raw_result=FAIL` while the canonical result is `INVALIDATED-ORCHESTRATION`; current canonical FAIL remains zero.

Consumer-specific closure remains the controlling classification: a retained artifact can be a direct input for one node and closure-only for another. The complete closure required by real predecessor `.deb` metadata is:
- KIO: KConfigWidgets, KArchive, KCodecs, KNotifications and Breeze Icons;
- KXMLGui: KArchive, KCodecs, KColorScheme, KCompletion, Sonnet and Breeze Icons.

Breeze Icons is supplied from the support PASS sub-DAG. KConfigWidgets is already a canonical Tier 3 Level 0 PASS artifact. None of these closure-only roles creates a KDE DAG edge or a direct `.buildinfo` requirement.

The runner now retains `provider-closure.json`, verifies declared runtime-input versions in `runtime-validation.json`, and records both gates in final evidence. KIO stays `6.30.0-0supralinux2`; KXMLGui stays `6.30.0-0supralinux1`. Attempt 2 remains `execution_authorized=false` until Repository Policy validates this corrected closure.


## Attempt 2 activation

Validation evidence:
- remediation commit: `568beba8aa3dce7a3f3a51d5e91d31edb5a30523`;
- Repository Policy: `35828634884` PASS;
- paused Level 1 validation workflow: `35828634887` PASS with rootfs/build skip;
- source revisions: unchanged;
- scope: full KIO + KXMLGui rerun;
- scheduling: parallel, `fail-fast=false`.

The runner additionally proves the complete provider-closure artifact set and declared runtime-input versions. No package becomes PASS merely by activation; canonical transitions occur only after Attempt 2 evidence review.


## Attempt 2 result — two real node failures

Workflow `35829170695` at commit `897d3a864bc7ea164400c7d9de2e9c51cf6316ab` reran both independent Level 1 nodes with the round-6 provider closure. The shared Resolute rootfs is artifact `10736033276`, artifact SHA-256 `8576bb973423d12cdd805c37e6c8b479aedf82466e38762a5ed8cb99def6961f`, inner rootfs SHA-256 `170fdc81f745a8597880a6433026f9ef66bca68665bf3450d02f0de561f3abe6`.

Both jobs passed dependency installation, so these failures are no longer orchestration-invalidated:

- **KIO** job `107077795233`, artifact `10736848742`, SHA-256 `94f5c7b51f47cd29dae2604f6258b8f10d13ef78e6f36e7023887c4f4336a51b`: compilation reached the complete 69-test CTest suite; 13 targets failed because the clean build lacked pieces of KIO's upstream test environment (session D-Bus, universal offscreen GUI selection, installed Breeze theme payload, network for the two upstream Google HTTP tests, deterministic HOME semantics, and isolation from cross-test shared state).
- **KXMLGui** job `107077795323`, artifact `10735938957`, SHA-256 `fe460539e197a4549b79cb8b6cedd9eac7ae823ceed6b758483cf53fcf774800`: CMake reached `ECMGeneratePythonBindings` with `BUILD_PYTHON_BINDINGS=ON` and stopped because Python module `build` is missing. The same ECM wheel path already established that Resolute also needs the setuptools backend.

These are **real FAIL results** in the Level 1 attempt ledger, not BLOCKED and not invalidated orchestration. No package is promoted from Attempt 2.

## Round 7 remediation

KIO advances to `6.30.0-0supralinux3`. No upstream test is disabled. The source package adds test-only `dbus-daemon` and the SupraLINUX Breeze icon-theme provider, and runs CTest under a controlled writable HOME/XDG runtime directory, `QT_QPA_PLATFORM=offscreen`, an isolated `dbus-run-session`, the KDE CI marker used by KIO itself, and serial CTest scheduling.

KIO's two upstream external HTTP tests intentionally access `google.com`. Because unshare-mode sbuild blocks build-network access by default, the Level 1 runner records a **KIO-only** `--enable-network` exception. KXMLGui and every other node remain network-disabled.

KXMLGui advances to `6.30.0-0supralinux2` and adds `python3-build` plus `python3-setuptools`; Python bindings remain enabled.

Level 1 is paused. Only KIO and KXMLGui enter source materialization; a full Attempt 3 rerun is allowed only after both materializations PASS, their exact evidence is promoted, and Repository Policy validates the promotion.


## Round 7 source PASS handoff

Source materialization run `35882795135` passed for both remediated Level 1 nodes. KIO is now pinned to `6.30.0-0supralinux3` artifact `10760324592` / SHA-256 `b58b7a45f6df0c8f01e9bd9a37799c1470369124a7c1b48fecb82a5f7f86ae8d`; KXMLGui is pinned to `6.30.0-0supralinux2` artifact `10761208629` / SHA-256 `72cd10276558264646a9e38d5beab7b231434338597ef8d276030e790ff02214`.

This transition does **not** authorize package builds. Attempt 2 remains the latest binary evidence and its two real FAIL records stay in the ledger. The Level 1 runner is paused with the refreshed source pins until Repository Policy validates the promotion; Attempt 3 requires a separate activation commit.


## Attempt 3 activation

Round-7 source promotion passed Repository Policy `35884583361` and paused Level 1 validation `35884584590`. The forward-compatible Attempt 3 lifecycle itself then passed Repository Policy `35885074463` and Level 1 validation `35885074557`.

A separate activation commit authorizes the complete two-node Level 1 rerun. KIO consumes `6.30.0-0supralinux3` artifact `10760324592`; KXMLGui consumes `6.30.0-0supralinux2` artifact `10761208629`. Scheduling remains parallel with `fail-fast=false`.

KIO alone retains the documented sbuild network exception required by its upstream external HTTP tests; KXMLGui remains network-disabled. No stable publication is implied by build success.

## Attempt 3 result — round 8 follow-up

Workflow `35887558758` at commit `7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94` completed **0 SUCCESS / 2 real FAIL**. The shared Resolute rootfs is artifact `10763606519`, artifact SHA-256 `bf1fe0caaf73f0595d94c75b01f560f2913511bcafe8efe6fa81d8cc2bc0aa67`, inner rootfs SHA-256 `bd00be95fb5b9446a527ea155d625bd7c1cfd9ff7a0c8e59ceef118b421c11b6`.

**KIO** job `107272258383` / artifact `10763498649` / SHA-256 `87ece6a4a4dd51af6b8d5810aaed39b58e5f3f01e979c0f2ce8daa8b3082d564` executed all 69 upstream tests: **62 PASS / 7 FAIL**. Round 7 therefore improved the suite from 13 failures to 7. Four current failures involve QLocalServer/listen behavior while the round-7 wrapper forces one fixed `XDG_RUNTIME_DIR`; `connectionbackendtest` and `fileundomanagertest` are new relative to Attempt 2. Round 8 removes only that forced runtime-directory override and retains the D-Bus session, offscreen Qt backend, Breeze payload, controlled HOME, KDECI marker, serial CTest and KIO-only network access that already fixed real failures. `krecentdocumenttest`, `kdirmodeltest` and `knewfilemenutest` remain explicitly unresolved; no test is suppressed.

**KXMLGui** job `107272258358` / artifact `10763747234` / SHA-256 `c4626450ad4149723818884373dfc56603e411b62eafa1d4968ac979c0fa6516` proves the Python build-provider remediation is solved. The complete upstream test invocation then produced **1 PASS / 6 FAIL**, all six aborting because Qt attempted xcb without a display. Round 8 keeps the normal upstream `dh_auto_test` path and adds only `QT_QPA_PLATFORM=offscreen`.

KIO advances to `6.30.0-0supralinux4`; KXMLGui advances to `6.30.0-0supralinux3`. Level 1 execution is paused until both source rematerializations PASS and their exact evidence is policy-validated. Level 2 remains unauthorized. Canonical package state remains **11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED**.

## Round 8 materialization handoff

Source materialization workflow `35894317888` completed successfully for both Level 1 nodes.

- KIO `6.30.0-0supralinux4`: job `107294403189`, artifact `10766471076`, artifact SHA-256 `80959256047d70323b6ea311551bed573661cefb4b831f30750e27ed11076cf6`, adapted rules SHA-256 `e8dae488976ef4d4748f044f52b3aebcf687ae3a52733588917fa8c397920f3e`.
- KXMLGui `6.30.0-0supralinux3`: job `107294403314`, artifact `10766665506`, artifact SHA-256 `100cf903ca1ef17cf2b37bab58ba0b7bf1e562d111cc04107247c3f35b134d58`, adapted rules SHA-256 `597ef52317fee17c1aa1dca92b0c547ac1fa543f4a56b8b3b1d6075e07d5c14f`.

The prior push exposed two historical lifecycle-validator assumptions before any binary rebuild occurred: `validate_kde_tier3.py` fell back to the old round-5 branch and `validate_kde_tier3_build_level1.py` still had a second round-7-only pending-materialization branch. They are updated with the round-8 handoff. Attempt 4 remains unauthorized until planning validation passes.

## Generated campaign synchronized after round 8

The generated Tier 3 build campaign now points to the promoted round-8 source inputs: KIO `6.30.0-0supralinux4` artifact `10766471076` and KXMLGui `6.30.0-0supralinux3` artifact `10766665506`, both from materialization run `35894317888`. This refresh changes only derived source pins; `execution_authorized=false` remains unchanged and Attempt 4 is still gated by Level 1 planning validation.

## Attempt 4 lifecycle pre-validation

The promoted round-8 inputs passed Repository Policy `35895610944` and the paused Level 1 planner `35895610937` at commit `9f680b0d8790c7bc472e8352e6675d606f706ee7`. KIO remains pinned to `6.30.0-0supralinux4`; KXMLGui remains pinned to `6.30.0-0supralinux3`.

Before changing execution authority, the validators are extended to recognize the future Attempt 4 active lifecycle and to require those exact planning-validation runs. This validator-only transition does not schedule package builds: `execution_authorized=false` remains the current manifest state until a separate activation commit.

## Attempt 4 activation

The promoted round-8 source pins passed Repository Policy `35895610944` and paused Level 1 validation `35895610937` at commit `9f680b0d8790c7bc472e8352e6675d606f706ee7`. The forward-compatible active lifecycle itself then passed Repository Policy `35961362802` and Level 1 validation `35961362869`.

A separate activation commit now authorizes the complete two-node Attempt 4. KIO consumes `6.30.0-0supralinux4` artifact `10766471076`; KXMLGui consumes `6.30.0-0supralinux3` artifact `10766665506`. Scheduling remains parallel with `fail-fast=false`.

KIO retains only its previously documented node-scoped network exception; KXMLGui remains network-disabled. Binary PASS does not imply stable publication.

## Attempt 4 result — round 9 follow-up

Workflow `35961584503` at commit `513cb12a96c7c79ffb5790253504482a56af2e63` completed with KIO FAIL and KXMLGui FAIL. The shared rootfs is artifact `10792995587`, SHA-256 `c9ed6500670e092f8fe6e0ec531857afb51c5587f9a56bef083af2267c268ce3`, inner SHA-256 `46fd06c2725ce8f10efba3c577da62f3a0dd5cb96e59683ca9fc988bed28c3a8`.

**KIO** job `107511358507`, artifact `10792898014`, SHA-256 `507f741700f698a1252851cb3d6ef2883fab68b4db79e239885eb5dc9e8bc299`: **67/69 CTest targets PASS**. The first assertions in both remaining targets show missing themed-icon lookup, not a compile, network, D-Bus or runtime-directory failure. The round-9 package revision `6.30.0-0supralinux5` retains the proven environment and uses XCB on Xvfb with Breeze selected as the system icon theme.

**KXMLGui** job `107511358468`, artifact `10792134667`, SHA-256 `7171d692f12eede3945b6136f175538ef6557601e7f370d2ccd9b11f45ec5849`: **6/7 CTest targets PASS**. The sole failing `ktoolbar_unittest` contains D-Bus-dependent toolbar-style assertions. Revision `6.30.0-0supralinux4` adds only an isolated session bus around the complete offscreen `dh_auto_test`.

Attempt 5 is not authorized. The next gate is `tier3-round9-level1-materialization`.

## Round 9 materialization handoff

Source materialization workflow `35965579279` completed successfully for both Level 1 nodes at commit `8380856c8161dccc9de9c12745012c555baa26b0`.

- KIO `6.30.0-0supralinux5`: job `107523339110`, artifact `10794251210`, artifact SHA-256 `45eac20aca30ca6a5ef78d8a94d15ee5408a8bed39c8fa72c6c8823134ffa0b2`, adapted rules SHA-256 `365ef3d5c2e2f13fb5e7c82891cddea72d4ec7538010b14fb834048d352bc2ee`.
- KXMLGui `6.30.0-0supralinux4`: job `107523339321`, artifact `10793229286`, artifact SHA-256 `44b9cf9d0ad12f06b12bda37c291fcda5ecf933e25cfdd61c42d9df6e11b0093`, adapted rules SHA-256 `65cd53913bb5e4ac48cd96b38606acf33bc0cc054128b9733508bffdd2d8a7b2`.

The generated campaign is refreshed to those exact source artifacts. `execution_authorized=false` remains unchanged; Attempt 5 is still gated by Repository Policy and Level 1 planning validation. No binary PASS or stable publication is implied.

## Attempt 5 lifecycle pre-validation

The round-9 source pins passed Repository Policy `35990068378` and the paused Level 1 planner `35990068382` at commit `45675c1fb5a43f95204c2cf0c5c15df0ef703832`. The planner reported the intentional skip; rootfs and build-matrix jobs were skipped, so no package build occurred.

The validators are now pre-armed for a future active Attempt 5 using exactly KIO `6.30.0-0supralinux5` artifact `10794251210` and KXMLGui `6.30.0-0supralinux4` artifact `10793229286`, with activation evidence pinned to Policy `35990068378`, Level 1 `35990068382`, and commit `45675c1fb5a43f95204c2cf0c5c15df0ef703832`.

This pre-validation does not authorize execution. `execution_authorized=false` remains authoritative until a separate activation commit passes its own gates.

## Attempt 5 activation

The promoted round-9 sources passed planning validation in Repository Policy `35990068378` and paused Level 1 `35990068382` at commit `45675c1fb5a43f95204c2cf0c5c15df0ef703832`. The forward-compatible active lifecycle itself then passed Repository Policy `35990715536`, Level 1 `35990715990`, and materialization `35990715302` at commit `6ed2f38cdc0e092b6bf639a8a5b0b2461057784a`.

A separate activation commit now authorizes the complete two-node Attempt 5. KIO consumes `6.30.0-0supralinux5` artifact `10794251210`; KXMLGui consumes `6.30.0-0supralinux4` artifact `10793229286`. Scheduling remains parallel with `fail-fast=false`.

KIO retains its documented node-scoped network exception; KXMLGui remains network-disabled. No stable promotion is authorized by a package PASS.

## Attempt 5 result — round 10 follow-up

Workflow `35991007820` at commit `3197c1988e1ab86ec5010cb693064db949bfe6b0` completed with KIO FAIL and KXMLGui FAIL. Shared rootfs evidence is artifact `10804620493`, artifact SHA-256 `0855a64addfe52eb38ae3f71b4e7a8c3c1a08c5351dfa677ba03e0933426ca21`, inner SHA-256 `ecc2df763b7dd14b8812bfebedecb1ff3c532dd970cb3f1f5b2973b750d9740c`.

**KIO** job `107605066803`, artifact `10804966399`, SHA-256 `850d56de4b07a9b0d2fd3dd2730ef13381fdcf4f0e9059e097cb829809a25ad3`: **67/69 CTest targets PASS**. The two failures remain `kdirmodeltest` and `knewfilemenutest`, but Attempt 5 proves why round 9 did not change them: CTest injects `QT_QPA_PLATFORM=offscreen` directly into those tests, overriding the outer XCB environment. Round 10 therefore changes only those two CTest properties to XCB/Breeze while keeping Xvfb and the complete suite.

**KXMLGui** job `107605066954`, artifact `10804084102`, SHA-256 `92adc73ad8242e07299b5ae20c0acd100979e78f0b7da6ebb8fb5686c4c7204a`: build succeeded and **7/7 CTest targets PASS**. The remaining failure is post-test packaging proof: add `libkf6textwidgets-dev (>= 6.30.0~) <!nocheck>` so the modeled upstream test-only predecessor is installed/proven, and add `_ZSt19piecewise_construct@Base` as an optional `6.30.0` symbol baseline rather than accepting a Debian-revision ABI version.

Attempt 6 is not authorized. The next gate is `tier3-round10-level1-materialization`.
