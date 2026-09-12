# KDE Frameworks 6.30 — Tier 1

Status: **29-node source set fixed; dependencies/provider references resolved; Attica hosted package PASS; 28 package nodes pending**  
Last reviewed: **2026-09-12**

## Authority and scope

Tier membership comes from KDE's API index. KDE defines Tier 1 as Frameworks depending only on Qt and possibly third-party libraries, never on another KDE Framework.

The selected release is KDE Frameworks **6.30.0**. Source URLs, source hashes, build requirements and defaults come from KDE upstream. Ubuntu and Debian packaging remain provider/compatibility references only.

Frameworks 6.30 declares Qt >= **6.9.0**. SupraLINUX currently uses Ubuntu Resolute Qt **6.10.2** as provider candidate with hosted preflight evidence. Final Qt-provider certification still requires broader selected KDE builds, runtime/compatibility evidence and the authoritative release lane.

## Prerequisite

Extra CMake Modules 6.30.0 is the build-system predecessor and hosted DAG root:

- package: `extra-cmake-modules 6.30.0-0supralinux3`;
- workflow run: `34694951158`;
- artifact: `10298635300`;
- `.deb` SHA-256: `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- hosted state: **PASS**, downstream eligible.

Tier 1 builds may consume only this retained PASS predecessor in the hosted campaign.

## Fixed Tier 1 set

`manifests/kde-frameworks-tier1.json` contains these **29** KDE Tier 1 nodes:

`attica`, `bluez-qt`, `karchive`, `kcalendarcore`, `kcodecs`, `kconfig`, `kcoreaddons`, `kdbusaddons`, `kglobalaccel`, `kguiaddons`, `kholidays`, `ki18n`, `kidletime`, `kirigami`, `kitemmodels`, `kitemviews`, `kplotting`, `kquickcharts`, `syntax-highlighting`, `ktexttemplate`, `kuserfeedback`, `kwidgetsaddons`, `kwindowsystem`, `modemmanager-qt`, `networkmanager-qt`, `prison`, `solid`, `sonnet`, `threadweaver`.

Every node remains pinned to upstream 6.30.0, its KDE-published source SHA-256, no KDE Framework dependency, and ECM as build-system predecessor.

## Dependency/provider evidence

External dependency metadata is machine-readable in `manifests/kde-frameworks-tier1-dependencies.json`. The policy keeps `required`, `default_enabled`, `recommended`, `optional`, `runtime` and `required_any_of` distinct and keeps Qt components separate from other dependencies.

First valid hosted provider PASS:

- workflow run: `34700048774`;
- artifact: `10299608166`;
- artifact SHA-256: `da6808c31554da4105713e060e328d4130253a100c628fef279d8d0a9cf8ceb3`.

This proves candidate availability/coherence only. It does not turn an unbuilt Framework into PASS.

Source packaging-reference PASS:

- run `34701132721`;
- artifact `10299579234`;
- artifact SHA-256 `a2951c297f125ad81d1487075f0a0a6250114c4e875f3ba3870c3c18c09adaca`.

Binary-contract reference PASS:

- run `34704117024`;
- artifact `10301282501`;
- artifact SHA-256 `9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97`.

Neither reference snapshot is authoritative over KDE.

## First real Tier 1 package — Attica PASS

Attica 6.30.0 was attempted twice.

Attempt 1, package `6.30.0-0supralinux1`:

- run `34705165994`;
- artifact `10300903114`;
- artifact SHA-256 `171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300`;
- result: **FAIL** at `source-package` because host-side `dpkg-buildpackage -S` invoked `debian/rules` before the clean sbuild environment.

Attempt 2, package `6.30.0-0supralinux2`:

- commit `9945bfa92d776d432c76e17516b0ff9452b6d159`;
- run `34706416753`;
- artifact `10301851297`;
- artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`;
- result: **PASS**;
- tests: **6/6 PASS**;
- Lintian error gate: **PASS**;
- ABI SONAME: `libKF6Attica.so.6`;
- consumer smoke: **PASS**;
- `.buildinfo` proves ECM `6.30.0-0supralinux3`;
- downstream eligible: **yes**.

The historical FAIL remains retained, but the current Attica node state is PASS.

## Current node states

- `attica`: **PASS**, `6.30.0-0supralinux2`, downstream eligible;
- remaining 28 Tier 1 nodes: **pending**;
- current Tier 1 FAIL nodes: **0**;
- current Tier 1 BLOCKED nodes: **0**.

An unattempted node remains pending. A node becomes FAIL only after a real attempt fails for its own cause. BLOCKED is used only when a required predecessor is FAIL and the node therefore cannot be attempted.

## Policy validation

Repository Policy validates:

- exact 29-node upstream set and hashes;
- exact 6.30 dependency-metadata blob pins;
- Qt and external dependency minima;
- ECM PASS predecessor;
- provider/reference evidence;
- Attica's exact FAIL→PASS history and retained artifact hashes;
- Attica's hosted/non-authoritative status and downstream eligibility;
- all remaining Tier 1 package/DAG states staying pending until actually attempted.

## Next stage

The proven path is now:

KDE source + hash → source package → retained ECM PASS → fresh Resolute `sbuild` → tests/ABI/policy → consumer smoke → retained artifacts → explicit DAG state.

The next engineering task is to generalize this path for the remaining 28 independent Tier 1 nodes and prepare enough package definitions to run them in parallel. Independent failures must not stop unrelated nodes; only PASS artifacts may feed later tiers.
