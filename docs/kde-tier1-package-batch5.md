# KDE Frameworks 6.30 Tier 1 — package Batch 5

Status: **open remediation; 2 package PASS, 1 remediation pending**  
Last reviewed: **2026-09-15**

## Selection

Batch 5 contains three independent Tier 1 nodes whose only KDE DAG predecessor is the retained ECM PASS and whose ABI surface fits the current single-primary-library runner:

- KIdleTime;
- ModemManagerQt;
- NetworkManagerQt.

Canonical promotion is deliberately deferred until the batch closes. The package-attempt ledger now contains two real PASS nodes and one real FAIL with a prepared remediation, while canonical Tier 1 remains **13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED**.

## First attempt — run 35014875475

The three nodes were all genuinely attempted from commit `30b5dcd293527b488c88cf0a861883ee869e3ea0`; none was scope-skipped.

### KIdleTime PASS

- job `104535671033`;
- package `6.30.0-0supralinux1`;
- artifact `10414598079`;
- artifact SHA-256 `272ccad537d21905cf75a1add74e937d176c20c05c38bf967226fef4ab28b605`;
- tests: `1/1 PASS`;
- Lintian: PASS;
- SONAME: `libKF6IdleTime.so.6`;
- consumer smoke: PASS;
- retained ECM predecessor: `6.30.0-0supralinux3`.

This is real hosted-clean-package-preflight PASS evidence. The node is package-ledger downstream-eligible, but remains canonical `pending` until Batch 5 closure updates Tier1/DAG.

### NetworkManagerQt PASS

- job `104535671250`;
- package `6.30.0-0supralinux1`;
- artifact `10414714325`;
- artifact SHA-256 `abf927b5749b34094d2b5ee530831f64638ba116a83e8b82f925a758aa018ad4`;
- tests: `38/38 PASS` after excluding only the three documented live-NetworkManager tests;
- Lintian: PASS;
- SONAME: `libKF6NetworkManagerQt.so.6`;
- consumer smoke: PASS;
- QML package contract retained.

This is real hosted-clean-package-preflight PASS evidence. Canonical promotion is still deferred to closure.

### ModemManagerQt FAIL

- job `104535671188`;
- attempted package `6.30.0-0supralinux1`;
- failure artifact `10415586492`;
- artifact SHA-256 `f79f98cc73f561e5750c4db7917917a043f260131af0ac19180fd835dee78af7`;
- build: successful;
- tests: `11/11 PASS`;
- failure stage: `sbuild` internal Lintian gate;
- fatal finding: `symbols-file-contains-current-version-with-debian-revision` for `_ZSt19piecewise_construct@Base`.

This is a real node `FAIL`, not `BLOCKED`. The corrected `modemmanager-dev` provider was sufficient to configure, compile and execute all tests; the failure is unrelated ABI/toolchain symbols metadata.

## ModemManagerQt remediation

Revision `6.30.0-0supralinux2` keeps KDE source and dependencies unchanged. Before `dh_makeshlibs`, a deterministic script verifies the exact retained Debian 6.28 symbols baseline and inserts exactly:

`(optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0`

This follows the already validated BluezQt remediation pattern.

Hashes:

- baseline symbols SHA-256 `70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2`;
- transformed symbols SHA-256 `b717475396376ac884bb3587ab2a0e898af5beb940836c45ee834758eec6820f`;
- transform script SHA-256 `f468a9e752ecb79ccc05e3a7e344622f7b1e6aeae94fb71089a94f0f51d5559b`.

The historical `-1` FAIL remains retained. `-2` is remediation-pending-build until a new real attempt passes.

## Provider inputs

KDE upstream 6.30.0 remains authority. Ubuntu Resolute only supplies providers.

The ModemManager mapping was revalidated before opening this batch. KDE requests `ModemManager >= 1.0` through pkg-config module `ModemManager`; Ubuntu Resolute supplies that interface with `modemmanager-dev`.

Targeted provider evidence:

- workflow run `35012023822`;
- job `104526071758`;
- commit `48fd01bfa7b254b5e5c8447b3d609f76a91f786f`;
- artifact `10414525047`;
- artifact SHA-256 `db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a`;
- result: PASS;
- authority claim: none; provider-availability evidence only.

## Package profiles

### KIdleTime

Retains KDE's Linux X11 and Wayland defaults. QCH is disabled by the common SupraLINUX Frameworks profile; autotests run under Xvfb rather than being disabled.

Primary ABI: `libKF6IdleTime.so.6`.

### ModemManagerQt

Uses `modemmanager-dev` as the Ubuntu provider for KDE's `ModemManager >= 1.0` requirement. Tests run under a private D-Bus session. QCH alone is disabled.

Primary ABI: `libKF6ModemManagerQt.so.6`.

### NetworkManagerQt

Keeps the upstream QML module enabled and preserves the established `qml6-module-org-kde-networkmanager` binary package contract. `libnm` and GIO are explicit direct build inputs because KDE's CMake calls both pkg-config modules directly.

Only `managertest`, `settingstest` and `activeconnectiontest` are excluded in the isolated package lane because they require a live NetworkManager service. All other upstream tests remain enabled. The `-1` attempt confirmed 38/38 executed tests PASS.

Primary ABI: `libKF6NetworkManagerQt.so.6`.

## Gates

Every node must independently complete source/hash verification, retained predecessor/reference verification, clean Ubuntu 26.04 `sbuild`, tests, exact binary contracts, SONAME check, source/binary Lintian, downstream consumer smoke and retained artifact upload.

A failed node is `FAIL` only if it was actually attempted and failed by its own cause. Independent nodes continue. `BLOCKED` is not used for the ModemManagerQt failure because it was genuinely attempted.

PR #1 remains Draft. No merge is authorized.
