# KDE Frameworks Tier 1 — Batch 11 multi-surface/optional

Status: **prepared; package builds pending**

Canonical Tier 1 remains **27 PASS / 2 pending / 0 current FAIL / 0 BLOCKED**. Batch 11 contains the final two pending Tier 1 nodes: KUserFeedback and Prison. Implementing this lane changes readiness, not canonical package state.

## Authority and provider

KDE Frameworks 6.30.0 remains desktop authority. Ubuntu 26.04 Resolute supplies general providers when they satisfy KDE's selected feature profile. Debian/Ubuntu packaging remains a technical reference for Debian-family splits, symbols and integration details only.

The retained reference input is workflow run `34708030450`, artifact `10301938362`. Before Batch 11 consumes retained copyright or symbols metadata, the runner verifies the pinned `tree-hashes.tsv`, verifies the selected node's `tree-files.sha256` hash, and then verifies every retained file listed by that node manifest.

## KUserFeedback

The package profile preserves upstream behavior:

- `ENABLE_SURVEY_TARGET_EXPRESSIONS=ON`;
- `ENABLE_PHP=ON`;
- `ENABLE_PHP_UNIT=ON`;
- `ENABLE_DOCS=ON`;
- `ENABLE_CONSOLE=OFF` — the KDE upstream default;
- `BUILD_TESTING=ON`.

Widgets and QML are built because the selected Resolute providers are available. Provider mapping includes Flex, Bison, PHP/PHPUnit, Qt Base, Qt Charts, Qt Declarative and Qt Tools.

The package lane validates the Core and Widgets runtime ABIs, the `org.kde.userfeedback` QML root, exact local-package APT closure and an external CMake consumer using `KF6::UserFeedbackCore` and `KF6::UserFeedbackWidgets`.

## Prison

The package profile explicitly preserves all default-enabled upstream surfaces:

- `WITH_DMTX=ON`;
- `WITH_ZXING=ON`;
- `WITH_QUICK=ON`;
- `WITH_MULTIMEDIA=ON`;
- `BUILD_TESTING=ON`.

Resolute provider mapping includes `libdmtx-dev`, `libqrencode-dev`, `libzxing-dev`, `qt6-declarative-dev` and `qt6-multimedia-dev`.

The package lane validates both `libKF6Prison.so.6` and `libKF6PrisonScanner.so.6`, both QML roots `org.kde.prison` and `org.kde.prison.scanner`, exact local-package APT closure and an external CMake consumer using `KF6::Prison` and `KF6::PrisonScanner`.

## CI semantics

KUserFeedback and Prison have no KDE Framework build predecessor beyond retained ECM and no package-validation dependency on each other. They therefore run as independent matrix nodes with `fail-fast: false` and `max-parallel: 2`.

A real attempted package failure is FAIL only for that node. The peer remains independently runnable. BLOCKED is reserved for an actual failed predecessor and is therefore not expected between these two Batch 11 nodes.

The shared development-contract audit runs before source packaging and again against built artifacts. Batch 11 also hardens that audit to recognize KDE export files named either `*Target.cmake` or `*Targets.cmake`; KUserFeedback 6.30 uses the singular `KF6UserFeedbackTarget.cmake`.

## Promotion boundary

Preparation does not promote either Framework. Real package attempts are preserved in `manifests/kde-tier1-package-batch11-attempts.json`. If both nodes later retain full package PASS evidence, canonical Tier 1 promotion remains a separate evidence/state change.

## Preparation infrastructure incident

Repository Policy run `35485140225`, job `106010004365`, failed at ShellCheck before package-policy validators ran. Bash syntax had already passed. ShellCheck SC2100 treated two unquoted hyphenated `STAGE` labels as arithmetic-like assignments.

Classification: **INFRA**, `package_attempted=false`, `package_state_effect=none`. The remediation quotes all literal stage labels in the Batch 11 runner. No package version, feature profile, dependency contract or canonical state changes.

## Cycle 1 results and remediation

Run `35485199667` exercised both nodes independently.

- **Prison** job `106010235300`: the source package built successfully, Lintian passed and upstream CTest reported **9/9 PASS**. The runner then failed because campaign metadata incorrectly expected 8 tests. This is **INFRA/validation**, not a package FAIL. Artifact `10596344285`, SHA-256 `67803dee1fc950cd960bfd836de516e3e397b7132f02338df00703c4f611c779`.
- **KUserFeedback** job `106010235329`: real FAIL during `sbuild` tests. Resolute provides PHPUnit 13.0.0; KDE 6.30's PHP tests still use legacy `@dataProvider` metadata and a fixture whose database variables depend on global include scope. The remediation keeps `ENABLE_PHP_UNIT=ON`, ports the test metadata to PHPUnit 13 attributes, puts fixture variables in `$GLOBALS`, and adds `php-sqlite3` for the upstream SQLite PDO fixture. Artifact `10596274248`, SHA-256 `a8db3c3c85e0645f64b62ba4ee0fe0d6c9b50a85a446680b0da1b0bb9fc44b6d`.

The corrected exact CTest counts are KUserFeedback **15** and Prison **9**. Canonical Tier 1 remains **27 PASS / 2 pending / 0 current FAIL / 0 BLOCKED** until a complete retained PASS exists.

## Cycle 2

Run `35488901554` validates the first remediation.

- Prison `6.30.0-0supralinux1`: **PASS** in job `106020266290`; artifact `10597829797`, SHA-256 `f0074c8da29cfda08018fa568fce9cabbf6fc23669416caf20c714c25ff7773f`. Gates: 9/9 CTest, Lintian, both ABI surfaces, both QML roots, exact APT closure, development contract and consumer smoke.
- KUserFeedback `6.30.0-0supralinux2`: real FAIL in job `106020266302`; **14/15 CTest PASS**. DataProvider metadata, scoped globals and SQLite provider are fixed. The only remaining failure is SampleTest's use of removed PHPUnit 13 `TestCase::getActualOutput()`. Revision `-3` replaces those four reads with scoped `ob_start()/ob_get_clean()` capture while preserving the same JSON assertions.

Prison is technically downstream-eligible, but canonical Tier 1 remains unchanged until Batch 11 promotion is performed separately.

## Cycle 3

Run `35489184465`, job `106021045629`, artifact `10598602563`, SHA-256 `e70ed24da8adcd0cedf6b28f9281bbc7d8e5f891337ec953d767a1de68b37a9a`.

KUserFeedback `6.30.0-0supralinux3` again reaches **14/15 CTest PASS**. The output-capture remediation works. The only remaining failing CTest is SampleTest because PHPUnit 13 removed `assertObjectHasAttribute()` and `assertObjectNotHasAttribute()`. Revision `-4` maps them to PHPUnit 13's `assertObjectHasProperty()` and `assertObjectNotHasProperty()`. All other PHP/C++ tests pass.

Prison remains retained PASS and was correctly scope-skipped in this cycle.

## Cycle 4

Run `35489499984`, job `106021890875`, artifact `10598313568`, SHA-256 `15458a33a3b4091bab61523097c23d7caeb46b188ba78188a92afec9f582dec5`.

KUserFeedback `6.30.0-0supralinux4` reaches **15/15 CTest PASS**: the PHPUnit 13 compatibility work is complete. Packaging then fails at `dh_missing` because `ENABLE_DOCS=ON` emits `usr/share/KDE/UserFeedbackConsole/user-feedback-manual.qch` and the initial doc split did not install it.

Revision `-5` assigns that upstream manual to `libkf6userfeedback-doc`. This does not re-enable Framework API QCH: `BUILD_QCH=OFF` remains unchanged.

## Canonical closure

Batch 11 is now **2/2 PASS retained and promoted**.

- KUserFeedback `6.30.0-0supralinux5`: run `35489771315`, job `106022610412`, artifact `10597923863`, ZIP SHA-256 `0a057d591a198f74cf6eee24d3b1ef4355f2a0d6073d48de8e220ac37f0a38b7`, rootfs `8b5518bea1704ffb9830b4d9a3259e2655ca69efb6dff108b9a9709e66d87e39`; 15/15 tests plus Lintian, ABI, APT, QML, development-contract and consumer gates PASS.
- Prison `6.30.0-0supralinux1`: run `35488901554`, job `106020266290`, artifact `10597829797`, ZIP SHA-256 `f0074c8da29cfda08018fa568fce9cabbf6fc23669416caf20c714c25ff7773f`, rootfs `a1ae6cb653ec18a6dba7142f4ee5acd94210076a9adba23d9d67d03ac03885e7`; 9/9 tests plus Lintian, ABI, APT, QML, development-contract and consumer gates PASS.

Both nodes retain only the ECM Framework build edge. The `multi-surface-optional` lane is completed and leaves global discovery. Canonical KDE Frameworks Tier 1 is now **29 PASS / 0 pending / 0 current FAIL / 0 BLOCKED**. Historical real FAILs and INFRA incidents remain in the Batch 11 ledger.

This canonical promotion does not publish packages to the APT `stable` channel.
