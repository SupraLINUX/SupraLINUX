# KDE Tier 3 KIO Round 24 — timestamp-tie causality diagnostic

Status: **diagnostic-PASS; closed historical evidence**.  
Candidate package execution / Attempt 9: **not authorized**.  
Canonical KIO: **6.30.0-0supralinux8 = FAIL**.

## Why Round 24 exists

Round 23 reproduced the historical KRecent failure inside the exact Attempt 8 build path even when `kiocore-krecentdocumenttest` ran in isolation:

- isolated runs: 100;
- failures: 58;
- exact Attempt 8 signature: 51.

The exact KIO 6.30.0 source provides a concrete causal candidate:

1. `addToXbel()` generates its bookmark timestamp from `currentDateTimeUtc()` at millisecond effective resolution;
2. `removeOldestEntries()` stores bookmarks in `QMultiMap<QDateTime, QDomNode>`, keyed only by the modified time;
3. `recentUrls()` sorts only by the selected `QDateTime`.

Round 23 showed timestamp ties in both passing and failing final captures, so correlation alone is insufficient.

## Method

Round 24 reuses the already-certified Round 23 transport and exact historical build path. It introduces **no new diagnostic infrastructure mechanism**:

```text
exact Attempt 8 rootfs
+ exact KIO 6.30.0-0supralinux8 materialization
+ retained predecessor artifacts
+ sbuild 0.91.2ubuntu3 / unshare
+ dpkg-buildpackage --sanitize-env -us -uc -b
+ debian/rules binary
+ override_dh_auto_test
```

The disposable diagnostic worktree receives a runtime-selectable timestamp control. The perturbation applies only to the numeric `temp File N` URLs created by `testXbelBookmarkMaxEntries`; the other KRecent tests retain the native timestamp path. The canonical source artifact is not changed and all modified source/rules files must be restored byte-for-byte before exit.

## Causal matrix

| Lane | Runs | Timestamp behavior |
| --- | ---: | --- |
| native | 40 | original KIO 6.30 timestamp path |
| monotonic | 40 | deterministic +1 ms per add; no ties |
| fixed | 20 | identical timestamp for every add; all tied |

Every lane runs only `kiocore-krecentdocumenttest` with a fresh HOME.

Validity requires:

- all 100 expected runs and captures;
- monotonic final XBEL captures have 3 distinct timestamps;
- fixed final XBEL captures have exactly 1 timestamp;
- exact historical build path reached;
- test source, KRecent implementation and `debian/rules` restored;
- no `.deb`, `.changes` or `.buildinfo` candidate artifacts.

## Decision rules

`timestamp-tie-causality-confirmed` requires all three:

1. native reproduces at least once;
2. monotonic produces zero failures;
3. fixed produces at least one failure.

If monotonic still fails, timestamp ties are not sufficient as the sole cause. If native fails but both monotonic and fixed pass, the result is inconclusive. If native does not reproduce in this run, the experiment is valid but inconclusive.

Round 24 is diagnostic only. No result from this run can itself patch KIO, suppress the test, allocate a package revision, authorize Attempt 9, unblock dependents or promote packages.

## Result

Workflow `36295265079`, job `108552864340`, artifact `10922979916` completed with valid historical-path evidence.

| Lane | Result | Timestamp proof | Observed final order |
| --- | --- | --- | --- |
| native | **14/40 FAIL** | 31 captures had 2 distinct timestamps; 9 had 3 | 14× `11,13,14`; 26× `12,13,14` |
| monotonic | **0/40 FAIL** | 40/40 had 3 distinct timestamps | 40× `12,13,14` |
| fixed | **20/20 FAIL** | 20/20 had exactly 1 timestamp | 20× `0,1,2` |

Conclusion: `timestamp-tie-causality-confirmed`.

Removing timestamp ties eliminated the failure in every monotonic run, while forcing all max-entry timestamps equal reproduced the failure in every fixed run. The native control reproduced the historical class in 14/40 runs. This is causal evidence for the timestamp-tie ordering defect, not merely correlation.

The experiment remained non-promoting: the diagnostic source and `debian/rules` were restored, no candidate package artifacts were accepted, KIO remains FAIL, and Attempt 9 remains unauthorized.

## Current state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Infrastructure preflight = PASS
Round 23 = diagnostic-PASS
Round 24 = diagnostic-PASS / timestamp-tie-causality-confirmed
Next gate = tier3-round25-kio-krecent-ordering-remediation-definition
```
