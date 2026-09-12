# KDE Frameworks 6.30 Tier 1 — packaging preparation

Status: **provider preflight PASS; source packaging-reference snapshot PASS; binary-contract snapshot PASS; Framework packaging/build campaign pending**  
Last reviewed: **2026-09-12**

## Purpose

Before writing SupraLINUX `debian/` metadata for the 29 Tier 1 Frameworks, the project captures current Ubuntu Resolute and Debian sid packaging metadata as technical reference evidence.

This does **not** change project authority:

- KDE Frameworks 6.30.0 source/build metadata remains authoritative for KDE requirements, features and defaults;
- Ubuntu Resolute remains the platform and compatibility reference;
- Debian and Ubuntu packaging may inform package names, dependency expressions, Multi-Arch layout, symbols/shlibs handling and other Debian-policy details;
- neither distro is allowed to select the KDE version or silently disable an upstream default feature.

## Why two packaging references

Ubuntu Resolute is the direct compatibility target, but its Frameworks packages trail the selected KDE Frameworks 6.30.0 stack. Debian sid is closer to current Frameworks packaging and is therefore useful for newer packaging mechanics. Both remain references only.

The snapshots record what each archive actually publishes at execution time rather than hard-coding an assumed distro version into SupraLINUX architecture.

## Machine-readable mapping

`manifests/kde-frameworks-tier1-packaging-reference.json` maps each of the fixed 29 Tier 1 nodes to its Debian-family source package (`kf6-<framework>`).

The manifest is explicitly:

- `authority: false`;
- `role: packaging-reference-only`;
- backed by retained workflow/artifact evidence;
- prohibited from changing a Framework's build/DAG state.

Repository Policy verifies that this node set exactly matches `manifests/kde-frameworks-tier1.json` and that every Framework remains `packaging.state=pending` and `state=pending` until an actual package build is attempted.

## Source-packaging reference PASS

The retained source snapshot resolved all **58** expected source records: 29 from Ubuntu Resolute and the same 29 from Debian sid.

Evidence:

- workflow run: `34701132721`;
- PR head: `943a99f7465e311bbc72d63cbe6555a29aa4b5ab`;
- artifact: `10299579234`;
- artifact SHA-256: `a2951c297f125ad81d1487075f0a0a6250114c4e875f3ba3870c3c18c09adaca`;
- normalized `snapshot.json` SHA-256: `601c668342c206af179e9c564bf87cac6a166f1070fe9af0b640cb57d2151597`;
- `versions.tsv` SHA-256: `af6fd90121801eaf322442c43b793422494dfd5a109edccf484f5d24b463ea9b`;
- result: `PASS`, `authority=false`, `role=packaging-reference-only`, `framework_package_build_certification=pending`.

Observed reference versions:

- Ubuntu Resolute: 28 nodes at upstream `6.24.0`; `modemmanager-qt` at `6.23.0`;
- Debian sid: 28 nodes at upstream `6.28.0`; `syntax-highlighting` at `6.28.1`.

These versions are evidence about reference packaging only. SupraLINUX remains selected on KDE Frameworks **6.30.0**.

The binary-package name sets exposed by the source stanzas are identical for **28 of 29** nodes. The exception is `kirigami`, where Debian adds:

- `libkirigamiforms6`;
- `libkirigamiformsprivatecards6`;
- `libkirigamiformsprivateflat6`;
- `libkirigamiformsprivatetemplates6`.

Fourteen source packages also have Build-Depends name differences between the Ubuntu and Debian references. Those differences are reference signals, not architecture decisions.

## Binary-contract reference PASS

The source snapshot alone is insufficient to preserve Debian/Ubuntu compatibility because it does not provide the complete installed binary-package contract.

`.github/workflows/kde-tier1-binary-contract-reference.yml` therefore captures the following fields for every binary package published by the selected source stanzas in both archives:

- package version and source-package relationship;
- `Architecture` and `Multi-Arch`;
- `Pre-Depends`, `Depends`, `Recommends`, `Suggests` and `Enhances`;
- `Provides`, `Breaks`, `Replaces` and `Conflicts`;
- `Section` and `Priority`.

The retained PASS is:

- workflow run: `34704117024`;
- PR head: `be7a53c34a7ac27065f848ea3abc14b867673bde`;
- artifact: `10301282501`;
- artifact SHA-256: `9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97`;
- `binary-query-plan.tsv` SHA-256: `b26c95d381db242c3c7a87228044a37bac8696e211358149a08bb5b55f411bb9`;
- `binary-contracts.json` SHA-256: `e44507d0dd73db913a91bd4852c452f783618aab0bd6a3790e4c4f4c40707b7b`;
- `binary-contracts.tsv` SHA-256: `ef29ecdf03a35616a7cd0155a54a0d93828ff2af9bd9a3dcba37c0dbdb8bb1ca`;
- Ubuntu binary records: `147`;
- Debian binary records: `151`;
- common binary package names: `147`;
- Ubuntu-only names: `0`;
- Debian-only names: `4` (the four Kirigami Forms libraries listed above);
- result: `PASS`, `authority=false`, `role=binary-packaging-contract-reference-only`, `framework_package_build_certification=pending`.

The metric `packages_with_contract_differences` is not itself an incompatibility count because versioned dependencies and Ubuntu's `universe/` section prefix naturally differ. Compatibility decisions must be made field-by-field.

The binary/source indexes use independent APT list directories. Debian sid is queried only as archive metadata: no Debian binary package is installed, no Debian repository is added to the host's normal APT configuration, and Debian never becomes a provider for SupraLINUX.

## Attica packaging contract selected for first proof

Attica is intentionally the first real Tier 1 packaging proof because KDE 6.30 upstream has a small dependency surface: ECM 6.30, Qt Core/Network >= 6.9, and Qt Test only when tests are enabled. The library keeps `SOVERSION 6` and installs the shared library, development headers, CMake package files, pkg-config metadata, logging categories and QDoc output.

The two retained packaging references agree on the package split:

- `libkf6attica6` — runtime library;
- `libkf6attica-dev` — development files;
- `libkf6attica-doc` — documentation.

The structural binary contracts also agree:

- `libkf6attica6`: `Multi-Arch: same`;
- `libkf6attica-dev`: depends on the exact matching runtime package and Qt base development package, and recommends the exact matching doc package;
- `libkf6attica-doc`: `Architecture: all`, `Multi-Arch: foreign`;
- no reference Attica package declares `Provides`, `Breaks`, `Replaces` or `Conflicts`.

Ubuntu and Debian differ only in archive-specific section naming and version/minimum expressions for this node. SupraLINUX packaging must retain the structural contract while using KDE 6.30 and the selected Resolute Qt provider.

## Evidence semantics

Both packaging-reference PASS states are **non-authoritative**. They prove that coherent reference metadata was captured; they do not prove that any SupraLINUX Framework package builds.

Therefore reference PASS states do not change any Framework node to PASS, FAIL or BLOCKED.

## Next gate

The next gate is the real Attica 6.30.0 package build. Its `debian/` tree must be justified against exact KDE 6.30.0 outputs, the resolved dependency/provider manifest and the retained compatibility contracts.

The build campaign reuses the established ECM model:

KDE source + verified SHA-256 → Debian source package → fresh Resolute build root → retained ECM PASS artifact → `sbuild` → `.deb/.changes/.buildinfo` → Lintian/tests/consumer checks → DAG evidence.

Only a real attempted Attica build may change the `attica` DAG state from `pending` to PASS or FAIL.
