# KDE Frameworks 6.30 Tier 1 — packaging reference trees

Status: **generic hosted capture PASS; 58 hash-verified reference trees retained; package states unchanged**  
Last reviewed: **2026-09-12**

## Purpose and authority

SupraLINUX needs exact Debian-family packaging trees as compatibility and implementation references while preparing KDE Frameworks packages. These trees do not select the KDE version and are not authoritative over KDE build requirements, defaults or features.

KDE upstream stable remains authority. Ubuntu Resolute and Debian sid are providers of technical packaging references only.

The selected set is KDE Frameworks **6.30.0** Tier 1: 29 nodes. The generic capture produces two reference trees per node — Ubuntu Resolute and Debian sid — for a total of **58 `debian/` trees**.

## Provenance model

The capture does not hardcode 58 archive URLs or trust unsigned web metadata.

For each distro it configures isolated `deb-src` indices with the distro archive keyring, updates them through APT, and records the source package metadata returned by those signed indices. For each selected source package it:

1. selects the newest exact source record visible in the configured reference series;
2. refuses to continue if the reference upstream version is newer than selected KDE 6.30.0, forcing an explicit review instead of silently importing future packaging policy;
3. reads `Directory` and `Checksums-Sha256` from the source record;
4. requires exactly one `.debian.tar.*` member;
5. downloads that exact Debian packaging tarball over HTTPS;
6. verifies its SHA-256 against the signed source-index metadata and verifies its declared byte size;
7. extracts the complete `debian/` tree;
8. records per-file hashes plus the archive, source package, version and URL provenance.

The normalized evidence contains `snapshot.json`, `versions.tsv`, `download-plan.tsv`, `tree-hashes.tsv`, source-index records, source-list hashes, the 58 extracted trees and pipeline/result records.

## First hosted capture — PASS

The first complete generic capture ran from commit `310510007d29c5d844d0dba770635c7336884a3d`.

- workflow run: `34708030450`;
- artifact: `10301938362`;
- GitHub artifact SHA-256: `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`;
- `snapshot.json` SHA-256: `f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345`;
- `versions.tsv` SHA-256: `af6fd90121801eaf322442c43b793422494dfd5a109edccf484f5d24b463ea9b`;
- `download-plan.tsv` SHA-256: `0b8776adbe14a9629350d1d00bc48475b32b5dbeae57e60ca15b7d69e18560b4`;
- `tree-hashes.tsv` SHA-256: `abf95096bbc16718102a53a132a576c9f61252d13321c58027325ffb2819c09e`;
- nodes: `29`;
- Ubuntu trees: `29`;
- Debian trees: `29`;
- total packaging trees: `58`;
- result: `PASS`, stage `complete`, exit code `0`;
- source-index provenance: `APT-verified`;
- package-state effect: none.

The artifact was inspected after download. It contains exactly 29 unique Tier 1 nodes and 58 tree records. All 58 `tree-files.sha256` manifests hash to the values recorded in `tree-hashes.tsv`, and every regular file referenced by those 58 manifests matches its recorded SHA-256 inside the retained artifact.

Observed reference upstream versions remain below selected KDE 6.30.0: Ubuntu references are 6.23.0/6.24.0 and Debian references are 6.28.0/6.28.1.

Machine-readable PASS evidence is retained separately in `manifests/kde-frameworks-tier1-packaging-tree-evidence.json`. Keeping capture inputs and evidence state separate prevents an evidence-only update from becoming a reason to refresh external reference trees.

## CI scope

The workflow uses the verified event-delta scope pattern. It runs the external capture only when one of its actual inputs changes:

- `manifests/kde-frameworks-tier1.json`;
- `manifests/kde-frameworks-tier1-packaging-reference.json`;
- `scripts/run-kde-tier1-packaging-tree-snapshot.sh`;
- `scripts/kde-tier1-packaging-tree-needed.sh`;
- `.github/workflows/kde-tier1-packaging-tree.yml`.

Documentation, validator-only edits and `manifests/kde-frameworks-tier1-packaging-tree-evidence.json` do not refresh external packaging trees. `workflow_dispatch` remains available when an explicit current-reference refresh is wanted.

## Relationship to existing evidence

The existing source packaging-reference snapshot and binary-contract snapshot remain valid technical evidence. This lane adds the missing full `debian/` trees; it does not replace or reinterpret their historical artifacts.

Attica's validated package PASS continues to depend on its already-retained reference artifact from run `34704689773`. That artifact remains immutable historical build input. The generic artifact from run `34708030450` is available to feed preparation of the remaining Tier 1 nodes.

## Package-state boundary

A packaging-reference-tree PASS is not a Framework package PASS.

The capture does not alter the package DAG. Current package state remains:

- Attica: hosted package **PASS**;
- other 28 Tier 1 nodes: `pending`;
- no node becomes FAIL or BLOCKED because a reference capture itself fails.

A failure in this lane is a reference/provenance pipeline failure. Package PASS/FAIL begins only when the corresponding SupraLINUX package is actually attempted.

## Next use

Use the retained generic trees together with the existing binary-contract snapshot and KDE 6.30 upstream metadata to prepare multiple independent Tier 1 packages in parallel. Distro packaging choices remain reference inputs only: any option that conflicts with KDE 6.30 upstream requirements/defaults must be rejected or explicitly justified for SupraLINUX.
