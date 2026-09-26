# KDE Tier 3 — KIO Round 18 test-provider remediation

Status: **definition pending source materialization**.

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

This stage authorizes **source materialization only**. Attempt 8 binary execution remains unauthorized, canonical KIO remains FAIL/downstream-ineligible, and the six dependent nodes remain BLOCKED.

Canonical state: **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

Next gate: `tier3-round18-kio-test-provider-remediation-materialization`.
