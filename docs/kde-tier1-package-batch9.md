# KDE Frameworks Tier 1 — Batch 9 multi-ABI

Status: **attempt 1 complete; remediation prepared; canonical package state not promoted**

Last reviewed: **2026-09-18**

## Scope and authority

Batch 9 covers the independent Tier 1 nodes `kconfig`, `ki18n` and `sonnet`. KDE upstream stable 6.30.0 is authoritative. Ubuntu 26.04 Resolute is the provider platform. Debian 6.28 and Ubuntu packaging captures are technical references only and cannot select versions, disable KDE defaults or promote package state.

Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until real package evidence is promoted separately.

Attempt 1 used `6.30.0-0supralinux1` for all three packages. KI18n retains that PASS revision; KConfig and Sonnet move to `6.30.0-0supralinux2` for reviewed ABI-symbol remediation. All consume the retained ECM PASS `6.30.0-0supralinux3`.

## Retained non-promoting discovery evidence

Source diagnostic run `35138333645` proved source SHA/provider/configure/build/upstream-test/install-staging/defaults behavior, but is **DIAG_PASS** only and does not promote packaging state:

- KConfig: job `104936243505`, artifact `10464074545`, SHA-256 `9f05b0e368c4d1a7eb3dbec441680b423fd3f8b4a7fc2a0cdcbf9edbb3ca6e68`;
- KI18n: job `104936243967`, artifact `10463404553`, SHA-256 `86b5f05313d164358ac36e1cc4982b72fad90bad3175114d2b2b493691a6bec3`;
- Sonnet: job `104936243844`, artifact `10464073832`, SHA-256 `6b17c7f02213282a520f4127feb010e9a37dbbafce9c8ab17d7f76164b22d7b6`.

Retained technical reference artifacts:

- packaging trees: run `34708030450`, artifact `10301938362`, ZIP SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`, snapshot SHA-256 `f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345`;
- binary contracts: run `34704117024`, artifact `10301282501`, ZIP SHA-256 `9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97`, `binary-contracts.json` SHA-256 `e44507d0dd73db913a91bd4852c452f783618aab0bd6a3790e4c4f4c40707b7b`.

## ABI surfaces

KConfig has nine binary packages and three runtime ABI surfaces: ConfigCore (`648` reference exports), ConfigGui (`170`) and ConfigQml (`22`).

KI18n has eight binary packages and three runtime ABI surfaces: I18n (`122`), I18nLocaleData (`58`) and I18nQml (`33`).

Sonnet has eight binary packages and two runtime ABI surfaces: SonnetCore (`263`) and SonnetUi (`179`).

The Debian 6.28 symbol files remain solely in the retained, hash-pinned packaging-tree artifact. The clean runner validates their SHA-256/export counts and materializes them as active `.symbols` only inside the ephemeral source package during the build. A new 6.30 symbol carrying the current `0supralinux` Debian revision is a hard failure until its actual upstream introduction version is reviewed; no ABI minimum is guessed in advance.

## Upstream defaults and downstream patches

`BUILD_TESTING=ON` is mandatory for all three packages. QCH stays OFF under the common SupraLINUX Frameworks profile; this is a documented SupraLINUX packaging profile and does not allow other KDE defaults to be reduced.

KConfig retains only Debian's technical `KCONFIG_COMPILER_INSTALL_DIR` patch to preserve the Debian-compatible `lib/libexec/kf6` layout. The two Debian `QSKIP` patches that suppress flaky tests are deliberately excluded.

KI18n carries no downstream patch and keeps the upstream-compatible locale fixture (`LANG=en_US.UTF-8`, no `LC_ALL`, no parallel test execution). The Ubuntu behavior that disables `dh_auto_test` is explicitly rejected.

Sonnet carries no downstream patch. Debian's `cross.patch` is excluded because it changes upstream cross-compilation behavior and is not needed for the native SupraLINUX package attempt. Widgets, QML/Quick, Designer plugin and spelling backends remain enabled; the provider installs all available backend development packages and the runner requires at least one packaged backend plugin.

## DIAG_PASS installed-surface audit

The retained DIAG_PASS artifacts were re-materialized and their ZIP SHA-256 values rechecked before package implementation: KConfig `9f05b0e368c4d1a7eb3dbec441680b423fd3f8b4a7fc2a0cdcbf9edbb3ca6e68`, KI18n `86b5f05313d164358ac36e1cc4982b72fad90bad3175114d2b2b493691a6bec3`, Sonnet `6b17c7f02213282a520f4127feb010e9a37dbbafce9c8ab17d7f76164b22d7b6`.

The KDE 6.30 `installed-files.txt` surfaces were compared against the retained Debian-family `.install` splits. KI18n and Sonnet are fully covered by the selected package manifests. KConfig is also covered except for `kconfig_compiler_kf6` in the unmodified diagnostic staging path `/usr/lib/<multiarch>/libexec/kf6`; the retained technical KConfig patch deliberately relocates that host build tool to Debian-compatible `/usr/lib/libexec/kf6`, matching `libkf6config-dev-bin.install`. This is the only deliberate installed-path delta from the source diagnostic and does not suppress or replace a KDE feature.

## Multi-ABI runner gates

The Batch 9 matrix is `kconfig`, `ki18n`, `sonnet`, with `fail-fast: false` and `max-parallel: 3`.

Each node independently validates source and retained-input hashes, a fresh Resolute `sbuild`, a non-zero upstream CTest PASS summary, exact binary package count/splits/Multi-Arch, `.ddeb` metadata, every runtime SONAME, every generated binary symbols control file, QML module declarations/import scanning, Lintian source+binary error gate, installation of the exact locally built package set with `apt-get check`, and a C++ consumer configure/build/run smoke.

A real attempted node may become PASS or FAIL. BLOCKED is reserved for a predecessor FAIL; these three nodes depend only on the retained ECM PASS, so one peer failing does not block either of the other two. Independent PASS results are retained while only real FAIL nodes are remediated.

Promotion remains a separate commit after retained real PASS evidence exists.


## Attempt 1 — real package results

PR CI run `35348130023` on commit `958d9990f0c5c6e85ade45faf8b7fa1a62c0c3af` produced three independent real package attempts:

- KConfig `6.30.0-0supralinux1`: **FAIL**, job `105609530611`, artifact `10549115856`, ZIP SHA-256 `6579cc838436e1390c950da9037997ae4646fb4fb40d5e69290377c16f385b6c`, rootfs `79fe82c1adfffb5050106b07157c423ed7c9c7c0a4a2608ace84899d5ae1184e`. Upstream tests were `90/90 PASS`; the package build itself completed, then Lintian rejected `_ZN16KStandardActions16staticMetaObjectE@Base` because `dpkg-gensymbols` assigned the current Debian revision. KDE Frameworks 6.29.0 introduced `StandardAction` as `Q_ENUM_NS`, so the reviewed public ABI minimum is `6.29.0`.
- KI18n `6.30.0-0supralinux1`: **PASS**, job `105609530707`, artifact `10548710619`, ZIP SHA-256 `d213147477242b08a1dac78611b30eacb60f9bd727abb1313d5a2c8bc7c24cf4`, rootfs `f3849a2ceb003aeb1de899fe3b56dec59b3b29da6589f79da9b7dc3685c52b4d`. Tests `17/17 PASS`; ABI exports remain exactly `122/58/33`; Lintian, QML imports, exact APT closure and consumer smoke pass. It is retained PASS and downstream-eligible.
- Sonnet `6.30.0-0supralinux1`: **FAIL**, job `105609530666`, artifact `10549100349`, ZIP SHA-256 `d01d279dc2645efd9ecc01506e17c0f99aecadda761bc12236af7ae1341a3fc6`, rootfs `300d410c9e584cd0bc8dee75578db2ac940363e20440a289c2a31142b64d7d09`. Upstream tests were `8/8 PASS`; the package build itself completed, then Lintian rejected `_ZN6Sonnet8Settings22defaultSkipRunTogetherEv@Base` at the current Debian revision. KDE Frameworks 6.30.0 fixes the historic function-name typo and adds `Settings::defaultSkipRunTogether()`, so the reviewed public ABI minimum is `6.30.0`.

The missing `optional=templinst` exports reported for Sonnet are optional toolchain/template-instantiation baseline entries and are not the cause of the package failure. Neither KConfig nor Sonnet is BLOCKED; each was attempted and failed for its own symbols-contract cause. KI18n PASS remains retained independently.

## Attempt 1 remediation

KConfig and Sonnet move to `6.30.0-0supralinux2`. Each uses the established SupraLINUX deterministic symbols-delta pattern immediately before `dh_makeshlibs`: verify the retained Debian 6.28 baseline SHA-256, insert exactly one reviewed public symbol at an exact anchor, verify the complete transformed symbols-file SHA-256, then invoke `dh_makeshlibs` normally. KConfig's transformed ConfigGui symbols SHA-256 is `8a8220263cd60e88208e68138cb0f7288a4d99d3a99c0349e62be314d9d1fd04`; SonnetCore's is `e75af49fd74700ef8a2c21ce55decaf96439479223770c63654410f3c3f956bb`.

Repository Policy run `35348129610`, job `105609486001`, independently exposed ShellCheck `SC2100` on the diagnostic `STAGE` string labels `qml-package-contract` and `qml-import-smoke`. This is infrastructure-only and has no package-state effect. The remediation quotes those two string assignments only and leaves every build/test/ABI/runtime gate unchanged. Because the shared runner changes, Batch 9's semantic selector correctly revalidates all three nodes on the next campaign run.
