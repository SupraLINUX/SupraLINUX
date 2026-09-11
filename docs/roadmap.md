# Development roadmap

Status: **planning document**  
Last reviewed: **2026-09-11**

The phases are gates, not calendar promises. A later phase may be prepared in parallel, but it is not promoted as complete until its evidence exists.

## Phase 0 — architecture bootstrap

- architecture and authority/provider ADR;
- machine-readable desktop-stack manifest;
- explicit Ubuntu 26.04 hosted policy CI;
- self-hosted runner contract;
- documentation status discipline.

## Phase 1 — package-build proof

- trivial SupraLINUX Debian source package;
- clean Ubuntu 26.04 sbuild;
- preserve `.deb`, `.changes`, `.buildinfo` and logs;
- autopkgtest smoke test;
- QEMU-based system test path;
- classify build outcome as PASS/FAIL/BLOCKED.

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
