# KDE Frameworks 6.30 — Tier 1

Status: **source set fixed; external dependency metadata resolved; Ubuntu provider mapping resolved; provider preflight pending; packaging pending**  
Last reviewed: **2026-09-12**

## Authority and scope

Tier membership comes from KDE's API index. KDE defines Tier 1 as frameworks that depend only on Qt and possibly third-party libraries, never on another KDE Framework.

The selected release is KDE Frameworks **6.30.0**. Source URLs and SHA-256 values come from KDE's 6.30.0 release information page, not from Ubuntu package versions.

KDE Frameworks 6.30.0 declares a Qt minimum of **6.9.0**. SupraLINUX currently has hosted preflight evidence for the Ubuntu Resolute Qt **6.10.2** candidate. That does not make Ubuntu authoritative for Qt and does not constitute final Qt certification; selected Frameworks, Plasma and KWin builds plus runtime/package-compatibility evidence are still required.

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

`pending` for packaging/DAG is intentional: dependency discovery is not a build attempt. No Tier 1 node becomes PASS, FAIL or BLOCKED until the corresponding build campaign actually runs.

## Dependency resolution

The non-KDE dependency model is documented in `docs/kde-tier1-dependencies.md` and machine-readable in `manifests/kde-frameworks-tier1-dependencies.json`.

Resolution rules are:

1. exact KDE `v6.30.0` build metadata is authoritative;
2. Linux/shared-library upstream defaults are preserved unless a later documented decision changes them;
3. `required`, `default_enabled`, `recommended`, `optional`, `runtime` and `required_any_of` are kept distinct;
4. Qt components are recorded separately from non-Qt dependencies;
5. Ubuntu Resolute package names are provider mappings only, never the source of KDE requirements;
6. provider mappings remain `resolved-pending-hosted-preflight` until the Resolute preflight records real APT candidates, installed versions and discovery checks.

## Policy

Repository Policy executes `scripts/validate_kde_tier1.py`. The validator pins:

- the exact 29-node upstream set and source hashes;
- exact `v6.30.0` dependency-metadata blob SHAs;
- the Frameworks Qt minimum and current Qt-provider evidence state;
- the ECM PASS predecessor;
- dependency classifications and sensitive minimum versions;
- the Sonnet at-least-one spell-backend rule;
- the real Ubuntu/Debian HSpell mapping (`hspell`, not an invented `libhspell-dev`);
- the requirement that packaging/DAG states remain pending until actual builds occur.

## Provider preflight

`.github/workflows/kde-tier1-dependency-preflight.yml` is a **non-authoritative hosted provider check** on Ubuntu 26.04. It is intended to prove that the mapped Resolute provider surface is real before packaging starts.

It checks package candidates, installs the mandatory/default-selected provider set, records installed versions, verifies important minimum versions, checks Qt/PySide/Shiboken coherence, probes sensitive CMake packages and preserves evidence under `evidence/kde-tier1-dependency-preflight/`.

A hosted preflight PASS does **not** certify a Framework package and does not promote the Ubuntu Qt provider to final certification.

## Next implementation step

After the dependency-provider preflight has real PASS evidence, prepare Debian packaging for all 29 Tier 1 nodes. Independent prepared nodes should run in parallel, consume only the retained ECM PASS artifact, and preserve per-node source, package, build log, `.deb`, `.changes`, `.buildinfo`, hashes and test evidence.

A packaging implementation that has not been attempted remains `pending`; a node whose prerequisite actually FAILs becomes `BLOCKED`; only a node attempted and failing for its own cause becomes `FAIL`.
