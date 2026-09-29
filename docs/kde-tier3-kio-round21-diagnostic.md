# KDE Tier 3 KIO Round 21 — KRecent visible-CWD timestamp diagnostic

Status: **diagnostic PASS; Attempt 8 failure not reproduced**.

Round 21 remained non-promoting. No Debian package was built, no KIO revision was allocated, no test was suppressed, and Attempt 9 was not authorized.

## Closed evidence

- workflow run: `36248969228`
- job: `108423337171`
- commit: `9c18c9e811d31f8ec296d22180fdda7ed70545d9`
- artifact: `10908497619`
- artifact SHA-256: `31f4fddc17bf13b2058773c9c506a54f625ebe100d884418ef27fe45fd9ec4e0`

## Result

The corrected environment was valid:

- baseline: 30 runs, 0 failures;
- exact Attempt 8 `temp File 11` vs `temp File 12` signature: 0/30;
- delayed `QTest::qWait(5)`: 30 runs, 0 failures;
- capture-all: 15 XBEL entries;
- duplicate `modified` timestamp groups: 0.

Therefore the simple timestamp-collision hypothesis was **not reproduced in the Round 21 direct-test environment**. This is not evidence that the Attempt 8 failure was spurious: Attempt 8 ran the complete KRecentDocumentTest through CTest inside the package test environment, while Round 21 invoked only one test function in a new process.

## Handoff

Round 22 compares the two remaining environmental dimensions directly:

1. selected test function vs complete CTest test binary;
2. visible HOME vs the hidden packaging HOME used by Attempt 8.

The CTest hidden-HOME lane reproduces the exact outer environment from Attempt 8 as closely as possible without building a Debian package.

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
```
