# KDE Frameworks 6.30 — Tier 1 package Batch 2

Status: **first attempt completed with three real FAIL results; revision 6.30.0-0supralinux2 prepared for remediation**

Batch 2 contains three independent Tier 1 nodes: **KTextTemplate**, **KArchive** and **KHolidays**. KDE upstream 6.30.0 remains the source/build authority. Ubuntu Resolute is the direct compatibility/provider target; Debian sid packaging is a technical reference only.

## Selection and retained requirements

The three nodes depend only on the already-PASS ECM root inside KDE Frameworks and are attempted independently. KTextTemplate exercises Qt Core plus its upstream optional QML integration, KArchive exercises KDE's default compression backends, and KHolidays exercises required Qt QML plus Flex/Bison parser generation.

- KTextTemplate: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 required; Qt QML remains available so the established plugin/runtime contract remains present.
- KArchive: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 plus the upstream-default ZLIB, BZip2, LibLZMA, OpenSSL and LibZstd backends. No default compression backend is disabled.
- KHolidays: CMake >= 3.29, ECM 6.30, Qt Core+QML >= 6.9, Flex and Bison >= 3.3.2.

`BUILD_TESTING=ON` remains explicit for all three. KHolidays retains serialized `dh_auto_test --no-parallel`; this changes scheduling only and does not suppress tests. The Ubuntu/Debian `BUILD_QCH=ON` flag is not copied because Frameworks 6.30 uses explicit ECMGenerateQDoc targets; QDoc remains a later common policy phase.

## First real attempt — workflow 34720201713

Head commit: `5edf71b390088a551af81e7fc7e8d87a8378104f`. All three jobs were actually attempted, so all three results are **FAIL**, not BLOCKED. ECM remained PASS and was not the failure source.

| Node | Job | Artifact | Artifact SHA-256 | Result / exact stage |
| --- | ---: | ---: | --- | --- |
| KTextTemplate | 103624554096 | 10306265683 | `c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a` | FAIL at `sbuild` / `dpkg-gensymbols`; 10/10 upstream tests had already PASSed |
| KArchive | 103624554004 | 10305889632 | `1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01` | FAIL at `sbuild` / `dh_auto_configure`; autotests not reached |
| KHolidays | 103624554109 | 10305513311 | `522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc` | FAIL at `sbuild` / `dh_auto_configure`; autotests not reached |

### KArchive and KHolidays

Both configure failures had the same root cause: `ECMPoQmTools.cmake` calls `find_package(Qt6 ... LinguistTools)` and the clean build root lacked `Qt6LinguistToolsConfig.cmake`. On Ubuntu Resolute that CMake component is supplied by `qt6-tools-dev`. Revision `-0supralinux2` therefore adds `qt6-tools-dev (>= 6.9.0~)` to Build-Depends. This is a provider/dependency correction; it does not change KDE's authority or the selected Qt series.

No build, autotest, ABI, lintian or consumer-smoke conclusion may be inferred for those two first attempts because configure stopped before those gates.

### KTextTemplate

The real KDE 6.30 binary passed all 10 upstream tests before `dpkg-gensymbols` compared it with the retained Debian 6.28 symbols reference. The delta contains three new public `KTextTemplate::Filter` exports introduced in 6.30, eleven Qt/plugin implementation exports that are no longer emitted from `libKF6TextTemplate.so.6` after upstream moved scriptable-tag support into a plugin, and the `KTextTemplate::Exception` vtable. The public Exception header is identical in KDE 6.28 and 6.30; its virtual destructor is inline, so the library is no longer treated as obligatorily materializing that vtable.

Revision `-0supralinux2` keeps the retained Debian 6.28 file as the verified technical reference and applies a deterministic reviewed transform immediately before `dh_makeshlibs`. The transform:

- removes the eleven Qt/plugin implementation exports from the required symbols contract;
- keeps `_ZTVN13KTextTemplate9ExceptionE` as `optional=inline` at its existing 6.0.0 minimum;
- records the two Filter constructors and `Filter::context()` at upstream minimum 6.30.0;
- requires input SHA-256 `552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273` and output SHA-256 `2ff2111ce15f910328557c3295008fa21588518a0156626425df3c7b9f1b0e19`.

This is a reviewed ABI-contract update based on an actual 6.30 build, not suppression of `dpkg-gensymbols`.

## Compatibility inputs and next gate

Binary names, Architecture and Multi-Arch contracts still follow the retained Ubuntu Resolute binary-contract snapshot. The retained packaging-tree reference remains workflow run `34708030450`, artifact `10301938362`; ECM predecessor remains `extra-cmake-modules 6.30.0-0supralinux3`, artifact `10298635300`.

The Batch 2 ledger is now `remediation-pending-build`. The canonical Tier 1 manifest is intentionally not promoted by preparation/remediation metadata: no node becomes downstream-eligible until its revised package reaches the complete gate with real `.deb`, `.changes`, `.buildinfo`, tests, ABI, lintian and consumer evidence. Historical FAIL evidence remains preserved when a later PASS is recorded.
