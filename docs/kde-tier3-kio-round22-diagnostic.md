# KDE Tier 3 KIO Round 22 — KRecent CTest/HOME matrix

Status: definition pending diagnostic evidence.

Round 22 is non-promoting. It does not build a Debian package, allocate a KIO revision, suppress a test, alter the DAG, or authorize Attempt 9.

## Why this round exists

Round 21 established a valid direct-test environment, but the Attempt 8 failure did not reproduce in 30 baseline runs. Round 21 differed from Attempt 8 in two important ways:

- Round 21 invoked only `testXbelBookmarkMaxEntries` in a fresh process.
- Attempt 8 ran the complete `KRecentDocumentTest` through CTest with the packaging HOME `debian/.supralinux-test-home/sbuild`.

Attempt 8 also used `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `LOGNAME=sbuild`, `USER=sbuild`, XCB, Breeze, D-Bus and Xvfb.

## Matrix

Each lane runs 30 times from the visible build-tree `obj-*/autotests` directory:

| Lane | Invocation | HOME |
| --- | --- | --- |
| direct-visible | selected max-entry function | visible |
| direct-hidden | selected max-entry function | packaging-shaped hidden HOME |
| ctest-visible | complete KRecentDocumentTest via CTest | visible |
| ctest-hidden | complete KRecentDocumentTest via CTest | packaging-shaped hidden HOME |

The `ctest-hidden` lane is the closest reproduction of Attempt 8 outside the actual sbuild chroot.

## Evidence preservation

A diagnostic-only source modification copies `m_xbelPath` immediately after `KRecentDocument::recentUrls()` and before the max-entry assertions. Upstream `cleanup()` is untouched, so test sequencing semantics are preserved.

Every run must produce a captured XBEL containing exactly three bookmarks. The evidence records return code, exact `temp File 11` / `temp File 12` signature, filenames, timestamps and duplicate timestamp groups.

If all four lanes remain clean, the next useful scope is an sbuild-contained KRecent diagnostic rather than another host-side approximation.

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
```
