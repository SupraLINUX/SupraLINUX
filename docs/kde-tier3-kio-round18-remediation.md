# KDE Tier 3 — KIO Round 18 test-provider remediation

Status: **Attempt 8 closed MIXED; focused follow-up diagnostic required**.

Round 17 established the causal environmental root cause: removing `qt6-svg-plugins` from otherwise identical KIO test binaries restores both historical empty-`QIcon::name()` failures, and reinstalling it restores PASS.

Round 18 audited ownership on Ubuntu 26.04. Workflow `36221977278`, job `108348814091`, artifact `10899531699` (SHA-256 `8dfc4f94ed892a49bd4dd3fd262b7755cb078adfa56716a7c0e7e679f6cb9c6c`) confirmed that `libqt6gui6` recommends the plugin, while `qt6-svg-dev`, KIconThemes and Breeze do not hard-own that runtime relation.

## Remediation decision

The explicit dependency belongs to the **KIO build/test closure**, not to a KIO runtime binary:

`Build-Depends: qt6-svg-plugins <!nocheck>`

Classification: `upstream-test-environment-provider`.

This matches the existing SupraLINUX KIconThemes precedent and preserves Ubuntu's runtime package contract. No new runtime relation is added to KIO, KIconThemes or Breeze.

## Materialization scope

Only KIO is rematerialized:

- canonical failed package: `6.30.0-0supralinux7`;
- source candidate: `6.30.0-0supralinux8`;
- retained KXMLGui: `6.30.0-0supralinux5` PASS;
- materialization queue: `[kio]`.

The existing complete test environment is retained: D-Bus session, writable HOME, KDECI marker, Xvfb/XCB, Breeze, node-scoped network, serial CTest and non-destructive `ENVIRONMENT_MODIFICATION`. All 69 upstream tests remain enabled and fatal.

Source materialization completed successfully in workflow `36222711238`, job `108350884409`, artifact `10898999142` (SHA-256 `c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d`). The materialized source is `6.30.0-0supralinux8`; this is source evidence only, not a package PASS. Attempt 8 binary execution remains unauthorized, canonical KIO remains FAIL/downstream-ineligible at `6.30.0-0supralinux7`, and the six dependent nodes remain BLOCKED.

Canonical state: **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

Planning validation passed in Repository Policy `36237942524` and Level 1 workflow `36237942600` for commit `349b0d543edefb2979f1712079628e25e37d8135`.

Attempt 8 is now authorized for the full Level 1 scope: KIO `6.30.0-0supralinux8` plus retained KXMLGui `6.30.0-0supralinux5`. Canonical KIO remains FAIL/downstream-ineligible until the real package job passes.

Next gate: `tier3-build-level1-attempt8`.


## Attempt 8 result

Workflow `36238357510` on `77129c31006ac746d0d5d1d249ed7d1aaf6cf530` completed with one PASS and one FAIL.

- KXMLGui `6.30.0-0supralinux5`: PASS, 7/7 upstream tests, Python import PASS.
- KIO `6.30.0-0supralinux8`: FAIL, 67/69 upstream tests.
- `kiofilewidgets-knewfilemenutest`: PASS after adding `qt6-svg-plugins <!nocheck>`.
- `KDirModelTest::testIcon()`: PASS; the previous empty icon-name failure is resolved.
- `kiocore-krecentdocumenttest`: fails only `testXbelBookmarkMaxEntries()` because ordering returns `temp File 11` where `temp File 12` is expected.
- `kiowidgets-kdirmodeltest`: fails `testShowRoot()` and `testShowRootAndExpandToUrl()` because `indexForUrl(homeUrl)` is invalid.

The SVG provider remediation is therefore proven effective for the icon-provider failure class, but KIO still has two independent upstream-test failures. No tests are suppressed.

Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

Next gate: `tier3-round19-kio-diagnostic-definition`.
