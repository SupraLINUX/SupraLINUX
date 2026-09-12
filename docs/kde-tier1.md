# KDE Frameworks 6.30 — Tier 1

Status: **29-node source set fixed; 4 hosted package PASS; 25 package nodes pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-12**

## Authority and scope

Tier membership and source requirements come from KDE upstream. SupraLINUX selects KDE Frameworks **6.30.0**. Ubuntu Resolute provides the platform, Qt/general dependencies and compatibility target; Ubuntu/Debian packaging is technical reference only.

Frameworks 6.30 requires Qt >= **6.9.0**. Ubuntu Resolute Qt **6.10.2** is the current provider candidate with hosted preflight PASS; final provider certification still requires broader KDE/runtime/compatibility evidence.

## Prerequisite

Extra CMake Modules is the retained build-system root:

- `extra-cmake-modules 6.30.0-0supralinux3`;
- run `34694951158`;
- artifact `10298635300`;
- `.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`;
- state **PASS**, downstream eligible.

## Fixed Tier 1 set

The manifest contains exactly 29 nodes:

`attica`, `bluez-qt`, `karchive`, `kcalendarcore`, `kcodecs`, `kconfig`, `kcoreaddons`, `kdbusaddons`, `kglobalaccel`, `kguiaddons`, `kholidays`, `ki18n`, `kidletime`, `kirigami`, `kitemmodels`, `kitemviews`, `kplotting`, `kquickcharts`, `syntax-highlighting`, `ktexttemplate`, `kuserfeedback`, `kwidgetsaddons`, `kwindowsystem`, `modemmanager-qt`, `networkmanager-qt`, `prison`, `solid`, `sonnet`, `threadweaver`.

Every node remains pinned to KDE 6.30.0 and its KDE-published SHA-256. A Tier 1 node has no KDE Framework predecessor other than the ECM build-system root.

## Reference evidence

- provider availability: run `34700048774`, artifact `10299608166`;
- source packaging reference: run `34701132721`, artifact `10299579234`;
- binary-contract reference: run `34704117024`, artifact `10301282501`;
- generic 58-tree packaging reference: run `34708030450`, artifact `10301938362`.

These gates are non-authoritative references and do not promote package state.

## Current package PASS nodes

- **Attica** `6.30.0-0supralinux2`: run `34706416753`, artifact `10301851297`, tests 6/6 PASS, downstream eligible.
- **KCodecs** `6.30.0-0supralinux4`: run `34716761551`, job `103615297758`, artifact `10305050385`, SHA-256 `d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45`, tests 8/8 PASS, Lintian/ABI/consumer PASS.
- **KDBusAddons** `6.30.0-0supralinux3`: run `34713034164`, job `103605147881`, artifact `10304340428`, tests 3/3 PASS, full package gate PASS.
- **ThreadWeaver** `6.30.0-0supralinux3`: run `34713034164`, job `103605147772`, artifact `10303986419`, tests 8/8 PASS, full package gate PASS.

Historical FAIL attempts remain attached to each node as evidence; they do not change the current PASS state.

## KCodecs ABI/symbol policy

Ubuntu 6.24's symbols reference was stale for KDE 6.30 because it still required two `KCharsets` constructors already absent from Debian 6.28. SupraLINUX therefore uses the retained Debian 6.28 symbols reference as the technical baseline.

KDE 6.30's `std::format` use emits 15 compiler/libstdc++ implementation symbols. They are retained in the reviewed symbols file as `(optional=toolchain)` with minimum **6.30.0**, never a Debian revision. `dpkg-gensymbols -c4` was verified against the actual built library before the clean hosted attempt, and the real `-0supralinux4` build then PASSed.

## Current states

- PASS: **4**;
- pending: **25**;
- current FAIL: **0**;
- BLOCKED: **0**.

A node becomes FAIL only after a real package attempt fails for its own cause. BLOCKED is reserved for nodes not attempted because a predecessor is FAIL.

## CI scope

Batch 1 package CI fingerprints only build inputs actually consumed by the runner. State/evidence/hash bookkeeping, validators and documentation must not rebuild an already-PASS node. A run selected by an infrastructure scope bug that aborts before source/package work is not recorded as a package FAIL.

## Batch 2 prepared

KTextTemplate, KArchive and KHolidays are the next independent package attempts. Their preparation lives in a separate Batch 2 campaign so the closed Batch 1 ledger and runner remain reproducible. Debian 6.28 symbols are used as the closer technical ABI baseline while Ubuntu Resolute remains the direct binary-compatibility target. KDE 6.30 upstream defaults and autotests remain enabled; stale distro `BUILD_QCH` settings are not inherited.

Canonical state is still **4 PASS / 25 pending / 0 FAIL / 0 BLOCKED** until these jobs actually attempt their packages.
