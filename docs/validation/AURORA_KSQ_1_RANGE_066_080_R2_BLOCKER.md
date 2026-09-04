# Aurora KSQ-1 — range 066–080 r2 blocker

Status: **BLOCKED / ROOT-CAUSE INVESTIGATION ACTIVE**

This record captures the proven state after the first maintained native attempt to build orders 66–80. It does not accept any part of the range as a checkpoint.

## Causal run

- workflow: `.github/workflows/ksq-native-range-066-080-r2.yml`
- run: `33821750759`
- artifact: `9919609367`
- artifact digest: `sha256:e04615715fcee3450c14db3f1a7085d09cd937c7db8d2520c0bff49f60546998`
- prior accepted checkpoint: order 65 / 295 accumulated DEBs
- run result: **FAIL**

The runner, exact 001–065 checkpoint chain, independent order-65/KWallet acceptance artifact, canonical r2 slice and clean native buildd recreation all passed before source building began.

## Build result

The run produced successful source builds for orders 66–73:

- 66 `kf6-kxmlgui`
- 67 `kf6-kio`
- 68 `drkonqi`
- 69 `kf6-baloo`
- 70 `kf6-kcmutils`
- 71 `kf6-knotifyconfig`
- 72 `kf6-kparts`
- 73 `kglobalacceld`

These eight successful builds are **partial evidence inside a failed range**, not an accepted checkpoint. DrKonqi order 68 is not reproducibility certification.

The first causal failure is:

- order: `74`
- source: `xdg-desktop-portal-kde`
- packaging base: `6.7.4-0ubuntu1`
- `sbuild` exit: `3`
- completed prior order: `73`
- new DEBs before failure: `27`
- accumulated DEBs before failure: `322`

## Proven failure mechanism

`xdg-desktop-portal-kde` Build-Depends contains `libcups2-dev`.

During the real `sbuild 0.91.2ubuntu3` APT dependency installation, APT selected the following Resolute packages among the transitive build dependency closure:

- `libjpeg-turbo8-dev=2.1.5-4ubuntu4`
- `libjpeg8-dev=8c-2ubuntu12`
- `libjpeg-dev=8c-2ubuntu12`

The canonical r2 repository metadata advertises all of them, but its materialized pool contains `libjpeg-turbo8-dev` and does not contain the two selected `libjpeg8-empty` development payloads:

- `pool/main/libj/libjpeg8-empty/libjpeg8-dev_8c-2ubuntu12_amd64.deb`
- `pool/main/libj/libjpeg8-empty/libjpeg-dev_8c-2ubuntu12_amd64.deb`

The real build therefore fails while fetching from the local-only r2 archive with `File not found`; there is no external network fallback.

The historical r2 closure-generation evidence (`9883249125`) contains 1783 selected binary objects and includes only `pool/main/libj/libjpeg8-empty/libjpeg8_8c-2ubuntu12_amd64.deb` from `libjpeg8-empty`. Its `binary-print-uris.txt` includes `libjpeg-turbo8-dev` but not `libjpeg8-dev` or `libjpeg-dev`.

Thus the demonstrated defect is **not an unsatisfied KDE Build-Depends relation**. It is a mismatch between the full signed APT metadata exposed by r2 and the subset of payload objects chosen by the r2 closure-generation transaction.

## Investigation boundary

No package is being added manually and `xdg-desktop-portal-kde` is not being patched.

The active root-cause probe compares the exact pinned Ubuntu snapshot `20260829T022000Z` under APT 3.2.0 in three resolver contexts:

1. the original r2 direct multi-root transaction containing the 244 certified Ubuntu binary seeds;
2. direct installation of `libcups2-dev=2.4.16-1ubuntu1.3`;
3. installation of an sbuild-style local dummy package whose `Depends` contains that exact `libcups2-dev` relation.

This follows sbuild's documented APT-resolver architecture: sbuild creates a transient dummy package containing source Build-Depends as package `Depends` and installs that dummy through APT.

A corrected slice must be derived from the demonstrated resolver semantics and must close the complete build requirement. It must not be created by appending only the two currently observed missing payloads.

## Gate state

- accepted KSQ-1 checkpoint remains: **order 65 / 295 DEBs**;
- orders 66–80: **NOT ACCEPTED**;
- r2: remains immutable historical/canonical input for the accepted-through-65 evidence, but is now proven insufficient as a general payload closure for continuing the 101-source build;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.

Any replacement build slice is a new immutable identity and triggers the required downstream regression before earlier PASS evidence may be carried forward.