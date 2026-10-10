# Development roadmap

Status: **planning document**  
Last reviewed: **2026-10-04**

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

Current package and gate state is generated in [docs/status/current.md](status/current.md). Frameworks has 65 retained build PASS records with environment scope recorded per node; only the KVM infrastructure and sample have been certified authoritatively. Plasma has 75 inventoried source nodes and 34 Level 0 materializations. Package admission advances individually and does not certify the whole stack.

- ingest official KDE stable source metadata;
- record source URLs, versions, tags and SHA-256 values from real downloads;
- derive package/component dependency relationships;
- topological campaign scheduler and status reporting.
- canonical Tier 2 manifest -> generated campaign plan, with provider-audit and package-contract gates before any build attempt.

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


## Completion criteria

The first deliverable is an amd64 live desktop image, an installer and a signed
APT repository, all built from the selected stack and retained source artifacts.
The desktop profile includes ordinary Plasma desktop functionality and its
integration dependencies. Mobile/TV components remain in the upstream inventory
and build campaign; their availability does not imply default installation on
the desktop image. Any exclusions must be recorded in the final seed.

The distribution remains in development until all of these gates close:

- Authoritative clean builds of the selected Frameworks, Plasma and Gear packages,
  with package tests, licensing, exact dependency inputs and retained sources.
- Ubuntu Qt reuse certification, library/plugin ABI checks and Ubuntu/third-party
  application installation and upgrade without unintended removals.
- A complete Wayland session: login, KWin rendering, audio, network, Bluetooth,
  power, portals, Discover and hardware-specific functions where applicable.
- Ubuntu-based composition, package seeds and signed APT metadata; testing and
  stable remain distinct publication stages.
- Btrfs/Snapper and APT-hook recovery, including a failed update and successful
  boot into a usable restored system without reverting user data.
- Live ISO boot, actual installation onto disposable VM disks, first boot,
  updates and recovery; BIOS/UEFI and Secure Boot behavior declared and tested.
- A final campaign from clean inputs, rebuild comparison and an offline restore
  of retained artifacts; documented limitations and manual release QA.

The final merge and stable publication require explicit approval after the
release evidence and installable image are ready for review. Package builds and
incremental integration continue under the existing authorization.
