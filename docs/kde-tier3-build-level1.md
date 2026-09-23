# KDE Frameworks Tier 3 — build Level 1

Status: **Attempt 3 active — KIO + KXMLGui full Level 1 rerun** as of 2026-09-23.

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
