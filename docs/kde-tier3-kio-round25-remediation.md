# KDE Tier 3 KIO Round 25 — deterministic XBEL ordering remediation proof

Status: **definition pending CI; remediation proof authorized**.  
Candidate package execution / Attempt 9: **not authorized**.  
Canonical KIO: **6.30.0-0supralinux8 = FAIL**.

## Proven cause

Round 24 established causality, not correlation:

- native timestamps: **14/40 FAIL**;
- monotonic no-tie timestamps: **0/40 FAIL**;
- fixed all-tied timestamps: **20/20 FAIL**.

Therefore the KRecent max-entry flake is caused by ambiguous ordering when multiple XBEL entries have equal recent timestamps.

## Upstream check

KDE KIO master was checked at commit `970cbbbc5f80e56b71c9f32b1d333abac24a7770`.

The relevant master implementation still:

- builds the eviction order with `QMultiMap<QDateTime, QDomNode>`, keyed only by the modified timestamp;
- sorts `recentUrls()` only by the selected `QDateTime`.

No upstream source fix was available to cherry-pick at definition time. Round 25 therefore evaluates a minimal, upstream-compatible candidate rather than inventing a new timestamp format.

## Candidate remediation

The candidate changes only private implementation in `src/core/krecentdocument.cpp`.

### Eviction

Each bookmark is ordered by:

```text
(modified timestamp, XBEL document order)
```

Timestamp remains primary. XBEL order is used only when timestamps compare equal. Because newly-created bookmarks are appended to the XBEL document, later entries survive a tie instead of older entries being retained arbitrarily.

### recentUrls()

The private parsed entry also retains its XBEL order. Results are sorted by:

```text
(selected recent timestamp, XBEL document order)
```

This removes the second nondeterministic ordering point without changing public API, ABI, timestamp serialization or the XBEL schema.

The candidate preserves per-URL deduplication.

## Proof matrix

The candidate runs inside the exact historical Attempt 8 build path:

| Lane | Runs | Purpose |
| --- | ---: | --- |
| native | 100 | verify normal behavior no longer flakes |
| fixed | 100 | worst-case: every max-entry timestamp tied |
| monotonic | 20 | no-tie sanity control |
| full-suite | 1 | complete KIO CTest regression pass |

All isolated lanes run `kiocore-krecentdocumenttest` with a fresh HOME. The fixed and monotonic controls affect only the numeric `temp File N` URLs used by the max-entry test.

PASS requires:

- all 221 runs/captures expected by the matrix;
- zero non-zero CTest return codes;
- zero KRecent failures;
- fixed lane proves one final timestamp value;
- monotonic lane proves three distinct final timestamps;
- every captured final order is `12,13,14`;
- candidate diff and source hash retained;
- exact source and `debian/rules` restoration;
- no candidate `.deb`, `.changes` or `.buildinfo`.

## Safety

Round 25 is still non-promoting. A PASS means only that this remediation candidate is technically proven in the historical build path.

It does **not**:

- allocate `6.30.0-0supralinux9`;
- authorize Attempt 9;
- alter the canonical KIO FAIL state;
- suppress or weaken the test;
- unblock downstream Tier 3 nodes;
- publish to testing or stable.

## Current state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Round 23 = diagnostic-PASS
Round 24 = diagnostic-PASS / timestamp-tie-causality-confirmed
Round 25 = definition-pending-ci
Next gate = tier3-round25-kio-krecent-ordering-remediation-evidence
```
