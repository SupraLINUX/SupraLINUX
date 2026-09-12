# KDE Frameworks 6.30 — Tier 1

Status: **source set fixed; external dependency metadata resolved; Ubuntu provider preflight PASS; packaging pending; build campaign pending**  
Last reviewed: **2026-09-12**

## Authority and scope

Tier membership comes from KDE's API index. KDE defines Tier 1 as frameworks that depend only on Qt and possibly third-party libraries, never on another KDE Framework.

The selected release is KDE Frameworks **6.30.0**. Source URLs and SHA-256 values come from KDE's 6.30.0 release information page, not from Ubuntu package versions.

KDE Frameworks 6.30.0 declares a Qt minimum of **6.9.0**. SupraLINUX has hosted preflight evidence for the Ubuntu Resolute Qt **6.10.2** candidate. Ubuntu remains provider only; selected Frameworks, Plasma and KWin builds plus runtime/package-compatibility evidence are still required before final Qt-provider certification.

## Prerequisite

Extra CMake Modules is the Tier 0/build-system predecessor and has a hosted clean-package PASS:

- package: `extra-cmake-modules` `6.30.0-0supralinux3`;
- workflow run: `34694951158`;
- `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

Only this retained PASS artifact is eligible to feed the Tier 1 hosted build campaign.

## Fixed Tier 1 set

`manifests/kde-frameworks-tier1.json` contains **29** KDE-upstream Tier 1 nodes:

`attica`, `bluez-qt`, `karchive`, `kcalendarcore`, `kcodecs`, `kconfig`, `kcoreaddons`, `kdbusaddons`, `kglobalaccel`, `kguiaddons`, `kholidays`, `ki18n`, `kidletime`, `kirigami`, `kitemmodels`, `kitemviews`, `kplotting`, `kquickcharts`, `syntax-highlighting`, `ktexttemplate`, `kuserfeedback`, `kwidgetsaddons`, `kwindowsystem`, `modemmanager-qt`, `networkmanager-qt`, `prison`, `solid`, `sonnet`, `threadweaver`.

Every node has:

- upstream version `6.30.0`;
- exact KDE stable tarball URL;
- KDE-published source SHA-256;
- `kde_framework_dependencies: []`;
- build-system predecessor `extra-cmake-modules`;
- a resolved dependency reference into `manifests/kde-frameworks-tier1-dependencies.json`;
- packaging state `pending`;
- DAG state `pending`.

`pending` remains intentional. Dependency/provider discovery is not a Framework build attempt, so no Tier 1 node becomes PASS, FAIL or BLOCKED from the provider gate alone.

## Dependency resolution

The non-KDE dependency model is documented in `docs/kde-tier1-dependencies.md` and machine-readable in `manifests/kde-frameworks-tier1-dependencies.json`.

Resolution rules are:

1. exact KDE `v6.30.0` build metadata is authoritative;
2. Linux/shared-library upstream defaults are preserved unless a documented decision changes them;
3. `required`, `default_enabled`, `recommended`, `optional`, `runtime` and `required_any_of` remain distinct;
4. Qt components are recorded separately from non-Qt dependencies;
5. Ubuntu Resolute package names are provider mappings only, never the source of KDE requirements;
6. hosted Ubuntu checks prove candidate availability/coherence only; package builds remain the certification gate.

## Provider preflight PASS

`.github/workflows/kde-tier1-dependency-preflight.yml` is a **non-authoritative hosted provider check** on Ubuntu 26.04.

First valid PASS evidence:

- workflow run: `34700048774`;
- PR head: `6ce61bc02c4aba146bcc33b16d17f56fb66f057a`;
- artifact: `10299608166`;
- artifact SHA-256: `da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3`.

The retained artifact proves that the selected mandatory/default-enabled Resolute provider set is installable, verifies sensitive minimum versions, keeps Qt/PySide/Shiboken coherent at 6.10.2, verifies HSpell's real development surface and passes the sensitive CMake discovery probe including Prison's upstream-compatible ZXing selection.

Historical run `34699717549` is retained as a gate-implementation FAIL caused by a broken-pipe interaction in the APT candidate helper. Historical run `34699889060` is retained as a gate-implementation FAIL caused by a ZXing CMake probe stricter than Prison 6.30 upstream. Neither represents a Framework FAIL because no Framework node was attempted.

A hosted provider PASS does **not** certify a Framework package and does not promote the Ubuntu Qt provider to final certification.

## Policy

Repository Policy executes `scripts/validate_kde_tier1.py`. The validator pins:

- the exact 29-node upstream set and source hashes;
- exact `v6.30.0` dependency-metadata blob SHAs;
- the Frameworks Qt minimum and current Qt-provider evidence state;
- the ECM PASS predecessor;
- the hosted Tier 1 dependency-provider PASS evidence;
- dependency classifications and sensitive minimum versions;
- the Sonnet at-least-one spell-backend rule;
- the real Ubuntu/Debian HSpell mapping (`hspell`, not an invented `libhspell-dev`);
- the requirement that packaging/DAG states remain pending until actual builds occur.

## Build-campaign contract

The next stage prepares Debian packaging for all 29 Tier 1 nodes and executes independent nodes in parallel. Each build must consume only retained PASS predecessors and preserve, at minimum:

- exact upstream source and source SHA-256;
- packaging revision and dependency set;
- build configuration;
- complete `sbuild` log;
- `.deb`, `.changes` and `.buildinfo` artifacts;
- artifact SHA-256 values;
- Lintian/test/consumer-smoke evidence where applicable;
- explicit DAG result `PASS`, `FAIL` or `BLOCKED`.

The existing ECM pipeline is the implementation model: verified KDE source → Debian source package → fresh Resolute build root → `sbuild` → artifact capture → package checks → consumer validation → DAG evidence.

An implemented package definition that has not yet been attempted remains `pending`. A node attempted and failing for its own cause becomes `FAIL`. A node is `BLOCKED` only when an actual prerequisite is `FAIL`; `BLOCKED` is never counted as `FAIL`.
