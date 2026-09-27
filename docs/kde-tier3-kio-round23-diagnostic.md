# KDE Tier 3 KIO Round 23 — historical build-path diagnostic

Status: **definition pending CI; diagnostic execution authorized**.  
Infrastructure preflight: **PASS**.  
Candidate package execution: **not authorized**.

Round 23 investigates the nondeterministic `KRecentDocumentTest::testXbelBookmarkMaxEntries()` failure observed in Level 1 Attempt 8. It does not change package state and it is not Attempt 9.

## Why the method changed

Seven earlier Round 23 executions were `INFRA_INVALID`. None is usable as a KIO conclusion. The seventh proved the native sbuild transport but still manually reconstructed selected `debian/rules` configure/build steps, so it did not preserve the historical failure path closely enough.

The infrastructure methodology was then frozen and a package-independent preflight was introduced under the two-invalid-attempt cutoff rule.

## Infrastructure gate — PASS

Closed preflight evidence:

- workflow run: `36286096599`
- job: `108527097646`
- commit: `340da99451a86b65513efcbfcae6b6b7145a2a96`
- artifact: `10920194622`
- artifact SHA-256: `ee6adecf77aa5110db735220bca0ebecd2a4a41b4a2b8dacc6692816866c1d39`
- exact Attempt 8 rootfs tar SHA-256: `790139881455b78e00621f1b8ab02efaee899b7e6873f4d65ae0ff7fa295020e`

That PASS certifies the sbuild/unshare hook transport and evidence round-trip. It does **not** prove anything about the KIO failure itself.

## Historical parity contract

The redesigned Round 23 must use:

```text
exact Attempt 8 rootfs
+ exact KIO 6.30.0-0supralinux8 materialization
+ exact retained predecessor artifacts
+ sbuild 0.91.2ubuntu3 / unshare
+ --enable-network
+ dpkg-buildpackage --sanitize-env -us -uc -b
+ debian/rules binary
```

The `starting-build-commands` hook is now limited to preparing instrumentation in the disposable unpacked worktree. It may not run `debian/rules clean`, `override_dh_auto_configure` or `override_dh_auto_build` itself.

The real `dpkg-buildpackage` path performs clean/configure/build. Only `override_dh_auto_test` is temporarily redirected to the diagnostic matrix. Before the intentional test-stage abort, the modified KRecent source and `debian/rules` are restored byte-for-byte.

No `.deb`, `.changes` or `.buildinfo` may be produced. If they appear, the diagnostic is invalid.

## Matrix

The test-stage diagnostic runs under the same package directory, HOME, XCB, Breeze, KDECI, D-Bus and Xvfb contract used by Attempt 8:

- `kiocore-krecentdocumenttest` isolated: 100 runs;
- CTest prefix 1–26: 30 runs;
- complete CTest suite: 3 runs.

Instrumentation is placed immediately after `KRecentDocument::recentUrls()` and before the failing comparison. It records the already-computed URL order and the XBEL state for each run.

A valid diagnostic requires all expected runs and captures. The conclusion distinguishes reproduction while isolated, after the CTest prefix, only in the full suite, or no reproduction.

## Canonical state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Infrastructure preflight = PASS
Round 23 = diagnostic pending CI
Next gate = tier3-round23-krecent-attempt8-full-build-path-diagnostic-evidence
```

A Round 23 result can guide diagnosis only. It cannot promote KIO, authorize Attempt 9, or alter stable/testing publication state by itself.
