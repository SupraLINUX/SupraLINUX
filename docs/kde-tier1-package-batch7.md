# KDE Frameworks 6.30 Tier 1 — package Batch 7

Status: **REMEDIATION PENDING BUILD — first real package attempt retained as 3 FAIL**

Canonical promoted Tier 1 remains **18 PASS / 11 pending / 0 current promoted FAIL / 0 BLOCKED**. This does not erase the Batch 7 attempt ledger: run `35102198701` really attempted all three selected pending nodes and all three failed during `sbuild` before promotion.

## Selection

Batch 7 contains three independent nodes:

- `kcalendarcore`
- `kcoreaddons`
- `kwidgetsaddons`

KGuiAddons remains deliberately deferred. Its public `KImageCache` development header consumes KCoreAddons (`kshareddatacache.h`), so its `-dev` contract must be fed by a retained local KCoreAddons PASS rather than by an Ubuntu KDE package.

## Upstream authority and Python bindings

Technical layout run `35086226149`, job `104761571679`, artifact `10443202060`, SHA-256 `c50a32b26e18ee84173b5a00cbd85e0c2b380660be9d939eb489c370f1317e77`, passed and established the selected KDE 6.30 defaults:

- `BUILD_PYTHON_BINDINGS=ON` for KCalendarCore, KCoreAddons and KWidgetsAddons;
- `BUILD_TESTING=ON` for all three;
- `BUILD_DESIGNERPLUGIN=ON` for KWidgetsAddons;
- installed Python modules are `KCalendarCore`, `KCoreAddons` and `KWidgetsAddons`;
- the Frameworks export PySide binding headers/typesystems required by downstream bindings.

SupraLINUX does not disable these defaults to simplify packaging.

## Debian Python filesystem contract

Every Batch 7 package exports `DEB_PYTHON_INSTALL_LAYOUT=deb`. Python extensions are split into dedicated `python3-*` packages under `/usr/lib/python3/dist-packages`; development packages retain the exported `/usr/include/PySide6/<Framework>/` and `/usr/share/PySide6/typesystems/` metadata.

## Provider evidence before the package attempt

The earlier provider correction remains backed by run `35087361837`, job `104765243282`, artifact `10442512801`, SHA-256 `49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9`. It verified `python3-build 1.4.0-1`, `import build`, and PySide6/Shiboken6 aligned with Qt `6.10.2`.

That evidence was provider-availability evidence only. It did not prove that a minimal clean `sbuild` contained the Clang development/resource-dir surface used internally by Shiboken's ApiExtractor.

## First real package attempt — retained FAIL evidence

Run `35102198701` on commit `f4e1754a348f56e2a47c69cf334a12bba3d4338d` executed all three matrix nodes with `fail-fast: false`.

### KCalendarCore `6.30.0-0supralinux1`

- job `104814147716`;
- artifact `10448034196`;
- artifact SHA-256 `c76b9900d622e5ae4ab5823771baeabcbe8e2e180811ed01ac18d42b99f792e4`;
- rootfs SHA-256 `bf2f0a5c3e9ac32396439474c12dc3d8528622b626d2adcc8056e5f288bef970`;
- result: `FAIL`, stage `sbuild`.

Shiboken reported that it could not locate Clang's built-in include directory and then ApiExtractor failed because `/usr/include/c++/15/cstddef` could not resolve `stddef.h`.

### KCoreAddons `6.30.0-0supralinux1`

- job `104814147979`;
- artifact `10449051854`;
- artifact SHA-256 `d7943a390efd8610cdab14422085c6c534f0d5877ece6910f36d8a01288acba7`;
- rootfs SHA-256 `350c778059425e3a06383b52d868440396e352b57b9afcb56474287a48f534cd`;
- result: `FAIL`, stage `sbuild`.

It exposed the same Shiboken/ApiExtractor failure and missing `stddef.h` after Shiboken could not resolve Clang's built-in include directory.

### KWidgetsAddons `6.30.0-0supralinux1`

- job `104814148006`;
- artifact `10448668591`;
- artifact SHA-256 `227370b1da6151ed68155e2dfc65252db77f68e6ec03ee8f5737550709c8b995`;
- rootfs SHA-256 `5e4efab6af0773d306e543a6f9089927881d1281efb017ccd8973587692e4e3d`;
- result: `FAIL`, stage `sbuild`.

It exposed the same resource-dir warning; ApiExtractor then failed resolving `limits.h`.

These are real node FAIL attempts, not `BLOCKED`. They share one packaging/toolchain cause; there is no evidence from this attempt that KDE's C++ source, upstream feature defaults or the selected Qt provider must be changed.

## Remediation `6.30.0-0supralinux2`

The clean build had Shiboken/PySide and Clang runtime libraries, but no explicit Clang/LLVM development toolchain contract. Resolute's own `pyside6` source packaging declares `clang`, `libclang-dev` and `llvm-dev` as build dependencies for this binding-generation surface.

SupraLINUX revision `-2` therefore adds exactly these three Build-Depends to each Batch 7 node:

- `clang`;
- `libclang-dev`;
- `llvm-dev`.

This is a provider/packaging correction. It does **not** change KDE authority, source hashes, Python bindings, tests, KWidgetsAddons Designer support, or the Debian Python install layout.

The next package attempt must prove that the correction is sufficient. No PASS is claimed in advance.

## Package gates

A Batch 7 PASS still requires, per node:

1. exact KDE 6.30.0 source SHA verification;
2. retained ECM PASS and packaging-reference hash verification;
3. clean Resolute `sbuild`;
4. a non-zero CTest run with `100% tests passed`;
5. exact expected binary package set;
6. SONAME check;
7. source+binary Lintian error gate;
8. APT installation of the locally built package closure and `apt-get check`;
9. exact locally built package versions;
10. Python import from the exact locally built `python3-*` package;
11. C++ consumer configure/build/run against extracted local artifacts;
12. retained `.deb`, `.ddeb`, `.changes`, `.buildinfo`, `.dsc`, source tarballs, rootfs hash and logs.

Debian/Ubuntu packaging remains technical provider/compatibility reference only. KDE upstream 6.30.0 remains source and feature authority.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
