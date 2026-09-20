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
