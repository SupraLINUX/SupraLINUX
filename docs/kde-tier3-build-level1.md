# KDE Frameworks Tier 3 — build Level 1

Status: **Attempt 1 active — KIO + KXMLGui authorized** as of 2026-09-23.

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
