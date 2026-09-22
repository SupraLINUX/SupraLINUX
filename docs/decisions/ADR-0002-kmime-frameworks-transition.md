# ADR-0002 — KMime transition from KDE PIM to KDE Frameworks

Status: **decision required**  
Date: **2026-09-20**

## Context

KDE upstream now classifies KMime as a Tier 2 Framework. Frameworks 6.30.0 ships `kmime-6.30.0` and KDE is the authority for that selected source/version.

Ubuntu 26.04 Resolute still provides KMime from the PIM/Gear line as source `kmime 25.12.3-0ubuntu1`, with binary contracts `libkmime-data`, `libkmime-dev` and `libkpim6mime6`. Ubuntu applications also depend on constraints such as `libkpim6mime6 (>= 25.12.3)` and the versioned virtual package `libkpim6mime6-25.12`.

This is not only a Debian-version ordering problem.

### Upstream namespace transition

KMime 25.12.3:
- library target: `KPim6Mime`;
- CMake target: `KPim6::Mime`;
- CMake package: `KPim6Mime`;
- runtime library basename: `libKPim6Mime.so.6`.

KMime Frameworks 6.30.0:
- library target: `KF6Mime`;
- CMake target: `KF6::Mime`;
- CMake package: `KF6Mime`;
- runtime library basename: `libKF6Mime.so.6`.

The shared-library basename changed even though both use SOVERSION 6. A Frameworks KMime package therefore cannot be treated as an in-place ABI replacement for binaries already linked to `libKPim6Mime.so.6`.

### Debian version ordering

A naïve SupraLINUX version `6.30.0-0supralinux1` sorts lower than Ubuntu's `25.12.3-0ubuntu1`. An epoch could solve only the package-version ordering. It does not solve the old runtime SONAME/CMake contract.

## Constraints

Any accepted design must:
- build KDE upstream Frameworks KMime 6.30.0;
- preserve Ubuntu 26.04 application compatibility as far as technically possible;
- keep old `libKPim6Mime.so.6` consumers working unless the complete dependent closure is deliberately rebuilt;
- provide the new `KF6Mime` development/runtime contract required by current KDE;
- define package names, version ordering, Depends/Provides/Replaces/Breaks/Multi-Arch and symbols/shlibs deliberately;
- avoid claiming ABI compatibility between the two differently named libraries without evidence.

## Candidate strategies — no selection yet

1. **Co-install legacy compatibility + new Frameworks KMime.** Keep the Ubuntu/PIM runtime contract available for prebuilt applications while packaging `libKF6Mime.so.6` separately for the Frameworks stack. Development-package coexistence/transition and source ownership need explicit design.
2. **Full PIM closure rebuild onto Frameworks KMime.** Rebuild every affected SupraLINUX PIM consumer against `KF6::Mime`; this still needs a strategy for third-party/Ubuntu binaries linked to the legacy SONAME.
3. **Compatibility shim/dual-library build.** Provide the legacy SONAME from the new source only if symbol/ABI analysis proves that doing so is safe. This is not assumed and would require strong evidence.

Version epochs or synthetic Debian versions are secondary choices inside the selected compatibility strategy, not a complete solution by themselves.

## Decision

**Pending human approval.** No KMime package tree, Debian version, Provides/Replaces/Breaks set, or promotion is authorized by this ADR yet.


## Evidence update — 2026-09-22

The initial compatibility concern is now supported by current upstream and distribution evidence.

### KDE upstream tags

KDE upstream tag `v25.12.3`:
- project/PIM version line: `6.6.3`;
- library target: `KPim6Mime`;
- imported target: `KPim6::Mime`;
- CMake package directory/export: `KPim6Mime`;
- SOVERSION: `6`.

KDE upstream tag `v6.30.0`:
- Framework version line: `6.30.0`;
- library target: `KF6Mime`;
- imported target: `KF6::Mime`;
- CMake package directory/export: `KF6Mime`;
- SOVERSION: `6`;
- required Framework dependency: KCodecs 6.30.

Therefore the equal SOVERSION does **not** make the two artifacts interchangeable: the library/CMake namespaces differ by design.

Upstream release reference:
- https://kde.org/info/kde-frameworks-6.30.0/

### Ubuntu 26.04 Resolute

Resolute still ships the PIM-line source `kmime 25.12.3-0ubuntu1` and the legacy binary contracts:
- `libkpim6mime6`;
- `libkmime-dev`;
- `libkmime-data`.

References:
- https://packages.ubuntu.com/resolute/libkpim6mime6
- https://packages.ubuntu.com/resolute/libkmime-dev

This is the Ubuntu compatibility contract SupraLINUX must preserve for prebuilt Resolute applications unless their complete dependent closure is deliberately rebuilt.

### Current Debian precedent

Debian sid now carries the legacy PIM KMime and the Framework KMime as **separate source/binary families** rather than treating them as one ABI-compatible replacement.

Legacy family:
- source `kmime`;
- runtime `libkpim6mime6`;
- development `libkmime-dev`;
- headers under `/usr/include/KPim6/KMime`;
- CMake package `KPim6Mime`;
- development link `libKPim6Mime.so`.

Framework family:
- source `kf6-kmime`;
- runtime `libkf6mime6`;
- development `libkf6mime-dev`;
- data `libkf6mime-data`.

Debian's current legacy runtime also accepts `libkf6mime-data` as an alternative to the legacy `libkmime-data`, demonstrating an explicit compatibility bridge at the data-package level without claiming runtime ABI identity.

References:
- https://packages.debian.org/sid/libkmime-dev
- https://packages.debian.org/sid/amd64/libkpim6mime6
- https://packages.debian.org/unstable/source/kf6-kmime
- https://packages.debian.org/sid/libkf6mime-dev
- https://bugs.debian.org/1141990

### Consequence for the pending decision

The evidence strengthens **candidate 1 (co-install legacy compatibility + new Frameworks KMime)** as a technically demonstrated packaging pattern: old PIM consumers can retain their old SONAME/CMake contract while the SupraLINUX KDE Framework stack receives the new `KF6Mime` contract.

This section records evidence only. It does **not** authorize the candidate. Package names, source ownership, data-package relationships, version ordering and any Provides/Replaces/Breaks/Multi-Arch policy remain pending explicit human approval.

Current project state when this evidence was recorded: **Tier 2 = 14 PASS / 1 pending / 0 current FAIL / 0 BLOCKED**, with KMime as the sole pending node.
