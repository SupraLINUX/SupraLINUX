# KDE Frameworks Tier 1 — Batch 9 multi-ABI

Status: **package campaign complete: 3/3 PASS retained; canonical promotion pending as a separate commit**

Last reviewed: **2026-09-18**

## Scope and authority

Batch 9 covers the independent Tier 1 nodes `kconfig`, `ki18n` and `sonnet`. KDE upstream stable 6.30.0 is authoritative. Ubuntu 26.04 Resolute is the provider platform. Debian 6.28 and Ubuntu packaging captures are technical references only and cannot select versions, disable KDE defaults or promote package state.

Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until real package evidence is promoted separately.

Attempt 1 used `6.30.0-0supralinux1` for all three packages. KI18n retains that PASS revision. KConfig and Sonnet used `6.30.0-0supralinux2` in attempt 2 to validate the reviewed ABI-symbol deltas, and now move to `6.30.0-0supralinux3` solely to declare the `python3:any` build prerequisite required by those deterministic delta scripts. All consume the retained ECM PASS `6.30.0-0supralinux3`.

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


## Attempt 2 — real package results

PR CI run `35354088696` on commit `f23d5b995468d16189ef18e9b59b63ac3927736f` revalidated the lane after the reviewed ABI deltas and Repository Policy ShellCheck fix:

- KConfig `6.30.0-0supralinux2`: **FAIL**, job `105629086800`, artifact `10551565818`, ZIP SHA-256 `44095dd2f16b7101c0f1dbe65fb561d79361b28a8b5f255151760e64a4ea09a3`, rootfs `a3ef32e90b7f8c734110becf63a327503855e3c5d495fb340668f944cb24b30c`. Tests remained `90/90 PASS`; the reviewed ConfigGui symbols delta executed before `dh_makeshlibs` and eliminated the attempt-1 symbol-version error. Lintian then rejected `debian/rules` because it invokes `python3` without declaring `python3:any` (or equivalent) as a build prerequisite.
- KI18n `6.30.0-0supralinux1`: **PASS**, job `105629086722`, artifact `10550338682`, ZIP SHA-256 `08271a40a392b0d947b05413c54c913230261d26bff1ed12d91d37a85400a3bd`, rootfs `2e45730952a04dc7b8ed5fe96c6e479427697a5d6fc0c840cc8817fe81c24974`. This revalidates the retained KI18n PASS under the corrected shared runner.
- Sonnet `6.30.0-0supralinux2`: **FAIL**, job `105629086871`, artifact `10551700066`, ZIP SHA-256 `3d995b55c0e106554957bd7cfc2a1f63df19fc3c7b95a59be9fa0df51a9f6c23`, rootfs `bca53d5e3e2f5e536987ad3d8885ba44d814db9a2bd80b7ed07b006bc394b5f7`. Tests remained `8/8 PASS`; the reviewed SonnetCore symbols delta executed successfully and eliminated the attempt-1 symbol-version error. Lintian then reported the same missing direct `python3` build prerequisite.

Attempt 2 therefore proves that both reviewed ABI deltas are correct. The remaining KConfig/Sonnet failure is packaging metadata, not ABI, source, test, QML, runtime or predecessor failure.

## Attempt 3 remediation

KConfig and Sonnet move to `6.30.0-0supralinux3` and add exactly `python3:any` to `Build-Depends`, because `debian/rules` invokes `python3 debian/apply-symbols-delta.py` during the package build. No KDE feature/default, ABI minimum, downstream patch or symbols transformation changes from attempt 2.

The semantic selector treats package-tree changes per node. Therefore attempt 3 must rebuild KConfig and Sonnet only. KI18n package inputs and per-node campaign build fingerprint are unchanged, so its retained attempt-2 PASS must scope-skip rather than rebuild.


## Validation cycle 3 — runner false negative, no package-state effect

PR CI run `35355395436` on commit `97e4feb51df541501b027ba80c4b86907d8763c8` rebuilt KConfig/Sonnet at `6.30.0-0supralinux3`; KI18n correctly scope-skipped because its package inputs were unchanged. Repository Policy run `35355394975` passed.

Both rebuilt packages completed source build, upstream tests and Lintian successfully, then the shared runner rejected them at its numeric ABI export-count gate:

- KConfig: job `105633436677`, artifact `10551433966`, ZIP SHA-256 `eed45f10d52f3190fcf099ceb63c4138f1c346d191d6aa85429b1beafd829b95`, rootfs `cd684394244cb651b6d36171bf140e8dfae4905d92b5f4da2d87d89b66754629`, tests `90/90 PASS`, Lintian PASS. ConfigCore generated 640 exports while the retained Debian baseline has 648 total. That total includes six `optional=templinst` entries plus eight non-optional exports restricted to `arch=armhf` or `arch=riscv64`; only **634** baseline exports are required on amd64. Therefore `640 < 648` is a runner false negative.
- Sonnet: job `105633436582`, artifact `10551832586`, ZIP SHA-256 `f9352e5f5c3cd527cc32887896b1c6c4441e1291ee103204de470e3378a77218`, rootfs `9e79ae0631e0c4b7a59f3fb82af976eaaf9c388c01b57edfebd30001f37d38af`, tests `8/8 PASS`, Lintian PASS. SonnetCore generated 255 exports while the retained baseline has 263 total, nine of which are `optional=templinst`; only **254** are required on amd64. Therefore `255 < 263` is also a runner false negative.

These events are recorded as validation infrastructure incidents with `package_state_effect=none`, not as package FAIL. They do not certify PASS because QML/APT/consumer gates were not reached after the false-negative abort.

### Retained ABI baseline partition for amd64

| Surface | Baseline total | Optional | Non-optional but inapplicable on amd64 | Required on amd64 |
| --- | ---: | ---: | ---: | ---: |
| ConfigCore | 648 | 6 | 8 | 634 |
| ConfigGui | 170 | 2 | 0 | 168 |
| ConfigQml | 22 | 0 | 0 | 22 |
| I18n | 122 | 1 | 0 | 121 |
| I18nLocaleData | 58 | 2 | 0 | 56 |
| I18nQml | 33 | 0 | 0 | 33 |
| SonnetCore | 263 | 9 | 0 | 254 |
| SonnetUi | 179 | 5 | 0 | 174 |

The runner now recomputes this partition directly from every retained hash-pinned Debian symbols file. It requires the computed total/optional/non-applicable/required counts to equal campaign metadata and uses only `reference_required_export_count_amd64` as the post-build numeric floor. `dpkg-gensymbols` remains the authoritative per-symbol missing-symbol check; the numeric gate remains an additional consistency guard.

Because the shared runner changes, the next validation cycle revalidates KConfig, KI18n and Sonnet. Package revisions do not change: KConfig/Sonnet remain `6.30.0-0supralinux3`, KI18n remains `6.30.0-0supralinux1`.


## Validation cycle 4 — architecture-aware ABI gate

Repository Policy run `35358919925` passed the hardened Batch 9 policy. PR CI run `35358920602` on commit `1048fd52df303957d2db82c29988c8170b6fd656` revalidated all three nodes with the corrected architecture-aware ABI floor.

- KI18n `6.30.0-0supralinux1`: **PASS**, job `105645094825`, artifact `10553916882`, ZIP SHA-256 `2a0d66f2760c49ba1128b8b51c741173a72e6f3ab51f3eb17c3584896d30a678`, rootfs `c3a542cadce65b491d0997f7fa61cfabc2b44188a2021c151858349766fd148d`, tests `17/17 PASS`. Generated ABI exports are `122/58/33` against required amd64 floors `121/56/33`; Lintian, exact APT closure, QML import and consumer smoke pass.
- Sonnet `6.30.0-0supralinux3`: **PASS**, job `105645094787`, artifact `10554216487`, ZIP SHA-256 `ae5a33cf8699b96b7b7b8c1a83bc4d37a484878029818c1885b4f4f44f15b431`, rootfs `38f9fcd9dd6cb379bd5ba1fbfb5c93f57b49db71c166615415ff663366fc54bb`, tests `8/8 PASS`. Generated ABI exports are `255/179` against required amd64 floors `254/174`; Lintian, exact APT closure, QML import, consumer smoke and packaged backend-plugin gate pass.
- KConfig `6.30.0-0supralinux3`: **FAIL**, job `105645094816`, artifact `10553307816`, ZIP SHA-256 `7bc04355d35d9bd86033ffaceb89a2addbb79e9e5d49ef14f59be58f2cfde312`, rootfs `3c863b17d63bf75492b41bcb774d6d40616ffe646ded3d0c50fb51562c17df57`. The package passed `90/90` tests, Lintian, ABI (`640/171/22` against required `634/168/22`), exact APT installation/check and QML import scanning. It then failed the C++ consumer configure because the installed `KF6ConfigConfig.cmake` executes `find_dependency(Qt6Qml "6.9.0")`, while `libkf6config-dev` did not depend on the development package that supplies that exported Qt CMake contract.

### KConfig consumer-development closure

The KConfig failure is a real package-contract failure, not infrastructure. KDE's exported CMake metadata determines that a consumer of the selected KConfig GUI/QML surface needs Qt6Qml >= 6.9.0. Ubuntu 26.04 Resolute is only the provider and currently supplies `qt6-declarative-dev 6.10.2+dfsg-3`.

KConfig therefore moves to `6.30.0-0supralinux4` with `qt6-declarative-dev (>= 6.9.0~)` added to the binary `libkf6config-dev` Depends. The package already had the same provider in Build-Depends; the correction closes the exported downstream development contract. No KDE feature/default, ABI delta or source patch changes.

Because only the KConfig package tree and its per-node campaign build fingerprint change, the next Batch 9 run must rebuild KConfig and scope-skip KI18n/Sonnet while retaining their cycle-4 PASS evidence.


## Validation cycle 5 — KConfig final PASS

Repository Policy run `35360530531`, job `105650391908`, passed before the final package result. PR CI run `35360530830` on commit `bfb02cdc6f6086ed41092cc900563dfa3be86e64` rebuilt only KConfig; KI18n job `105650448606` and Sonnet job `105650448640` intentionally scope-skipped and retained their cycle-4 PASS evidence.

KConfig `6.30.0-0supralinux4` is **PASS**:

- job `105650448776`;
- artifact `10554715051`;
- artifact ZIP SHA-256 `bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e`;
- rootfs SHA-256 `cf14256f216dd3ec9a67a7bca3bd46e8624391ffe40b2c08567dc1fe90a4b9e3`;
- tests `90/90 PASS`;
- Lintian source+binary error gate PASS;
- exact local-package APT install/check PASS;
- QML import smoke PASS;
- consumer CMake/build/runtime smoke PASS;
- generated ABI exports: ConfigCore `640 >= 634`, ConfigGui `171 >= 168`, ConfigQml `22 = 22`.

The `qt6-declarative-dev (>= 6.9.0~)` binary development dependency therefore closes the exported `Qt6Qml >= 6.9.0` contract without reducing any KDE upstream feature/default.

Batch 9 package state is now **3/3 retained PASS**: KConfig `6.30.0-0supralinux4`, KI18n `6.30.0-0supralinux1`, Sonnet `6.30.0-0supralinux3`. Historical FAIL attempts and cycle-3 infrastructure incidents remain preserved. Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until the separate promotion commit.


## Repository Policy closure-validator incident

Repository Policy run `35365460369`, job `105666708183`, reached the Batch 9 validator after every earlier policy validator had passed. It failed only because the documentation-token check searched lowercase `validation cycle 4` and `validation cycle 5` case-sensitively while the actual section headings begin with uppercase `Validation`.

Classification: **infrastructure-validator-documentation-case-sensitivity**, `package_state_effect=none`. No package build, PASS evidence or canonical state changes. The validator now compares documentation tokens case-insensitively.
