# KDE Tier 3 — KIO Round 11 remediation definition

Status: **definition pending validation**.

This document defines the next KIO remediation but does not activate it. The executable package contract, canonical Tier 3 state, materialization queue and Level 1 execution authority remain unchanged until Repository Policy validates this definition.

## Evidence

The non-promoting Round 11 diagnostic completed successfully in workflow `36071103806`, job `107872008601`, artifact `10837734340`, SHA-256 `d4d944ac656d755ebd8c828d1e84c1b735e076c26a17adc66da42f0464a8cedc`. Its closure was validated at commit `5f057d6abcdd767f97856d83ce7d7fb0caa0bca0` by Repository Policy `36071666308` and diagnostic workflow `36071666343`.

The evidence proves that CMake `ENVIRONMENT_MODIFICATION` changes the intended QPA variables while preserving the existing `QT_PLUGIN_PATH`. It also proves that Ubuntu Resolute Qt 6.10.2 with the exact retained SupraLINUX Breeze package resolves `unknown`, `inode-directory`, and `folder-red` correctly under XCB.

## Planned package delta

KIO is the only source-package change:

- current canonical/materialized package: `6.30.0-0supralinux6`;
- next candidate after definition validation: `6.30.0-0supralinux7`;
- KDE upstream source remains exactly KIO 6.30.0;
- the change is a SupraLINUX packaging/test-fixture adaptation only.

Round 10 appended two `set_tests_properties(... ENVIRONMENT ...)` assignments. CTest treats that as replacement of the complete per-test environment, which removed KDE/ECM's `QT_PLUGIN_PATH`.

Round 11 will instead append `ENVIRONMENT_MODIFICATION` operations for only:

- `QT_QPA_PLATFORM=set:xcb`;
- `QT_QPA_SYSTEM_ICON_THEME=set:breeze`.

The affected tests remain `kiowidgets-kdirmodeltest` and `kiofilewidgets-knewfilemenutest`. Existing environment entries, including `QT_PLUGIN_PATH`, remain intact. No upstream test is removed, excluded, ignored or converted to non-fatal.

## Attempt 7 scope

Only KIO is rematerialized. KXMLGui stays canonical PASS at `6.30.0-0supralinux5` and its existing source artifact is retained.

After KIO `-7` materialization and planning validation, the complete Level 1 pair is rerun:

- KIO `6.30.0-0supralinux7`;
- retained KXMLGui `6.30.0-0supralinux5`.

KXMLGui is a revalidation node, not a source-changed node.

## krecentdocumenttest

`kiocore-krecentdocumenttest` remains unchanged and fatal. Its single Attempt 6 failure is consistent with the documented timestamp-tie hypothesis, but there is not enough focused runtime evidence to patch or suppress it. If it reproduces in Attempt 7, it becomes a separate diagnostic gate.

## Safety gate

While this definition is pending validation:

- canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**;
- KIO remains canonical FAIL at `6.30.0-0supralinux6`;
- KXMLGui remains canonical PASS at `6.30.0-0supralinux5`;
- `execution_authorized=false`;
- no KIO `-7` source artifact exists;
- no materialization remediation queue exists;
- stable promotion remains impossible without explicit user approval.

Next gate: `tier3-round11-definition-validation`.
