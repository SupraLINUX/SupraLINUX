# KDE Frameworks 6.30 Tier 1 — packaging reference trees

Status: **generic capture implemented; first hosted capture pending CI evidence**  
Last reviewed: **2026-09-12**

## Purpose and authority

SupraLINUX needs exact Debian-family packaging trees as compatibility and implementation references while preparing KDE Frameworks packages. These trees do not select the KDE version and are not authoritative over KDE build requirements, defaults or features.

KDE upstream stable remains authority. Ubuntu Resolute and Debian sid are providers of technical packaging references only.

The selected set is KDE Frameworks **6.30.0** Tier 1: 29 nodes. The generic capture produces two reference trees per node — Ubuntu Resolute and Debian sid — for an expected total of **58 `debian/` trees**.

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

## CI scope

The workflow uses the verified event-delta scope pattern. It runs the external capture only when one of its actual inputs changes:

- `manifests/kde-frameworks-tier1.json`;
- `manifests/kde-frameworks-tier1-packaging-reference.json`;
- `scripts/run-kde-tier1-packaging-tree-snapshot.sh`;
- `scripts/kde-tier1-packaging-tree-needed.sh`;
- `.github/workflows/kde-tier1-packaging-tree.yml`.

Documentation and validator-only edits do not refresh external packaging trees. `workflow_dispatch` remains available when an explicit current-reference refresh is wanted.

## Relationship to existing evidence

The existing source packaging-reference snapshot and binary-contract snapshot remain valid technical evidence. This lane adds the missing full `debian/` trees; it does not replace or reinterpret their historical artifacts.

Attica's validated package PASS continues to depend on its already-retained reference artifact from run `34704689773`. That artifact remains immutable historical build input. The new generic tree artifact is intended to feed preparation of the remaining Tier 1 nodes after its own capture evidence passes review.

## Package-state boundary

A packaging-reference-tree PASS is not a Framework package PASS.

The capture must not alter the package DAG. Current package state remains:

- Attica: hosted package **PASS**;
- other 28 Tier 1 nodes: `pending`;
- no node becomes FAIL or BLOCKED because a reference capture itself fails.

A failure in this lane is a reference/provenance pipeline failure. Package PASS/FAIL begins only when the corresponding SupraLINUX package is actually attempted.

## First gate

The first hosted run must demonstrate all 29 Ubuntu source records, all 29 Debian source records, 58 checksum-verified Debian packaging tarballs, 58 extracted `debian/` trees and complete normalized provenance. Only after inspecting that artifact will the documentation and machine-readable evidence record this lane as PASS.
