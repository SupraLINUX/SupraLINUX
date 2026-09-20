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
