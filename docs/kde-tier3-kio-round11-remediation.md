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

## Definition validation — PASS / materialization active

The Round 11 definition passed Repository Policy `36072487004` at commit `0dad8b3e82eb07bb02e90da4036001a82e885b0f`.

That approval authorizes the next source-only gate:

- rematerialize **KIO only** as candidate `6.30.0-0supralinux7`;
- retain KXMLGui `6.30.0-0supralinux5` unchanged for later full Level 1 revalidation;
- replace the destructive per-test CTest `ENVIRONMENT` assignment with `ENVIRONMENT_MODIFICATION`;
- preserve `QT_PLUGIN_PATH` and every pre-existing per-test environment entry;
- keep all 69 KIO upstream tests fatal, including `krecentdocumenttest`.

This activation does not authorize a binary package build. Canonical package state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED** and KIO remains canonical FAIL at `6.30.0-0supralinux6` until a later binary Attempt 7 succeeds. The active gate is now `tier3-round11-kio-materialization`.

## Round 11 KIO materialization — PASS

KIO candidate `6.30.0-0supralinux7` was materialized successfully in workflow `36073638711`, job `107879979760`, from commit `ebe60a0147e2a47b6c256ac015f43eea350c3ba2`.

Evidence artifact `10839162922` has SHA-256 `ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c`. Internal source evidence includes `dsc_sha256=fbba71c0d66cb4e0e09a9f6e2625dd416d642c075a7b8f9ae8bfcd51eee413ec`, `debian_tar_sha256=bccd518fc0be0e9f09bf06e9b346ad21d24143191eef73585cf4347a6fa41118`, `source_tree_sha256=8db83e361fa632ecb36fb171ae78ec021cc6f9e1d0b67fc0476f045e3afce923`, `materialized_tree_sha256=9138398b41e18849de47ac93a0f5f4a68b449607a3b8b02fd16607cf99b2e18d`, and `adapted_rules_sha256=c966d9328a0ab624ac5c7b5fb4d1b328d4812ac477446e0b0adf05671c410bfd`.

This remains **source materialization only**: no KIO binary package was built and canonical KIO remains FAIL at `6.30.0-0supralinux6` until a later Level 1 Attempt 7 succeeds. KXMLGui remains canonical PASS at `6.30.0-0supralinux5`.

The generated Tier 3 build campaign now references the KIO `-7` materialization artifact while `execution_authorized=false`. The next gate is `tier3-build-level1-planning-validation`.
