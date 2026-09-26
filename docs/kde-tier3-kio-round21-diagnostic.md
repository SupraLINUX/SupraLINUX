# KDE Tier 3 KIO Round 21 — KRecent visible-CWD timestamp diagnostic

Status: definition pending diagnostic evidence.

Round 21 is a **non-promoting KRecent-only diagnostic**. KDirModel is not rerun because Round 20 established its hidden-HOME cause. No Debian package is built, no KIO revision is allocated, no test is suppressed, and Attempt 9 remains unauthorized.

## Corrected environment

Each selected test gets a visible CWD outside `/tmp`, a fresh visible HOME, `TMPDIR=/tmp`, and the XDG data/config/cache overrides unset. Diagnostic-only instrumentation prevents QTest cleanup from deleting the XBEL after the test. The runner then discovers exactly one `recently-used.xbel` below HOME instead of assuming its path.

## Sequence

1. 30 baseline runs.
2. A capture-all variant with `MaxEntries=50` and the ordering assertion removed only for timestamp inspection.
3. Capture all 15 bookmark names and `modified` timestamps.
4. Restore upstream source, add only `QTest::qWait(5)` after each add plus XBEL preservation, and run 30 delayed repetitions.
5. Restore upstream source byte-for-byte.

Timestamp-collision ordering is confirmed only with a valid environment, at least one exact Attempt 8 baseline signature (`temp File 11` vs `temp File 12`), duplicate capture-all timestamps, and zero delayed failures.

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
```
