# KDE Frameworks 6.30 — Tier 1 source manifest

Status: **source set fixed; packaging/external dependency resolution pending**  
Last reviewed: **2026-09-12**

## Authority and scope

Tier membership comes from KDE's current API index. KDE defines Tier 1 as frameworks that depend only on Qt and possibly third-party libraries, never on another KDE Framework.

The selected release is KDE Frameworks **6.30.0**. Source URLs and SHA-256 values come from KDE's 6.30.0 release information page, not from Ubuntu package versions.

KDE states that Frameworks 6.30.0 requires **Qt 6.9.0**. SupraLINUX currently selects the Ubuntu Resolute Qt **6.10.2** provider in its hosted provider preflight, so the selected provider is newer than the Frameworks minimum. Plasma's own selected Qt profile remains a separate desktop-level requirement and authority decision.

## Prerequisite

Extra CMake Modules is the Tier 0/build-system predecessor and has a hosted clean-package PASS:

- package: `extra-cmake-modules` `6.30.0-0supralinux3`;
- workflow run: `34694951158`;
- `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

Only this retained PASS artifact is eligible to feed the Tier 1 hosted build campaign.

## Fixed Tier 1 set

The machine-readable manifest `manifests/kde-frameworks-tier1.json` contains **29** KDE-upstream Tier 1 nodes:

`attica`, `bluez-qt`, `karchive`, `kcalendarcore`, `kcodecs`, `kconfig`, `kcoreaddons`, `kdbusaddons`, `kglobalaccel`, `kguiaddons`, `kholidays`, `ki18n`, `kidletime`, `kirigami`, `kitemmodels`, `kitemviews`, `kplotting`, `kquickcharts`, `syntax-highlighting`, `ktexttemplate`, `kuserfeedback`, `kwidgetsaddons`, `kwindowsystem`, `modemmanager-qt`, `networkmanager-qt`, `prison`, `solid`, `sonnet`, `threadweaver`.

Every node currently has:

- upstream version `6.30.0`;
- exact KDE stable tarball URL;
- KDE-published SHA-256;
- `kde_framework_dependencies: []`;
- build-system predecessor `extra-cmake-modules`;
- external dependency resolution: `pending-resolution`;
- packaging state: `pending`;
- DAG state: `pending`.

`pending` is intentional: no Tier 1 node has been attempted yet, so none is PASS, FAIL or BLOCKED.

## Policy

Repository Policy executes `scripts/validate_kde_tier1.py`. The validator pins the exact 29-node upstream set and every KDE-published SHA-256, enforces the Qt minimum/provider evidence, requires the ECM PASS predecessor and rejects invented Tier 1-to-Tier 1 Framework dependencies.

## Next implementation step

Resolve each node's non-KDE build dependencies and Debian package contracts using upstream build metadata first and Ubuntu/Debian packaging only as technical reference. Then create the package campaign so all prepared independent Tier 1 nodes run in parallel, consume the verified ECM PASS artifact, and retain individual PASS/FAIL evidence. A node is not marked FAIL merely because its packaging has not yet been prepared.
