# KDE Frameworks Tier 3 — build Level 1

Status: **planning prepared; binary execution unauthorized** as of 2026-09-23.

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
