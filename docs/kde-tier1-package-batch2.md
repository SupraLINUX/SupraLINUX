# KDE Frameworks 6.30 — Tier 1 package Batch 2

Status: **prepared; no package result claimed yet**

Batch 2 contains three independent Tier 1 nodes: **KTextTemplate**, **KArchive** and **KHolidays**. KDE upstream 6.30.0 remains the source/build authority. Ubuntu Resolute is the direct compatibility/provider target; Debian sid packaging is a technical reference only.

## Selection rationale

The three nodes depend only on the already-PASS ECM root inside KDE Frameworks and therefore can be attempted in parallel. They deliberately exercise different integration profiles without introducing a Framework-to-Framework dependency: KTextTemplate exercises Qt Core plus its upstream optional QML integration, KArchive exercises KDE's default compression backends, and KHolidays exercises required Qt QML plus Flex/Bison parser generation.

KItemModels was not selected for this batch because its build/test profile adds QML test modules and Xvfb. It remains pending and can be handled in a later independent batch.

## Upstream 6.30 requirements retained

- KTextTemplate: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 required; Qt QML is optional upstream and intentionally available in the SupraLINUX build so the established plugin/runtime contract remains present.
- KArchive: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 plus the upstream-default ZLIB, BZip2, LibLZMA, OpenSSL and LibZstd backends. No default compression backend is disabled.
- KHolidays: CMake >= 3.29, ECM 6.30, Qt Core+QML >= 6.9, Flex and Bison >= 3.3.2.

`BUILD_TESTING=ON` is explicit for all three. KHolidays retains serialized `dh_auto_test --no-parallel` from the technical packaging reference; this changes scheduling only and does not suppress tests. The Ubuntu/Debian `BUILD_QCH=ON` flag is not copied because Frameworks 6.30 uses explicit ECMGenerateQDoc targets; QDoc remains a later common policy phase.

## ABI and compatibility inputs

Binary names, Architecture and Multi-Arch contracts follow the retained Ubuntu Resolute binary-contract snapshot. Symbols use the retained **Debian 6.28** trees because they are closer to KDE 6.30 than Ubuntu 6.24. This does not make Debian an authority: a real 6.30 build must prove the ABI with `dpkg-gensymbols`; any new/missing symbol becomes real evidence to review, not something pre-filled here.

Reference source: workflow run `34708030450`, artifact `10301938362`. ECM predecessor: `extra-cmake-modules 6.30.0-0supralinux3`, artifact `10298635300`.

## State semantics

Preparation does not promote the canonical Tier 1 DAG. Until the hosted clean-package jobs actually run, KTextTemplate, KArchive and KHolidays remain `pending`. A real own-cause failure becomes FAIL; a node is BLOCKED only when an actual failed predecessor prevents its attempt. Independent jobs continue regardless of another Batch 2 result.
