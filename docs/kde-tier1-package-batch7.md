# KDE Frameworks 6.30 Tier 1 — package Batch 7

Status: **PREPARED — package builds not yet promoted**

Canonical Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**.

## Selection

Batch 7 contains three independent nodes:

- `kcalendarcore`
- `kcoreaddons`
- `kwidgetsaddons`

All three still depend only on the retained ECM PASS inside the KDE DAG. KGuiAddons is deliberately deferred even though its source build is Tier 1: its public `KImageCache` development header consumes KCoreAddons (`kshareddatacache.h`), so its `-dev` contract must be fed by a retained local KCoreAddons PASS rather than by an Ubuntu KDE package.

## Upstream authority and Python bindings

Technical layout run `35086226149`, job `104761571679`, commit `1e97234908f3a8b201dfa6550278c3b1c380619d`, artifact `10443202060`, SHA-256 `c50a32b26e18ee84173b5a00cbd85e0c2b380660be9d939eb489c370f1317e77`, completed successfully.

It proves for KDE Frameworks 6.30.0 on Ubuntu 26.04:

- `BUILD_PYTHON_BINDINGS=ON` for KCalendarCore, KCoreAddons and KWidgetsAddons;
- `BUILD_TESTING=ON` for all three;
- `BUILD_DESIGNERPLUGIN=ON` for KWidgetsAddons;
- installed Python modules are `KCalendarCore`, `KCoreAddons` and `KWidgetsAddons`;
- KCalendarCore/KCoreAddons/KWidgetsAddons export PySide binding headers and typesystem XML for downstream binding generation.

SupraLINUX therefore does not inherit downstream `BUILD_PYTHON_BINDINGS=OFF` or `BUILD_TESTING=OFF` packaging shortcuts. The package rules make the verified KDE 6.30 defaults explicit as fail-closed assertions.

## Debian Python filesystem contract

ECM asks Python `sysconfig` for `platlib`. Debian/Ubuntu default local builds to the `posix_local` scheme, which points at `/usr/local`. Debian package builds must instead use the `deb_system` scheme.

Every Batch 7 package exports:

`DEB_PYTHON_INSTALL_LAYOUT=deb`

The Python extension is split into a dedicated `python3-*` package and must land under `/usr/lib/python3/dist-packages`. The development package retains the exported `/usr/include/PySide6/<Framework>/` header and `/usr/share/PySide6/typesystems/` XML.

## Provider evidence

The Python build provider correction remains backed by run `35087361837`, job `104765243282`, artifact `10442512801`, SHA-256 `49f74d493dd18ed68ecee668f68549cf5f71279fcb96e2f481ceef0eaccf5fa9`.

Resolute provides `python3-build 1.4.0-1`, and the preflight recorded `import build` PASS with module `1.4.0`; PySide6 and Shiboken6 remain aligned to Qt `6.10.2`.

This is provider evidence only. It does not promote a Framework node.

## Package gates

A Batch 7 PASS requires, per node:

1. exact KDE 6.30.0 source SHA verification;
2. retained ECM PASS and packaging-reference hash verification;
3. clean Resolute `sbuild`;
4. a non-zero CTest run with `100% tests passed`;
5. exact expected binary package set;
6. SONAME check;
7. source+binary Lintian error gate;
8. APT installation of the locally built package closure and `apt-get check`;
9. exact locally built package versions;
10. Python module import from the exact locally built `python3-*` package;
11. C++ consumer configure/build/run against extracted local artifacts;
12. retained `.deb`, `.ddeb`, `.changes`, `.buildinfo`, `.dsc`, source tarballs, rootfs hash and logs.

`FAIL` means a node was really attempted and failed by its own build/package/test/consumer contract. `BLOCKED` remains distinct and is not used for these three independent nodes.

## Packaging reference policy

Debian 6.28 packaging is used only as a technical reference for symbols, copyright and compatible binary split conventions. It is not an authority over KDE features. The first real Batch 7 package campaign intentionally starts from the retained 6.28 public symbol baselines; any real 6.30 ABI delta must be discovered from build evidence rather than invented in advance.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
