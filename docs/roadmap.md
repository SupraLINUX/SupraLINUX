# Development roadmap

Status: **planning document**  
Last reviewed: **2026-09-11**

The phases are gates, not calendar promises. A later phase may be prepared in parallel, but it is not promoted as complete until its evidence exists.

## Phase 0 — architecture bootstrap

- architecture and authority/provider ADR;
- machine-readable desktop-stack manifest;
- explicit Ubuntu 26.04 hosted policy CI;
- authoritative disposable Ubuntu 26.04 KVM runner contract;
- documentation status discipline.

## Phase 1 — package-build proof

- trivial SupraLINUX Debian source package;
- GitHub-hosted non-authoritative clean-build preflight;
- disposable Ubuntu 26.04 KVM runner for authoritative execution;
- clean `sbuild/unshare` package build inside that VM;
- preserve `.deb`, `.changes`, `.buildinfo`, hashes and logs immediately after build;
- `autopkgtest/QEMU` smoke test in a nested Ubuntu 26.04 test VM;
- certify nested KVM and the QEMU base-image hash;
- classify each attempted/not-attempted gate using PASS/FAIL/BLOCKED semantics.

## Phase 2 — repository and publisher

- aptly repository layout;
- incoming/staging/candidate/stable promotion;
- separate builder and publisher responsibilities;
- signing only in the publisher path;
- repository integrity verification.

## Phase 3 — KDE metadata and DAG

- ingest official KDE stable source metadata;
- record source URLs, versions, tags and SHA-256 values from real downloads;
- derive package/component dependency relationships;
- topological campaign scheduler and status reporting.

## Phase 4 — Qt provider certification

- enumerate all Qt modules required by the selected KDE stack;
- test the Ubuntu Qt candidate first;
- certify or reject reuse based on evidence;
- if rejected, build a SupraLINUX Qt package set preserving Debian contracts as far as practical.

## Phase 5 — KDE stack

- KDE Frameworks stable;
- Plasma/KWin/Workspace/Breeze stable;
- KDE Gear stable;
- runtime session and upgrade tests;
- package precedence and repository integration.

## Phase 6 — system composition and recovery

- minimal Ubuntu base composition;
- desktop package seed/metapackages;
- Btrfs layout;
- Snapper snapshots and APT hooks;
- recovery environment;
- installer/image generation.

## Phase 7 — compatibility certification

- representative Ubuntu repository applications;
- third-party `.deb` applications;
- Multi-Arch cases;
- upgrade from previous SupraLINUX release state;
- ABI/shlibs/symbols regression checks for replaced libraries.
