# KDE Tier 3 KIO Round 23 — historical build-path diagnostic

Status: **diagnostic PASS — exact Attempt 8 KRecent signature reproduced in isolation**.  
Infrastructure preflight: **PASS**.  
Candidate package execution / Attempt 9: **not authorized**.

Round 23 used the exact Attempt 8 rootfs, KIO 6.30.0-0supralinux8 source materialization, retained predecessor artifacts, sbuild 0.91.2ubuntu3/unshare and the historical Debian build path:

```text
sbuild
→ dpkg-buildpackage --sanitize-env -us -uc -b
→ debian/rules binary
→ override_dh_auto_test
```

No candidate package artifacts were produced. The temporary KRecent instrumentation and `debian/rules` change were restored byte-for-byte before the diagnostic abort.

## Closed evidence

- workflow run: `36288655361`
- job: `108534328079`
- branch commit: `f31c5620697dfaecb69b870287a180574b3bc92d`
- artifact: `10921272952`
- artifact SHA-256: `1638ac8ea01881a78e4ec32761eb473836258653d3c08f1f116af6ac93829e69`
- result: `DIAG_COMPLETE`
- environment valid: **true**
- historical build path invoked: **true**
- source restored: **true**
- rules restored: **true**
- package attempted: **false**

## Result

| Lane | Runs | KRecent failures | Exact Attempt 8 signature | Valid XBEL captures |
| --- | ---: | ---: | ---: | ---: |
| isolated KRecent | 100 | 58 | **51** | 100 |
| CTest prefix 1–26 | 30 | 14 | **13** | 30 |
| full suite | 3 | 3 | **1** | 3 |

The exact historical failure — `Actual temp File 11 / Expected temp File 12` — therefore reproduces without any preceding CTest targets: **51 / 100 isolated runs**.

Seven additional isolated failures returned `temp File 10` instead of `temp File 12`. This is broader ordering instability, not a dependency on a previous test.

## Interpretation

Round 23 closes the main uncertainty left by Rounds 19–22:

- hidden HOME alone was insufficient;
- CTest sequencing outside the retained build rootfs was insufficient;
- inside the exact historical build path, the failure is reproducible even when KRecentDocumentTest is isolated.

Captured XBEL files show millisecond-level timestamp ties around the surviving recent entries. That materially strengthens the timestamp-tie hypothesis, but **does not yet prove it is the sole cause**: both passing and failing captures can contain tied timestamps.

Therefore no production patch or test suppression is justified yet. The next diagnostic must prove or reject timestamp-tie causality, preferably by observing the per-add timestamp/eviction sequence and a controlled no-tie lane while preserving the historical build path.

## Canonical state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Infrastructure preflight = PASS
Round 23 = diagnostic-PASS
Next gate = tier3-round24-kio-krecent-timestamp-tie-causality-diagnostic-definition
```

Round 23 changes diagnostic knowledge only. It does not promote KIO, unblock dependents, allocate a package revision, or alter testing/stable publication state.
