# KDE Tier 3 KIO Round 22 — KRecent CTest/HOME matrix

Status: **diagnostic PASS; Attempt 8 failure not reproduced outside sbuild**.

Closed evidence:

- workflow run: `36278019755`
- job: `108504444054`
- commit: `07282c338c1c6d3b1341e4ba8d4d1c82c9b3b658`
- artifact: `10917842068`
- artifact SHA-256: `0554aeb1a38aa78de4b9316e85058fbfd6b24cc8ff62c7978cfa286f6ea34f8e`

All four lanes were valid and clean:

| Lane | Runs | Failures | Attempt 8 signature | Valid XBEL captures | Duplicate timestamp runs |
| --- | ---: | ---: | ---: | ---: | ---: |
| direct-visible | 30 | 0 | 0 | 30 | 0 |
| direct-hidden | 30 | 0 | 0 | 30 | 0 |
| ctest-visible | 30 | 0 | 0 | 30 | 0 |
| ctest-hidden | 30 | 0 | 0 | 30 | 0 |

Therefore neither the hidden packaging HOME nor complete KRecentDocumentTest execution through CTest is sufficient to reproduce the historical failure on the hosted runner filesystem.

Round 23 moves the diagnostic into the exact Attempt 8 rootfs artifact. No package build, package revision, test suppression or Attempt 9 authorization occurs.

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
```
