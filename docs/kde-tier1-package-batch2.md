# KDE Frameworks 6.30 — Tier 1 package Batch 2

Status: **KTextTemplate PASS; KHolidays PASS; KArchive FAIL only at consumer-smoke after successful package build/tests/Lintian**

Last reviewed: **2026-09-14**

Batch 2 contains three independent Tier 1 nodes: **KTextTemplate**, **KArchive** and **KHolidays**. KDE upstream 6.30.0 remains the source/build authority. Ubuntu Resolute is the direct compatibility/provider target; Debian sid packaging is a technical reference only.

## Selection and retained requirements

The three nodes depend only on the already-PASS ECM root inside KDE Frameworks and are attempted independently. KTextTemplate exercises Qt Core plus its upstream optional QML integration, KArchive exercises KDE's default compression backends, and KHolidays exercises required Qt QML plus Flex/Bison parser generation.

- KTextTemplate: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 required; Qt QML remains available so the established plugin/runtime contract remains present.
- KArchive: CMake >= 3.29, ECM 6.30, Qt Core >= 6.9 plus the upstream-default ZLIB, BZip2, LibLZMA, OpenSSL and LibZstd backends. No default compression backend is disabled.
- KHolidays: CMake >= 3.29, ECM 6.30, Qt Core+QML >= 6.9, Flex and Bison >= 3.3.2.

`BUILD_TESTING=ON` remains explicit for all three. KHolidays retains serialized `dh_auto_test --no-parallel`; this changes scheduling only and does not suppress tests. The Ubuntu/Debian `BUILD_QCH=ON` flag is not copied because Frameworks 6.30 uses explicit ECMGenerateQDoc targets; QDoc remains a later common policy phase.

## Attempt 1 — workflow 34720201713

Head commit: `5edf71b390088a551af81e7fc7e8d87a8378104f`. All three jobs were actually attempted, so all three results are **FAIL**, not BLOCKED. ECM remained PASS and was not the failure source.

| Node | Job | Artifact | Artifact SHA-256 | Result / exact stage |
| --- | ---: | ---: | --- | --- |
| KTextTemplate | 103624554096 | 10306265683 | `c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a` | FAIL at `sbuild` / `dpkg-gensymbols`; 10/10 upstream tests had already PASSed |
| KArchive | 103624554004 | 10305889632 | `1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01` | FAIL at `sbuild` / `dh_auto_configure`; autotests not reached |
| KHolidays | 103624554109 | 10305513311 | `522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc` | FAIL at `sbuild` / `dh_auto_configure`; autotests not reached |

KArchive and KHolidays both lacked the provider of `Qt6::LinguistTools` required by ECM `ECMPoQmTools`; Ubuntu Resolute supplies that component in `qt6-tools-dev`. Revision `-0supralinux2` added `qt6-tools-dev (>= 6.9.0~)` without changing KDE's authority or the selected Qt series.

KTextTemplate's real KDE 6.30 binary exposed a reviewed ABI delta: three public `Filter` exports were added; eleven Qt/plugin implementation exports stopped being emitted from the main library after upstream moved scriptable-tag support into a plugin; the inline Exception vtable is not obligatorily materialized. Revision `-0supralinux2` retained the Debian 6.28 baseline and applied a deterministic transform from SHA-256 `552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273` to `2ff2111ce15f910328557c3295008fa21588518a0156626425df3c7b9f1b0e19` immediately before `dh_makeshlibs`.

## Attempt 2 — workflow 34776389758

Head commit: `5b7e539b2512a1486ffa1816017932dca76a73ac`. All three jobs were actually attempted again.

| Node | Job | Artifact | Artifact SHA-256 | Result / exact stage |
| --- | ---: | ---: | --- | --- |
| KTextTemplate | 103775171198 | 10323646687 | `c9343f846f172770081700c74e6bb42e9d99090ec1e66b3c978de49c243b1462` | **PASS** complete; 10/10 tests, Lintian error gate, SONAME and consumer smoke PASS |
| KArchive | 103775171200 | 10323946438 | `9778cf376281794f3e2ac84977b1eef0747f575d70d148c5453dc0da96b65dbe` | **FAIL** at `sbuild` / `dh_missing` after 5/5 tests PASS |
| KHolidays | 103775171063 | 10323921696 | `57f842e542abe69dcbdcbcd2961cee2ec774201e5d4a9babeee5274029838a5c` | **FAIL** at `lintian` after 8/8 tests and binary build PASS |

### KArchive remediation for revision -0supralinux3

Upstream correctly installs `usr/lib/x86_64-linux-gnu/pkgconfig/KF6Archive.pc`. The SupraLINUX `libkf6archive-dev.install` manifest omitted it, so `dh_missing` rejected a valid development artifact left in `debian/tmp`. Revision `-0supralinux3` assigns `usr/lib/*/pkgconfig/KF6Archive.pc` to `libkf6archive-dev`. This is a package-file manifest correction only; KDE source, compression backends, tests and ABI baseline are unchanged.

### KHolidays remediation for revision -0supralinux3

The second build completed and passed all 8 upstream tests. `dpkg-gensymbols` discovered **36 real public exports** from the Hebrew-calendar support added upstream in KDE Frameworks 6.30 and initially assigned them minimum version `6.30.0-0supralinux2`. Lintian correctly rejected the Debian revision embedded in the symbols contract.

The 36 exports belong to `KHolidays::HebrewDate` and `KHolidays::HebrewConverter`; upstream KDE introduced the corresponding public implementation/header support in the 6.30 development cycle. They are therefore recorded at upstream minimum **6.30.0**, not hidden and not marked as toolchain implementation symbols.

Revision `-0supralinux3` keeps the exact Debian 6.28 baseline SHA-256 `b0be25ddbc4c7abeb121bb0d3c3ca053d33e2a9fa88695bea210c50d56c256cd` and applies a deterministic hash-pinned transform before `dh_makeshlibs`. The reviewed result SHA-256 is `fac03d2f96ccec7b6cbcfd30d59cee86496d3a0f6b5ad02d3392496b61e7c135`; the transform file SHA-256 is `6b0a250fc6c847ee8bedadf83b922a81921aa9bc7a8cc32382c969210b3b3c69`.

## Attempt 3 — workflow 34834818877

Head commit: `1634e56fcbb7dd4cc7a931f98a846b485c84077e`. KArchive and KHolidays were really rebuilt; KTextTemplate was intentionally skipped because its consumed build inputs did not change.

| Node | Job | Artifact | Artifact SHA-256 | Result / exact stage |
| --- | ---: | ---: | --- | --- |
| KArchive | 103946132310 | 10342979027 | `216d291414f884ea49cfc3661575973ec09081bc92080e76d0a12e0e476eb562` | **FAIL** at `consumer-smoke`; sbuild successful, 5/5 tests PASS, Lintian error gate PASS, SONAME `libKF6Archive.so.6` PASS |
| KHolidays | 103946132514 | 10343623713 | `bb6ce23797d69f46f430fa53fef9e439b94772ce4566a3684f3a7038cada854d` | **PASS** complete; 8/8 tests, Lintian error gate, SONAME and consumer smoke PASS |

### KArchive consumer-smoke diagnosis

The third KArchive package itself is valid through all package gates. `libkf6archive-dev_6.30.0-0supralinux3_amd64.deb` contains both the generated CamelCase forwarding headers (`KArchive`, `KZip`, `K7Zip`, etc.) and the lowercase implementation headers under `/usr/include/KF6/KArchive/`. Upstream's exported `KF6::Archive` target advertises that directory itself as its include directory.

The SupraLINUX smoke test incorrectly used `#include <KArchive/KZip>`, which asks the compiler for `/usr/include/KF6/KArchive/KArchive/KZip`. That path is not the KDE install contract. The correct consumer include is `#include <KZip>`, resolved through `KF6::Archive`'s exported include directory. The remediation therefore changes only the SupraLINUX consumer probe; package revision `6.30.0-0supralinux3`, KDE source, symbols baseline and package contents remain unchanged.

KArchive remains **FAIL** and is not downstream-eligible until a real rerun passes the corrected consumer smoke. The successful package build alone is not promoted to PASS.

### KHolidays PASS evidence

The retained KHolidays PASS artifact proves:

- revision `6.30.0-0supralinux3`;
- 8/8 upstream tests PASS;
- Lintian error gate PASS;
- SONAME `libKF6Holidays.so.6`;
- consumer smoke PASS;
- `.buildinfo` exact ECM predecessor `6.30.0-0supralinux3`;
- runtime `.deb` SHA-256 `1ce83590add63defda14cb81d9540f8a10b29cf428e730b837b3c2b1866a441e`;
- development `.deb` `25257b454cef04bd6d7aa875b0c5ff79774387d6c438b8d098118b414da7a191`;
- data `.deb` `7a611425648cace15dbc5a99c39462a2531cfe04253a0143175f8e2b18e5cf29`;
- doc `.deb` `44935c0c97f8de3c3d21c7c5184a0fa3297aee648a39ec0f1b283dbabb767bbf`;
- QML `.deb` `f9981a3258ebcb312911a60aadd769f5b6ae02ce3be8fdaaf057aa868fe3119d`;
- `.changes` `a76446a2412fcc05ac3b527d4873e79b8df202b27e01a76d5d5ebb75cd0cd24c`;
- `.buildinfo` `0d2f37f59ce201342cd9d5a62db70bd04a0beaa0343af83b01d6c706a8787575`;
- `.dsc` `735efa970be24cab57020befe9e30ffe4b6c2ee6a14bfe365207cd6aa70ffe30`;
- Debian tar `58c1a5f2334b180a8dd22fb79a567ba3ba6e3a524e683e90239c5c4cdc8a8077`;
- upstream tar `02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b`;
- rootfs `482fab954ea0630eba1362053725d3ac9b11ad791a1f7bdab95a8baae20e43ef`.

## KTextTemplate current-head revalidation

Commit `3944b0fe78d51ac9ac77566948c0419e2bfa7b0a` pinned the exact transform bytes and triggered a real KTextTemplate rebuild in workflow `34776524481`.

- job `103315694490`;
- artifact `10323233062`;
- artifact SHA-256 `c0825408584e8d2e37a66ba95764e3e33adeafeaa5adcb30c253fb706c6c9f27`;
- revision `6.30.0-0supralinux2`;
- tests **10/10 PASS**;
- Lintian error gate PASS;
- SONAME `libKF6TextTemplate.so.6`;
- consumer smoke PASS;
- `.buildinfo` proves ECM `6.30.0-0supralinux3`;
- downstream eligibility: **yes** in the Batch 2 attempt ledger.

The current artifact includes runtime `.deb` SHA-256 `1b45b1191176062de32faaf96ce85f20329aa717e1f1ad71453ce91ac6ffbebc`, development `.deb` `0905718c7d1a3d227b3e29a4b945a8751f87a9bb19e0d0e5fff498393373b631`, doc `.deb` `b8cf9fa1983fbae53e612293c9106dcb79ca0bb64d58db71b7e4bf53a2de3811`, `.buildinfo` `84ef4928cc5032cf423ae8d4bec6817bb97ae4bf563177909d79895272b61af3`, `.dsc` `50b9e77a72799e0fa841b74af91285955de60c186ec71ca0845bd000f1597260` and rootfs `9f1d5cc7e07f0856829f6e37f86b59e1a63eb1dbeb41196426956766da44c949`.

## Current gate state

The retained packaging-tree reference remains workflow run `34708030450`, artifact `10301938362`; ECM predecessor remains `extra-cmake-modules 6.30.0-0supralinux3`, artifact `10298635300`.

Batch 2 is now **2 PASS / 1 remediation-pending-build** in the observed CI evidence: KTextTemplate and KHolidays have real complete PASS artifacts; KArchive remains FAIL solely because the consumer probe used the wrong include form. The Batch 2 attempt ledger and canonical Tier 1/DAG manifests are reconciled in the closure commit after KArchive passes the corrected probe. Until then KArchive must not feed downstream nodes. Historical FAIL evidence remains preserved.
