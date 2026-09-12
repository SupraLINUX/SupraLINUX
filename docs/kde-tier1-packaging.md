# KDE Frameworks 6.30 Tier 1 — packaging preparation and campaign

Status: **provider/source/binary reference gates PASS; Attica package PASS; 28 Tier 1 packages pending**  
Last reviewed: **2026-09-12**

## Authority model

KDE Frameworks 6.30.0 source/build metadata defines requirements, defaults and selected KDE version. Ubuntu Resolute is the platform/provider and compatibility target. Debian/Ubuntu packaging is technical reference for Debian contracts only.

Reference metadata never promotes a Framework node. Only an actual package attempt may produce PASS/FAIL; BLOCKED is reserved for nodes that cannot be attempted because a prerequisite is FAIL.

## Source packaging-reference PASS

The source snapshot resolved all 58 expected source records (29 Ubuntu Resolute + 29 Debian sid):

- run `34701132721`;
- artifact `10299579234`;
- artifact SHA-256 `a2951c297f125ad81d1487075f0a0a6250114c4e875f3ba3870c3c18c09adaca`;
- `snapshot.json` SHA-256 `601c668342c206af179e9c564bf87cac6a166f1070fe9af0b640cb57d2151597`;
- `versions.tsv` SHA-256 `af6fd90121801eaf322442c43b793422494dfd5a109edccf484f5d24b463ea9b`.

Ubuntu references are mostly 6.24.0 (`modemmanager-qt` 6.23.0); Debian references are mostly 6.28.0 (`syntax-highlighting` 6.28.1). SupraLINUX remains on KDE 6.30.0.

## Binary-contract reference PASS

The isolated binary-contract snapshot captured Architecture, Multi-Arch, dependency/recommendation fields, Provides/Breaks/Replaces/Conflicts and package/source relationships without installing Debian sid binaries:

- run `34704117024`;
- artifact `10301282501`;
- artifact SHA-256 `9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97`;
- `binary-contracts.json` SHA-256 `e44507d0dd73db913a91bd4852c452f783618aab0bd6a3790e4c4f4c40707b7b`.

There are 147 Ubuntu binary records and 151 Debian records. The four Debian-only names are the Kirigami Forms libraries identified by the source snapshot. This is a compatibility review signal, not authority.

## First package proof — Attica

The Attica packaging references agree on the core split:

- `libkf6attica6`;
- `libkf6attica-dev`;
- `libkf6attica-doc`.

Exact `debian/` reference trees were retained in run `34704689773`, artifact `10301617541`, SHA-256 `ce9e9949f643736f25ec27d2850cb0654334b64a28dfcd293df78ae1b1f60407`.

### Attempt 1 — FAIL

- package `6.30.0-0supralinux1`;
- run `34705165994`;
- artifact `10300903114`;
- artifact SHA-256 `171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300`;
- stage: `source-package`;
- cause: source assembly with `dpkg-buildpackage -S` executed KDE build helpers on the host before clean sbuild.

### Attempt 2 — PASS

The source package was instead assembled with `dpkg-source -b`, leaving package Build-Depends to the clean Resolute build root.

- package `6.30.0-0supralinux2`;
- run `34706416753`;
- artifact `10301851297`;
- artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`;
- source SHA-256 verified: `3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c`;
- retained ECM predecessor: `extra-cmake-modules 6.30.0-0supralinux3`;
- tests: 6/6 PASS;
- Lintian errors: PASS;
- SONAME: `libKF6Attica.so.6`;
- consumer smoke: PASS;
- downstream eligible: yes.

The doc compatibility package produces an `empty-binary-package` Lintian warning because Attica 6.30's QDoc targets are explicit rather than part of the normal build. This is retained evidence, not hidden; there are no Lintian errors.

## Current campaign state

`manifests/kde-frameworks-tier1.json` records:

- Attica: PASS, package `6.30.0-0supralinux2`, hosted/non-authoritative, downstream eligible;
- other 28 Tier 1 nodes: pending.

`manifests/kde-dag.json` records the same Attica node after the ECM PASS root, including both the historical FAIL and current PASS attempt.

## Generalized build contract

Every remaining Tier 1 package campaign must follow the same evidence model:

1. exact KDE 6.30 source + KDE-published SHA-256;
2. package metadata audited against current upstream requirements and retained compatibility references;
3. source package assembled without contaminating the host with package Build-Depends;
4. retained ECM PASS injected as predecessor;
5. fresh Resolute `sbuild` root;
6. upstream tests where deterministic, with any exclusions documented narrowly;
7. Debian binary contract/ABI review appropriate to the node;
8. fatal Lintian error gate;
9. consumer smoke where a useful public API can be exercised;
10. `.deb`, `.changes`, `.buildinfo`, `.dsc`, source/rootfs hashes and logs retained;
11. node marked PASS/FAIL only after the real attempt.

## Next implementation step

Generalize the Attica-specific runner into reusable Tier 1 package infrastructure while keeping package-specific policy (binary split, symbols, tests, patches, consumer smoke) explicit. Then prepare several independent low-dependency nodes and run them in parallel rather than serializing all 28 behind one package.
