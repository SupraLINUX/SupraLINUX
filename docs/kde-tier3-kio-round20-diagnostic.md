# KDE Tier 3 KIO Round 20 — environment-corrected residual diagnostic

Status: **diagnostic PASS, partially causal**.

Round 20 remained non-promoting: no Debian package, KIO revision, test suppression, DAG transition, or Attempt 9 authorization occurred.

## Closed evidence

- workflow run: `36244913604`
- job: `108412266582`
- artifact: `10906434669`
- artifact SHA-256: `2071034608c31411399b656fb4e963cd066bded08e8c52566beea6c186d77fbc`

## KDirModel result

The corrected A/B/A control is causal. Hidden HOME fails both ShowRoot expansion tests, the audited visible HOME passes both, and the hidden HOME repeat fails again. `testShowRootWithTrailingSlash` passes in all three runs.

Conclusion: **a hidden component in HOME controls the KDirModel ShowRoot/expand failure in this diagnostic environment**.

## KRecentDocument result

The KRecent branch is invalid for the Attempt 8 symptom. The exact KDE 6.30.0 source shows that the test creates `temp File N` below `QDir::currentPath()`, while `KRecentDocument::add()` ignores local URLs containing `/.` when `IgnoreHidden` is true. Round 20 ran from the repository `.work` tree, so those inputs were discarded before XBEL creation.

In addition, QTest invokes `KRecentDocumentTest::cleanup()` after the selected test, and that cleanup removes `m_xbelPath`. Post-process XBEL evidence therefore needs explicit diagnostic preservation.

Round 20 cannot accept or reject the KRecent timestamp-ordering hypothesis.

## Handoff

Round 21 is KRecent-only and uses a visible non-temporary CWD, fresh visible HOME, explicit diagnostic XBEL preservation, and actual XBEL discovery.

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
```
