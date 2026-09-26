# KDE Tier 3 KIO Round 20 — environment-corrected residual diagnostic

Status: definition pending diagnostic evidence.

Round 20 is a **non-promoting diagnostic**. It does not build a Debian package, allocate a new KIO revision, suppress tests, alter the DAG, or authorize Attempt 9.

## Why Round 20 exists

Round 19 executed successfully as a diagnostic workflow, but inspection of its artifact found two methodology defects that prevent causal conclusions.

### KRecentDocument

The targeted runner created a fresh `HOME` but did not create the parent used by Qt test mode. `QStandardPaths::setTestModeEnabled(true)` resolves the recent-document XBEL to `$HOME/.qttest/share/recently-used.xbel`.

Round 19 therefore produced `recentUrls.length() == 0`, not the Attempt 8 failure where `temp File 11` was retained instead of `temp File 12`.

Round 20 creates `$HOME/.qttest/share` and `$HOME/.qttest/config` for every fresh run and treats bookmark counts as validity guards. The timestamp hypothesis is evaluated only after those guards pass.

### KDirModel

Round 19 changed `.supralinux-test-home` to `supralinux-test-home`, but the diagnostic workspace itself lived below a `.work` component. Its nominal visible control therefore still had a hidden path component.

Round 20 uses a truly visible control HOME under `$RUNNER_TEMP/supralinux-kdir-home/sbuild` and audits every path component before accepting the control. It runs only:

- `testShowRoot`
- `testShowRootWithTrailingSlash`
- `testShowRootAndExpandToUrl`

with the same Qt/KDE display environment used by the Attempt 8 test campaign.

## KRecentDocument sequence

1. 30 baseline runs in independent fresh homes.
2. One diagnostic capture-all build with `MaxEntries=50`.
3. Record all 15 XBEL entries and their `modified` values.
4. Restore upstream test source.
5. Inject only `QTest::qWait(5)` after each add.
6. Run 30 delayed repetitions.
7. Restore the source byte-for-byte.

A KRecent conclusion is invalid unless each baseline/delayed run leaves exactly three XBEL bookmarks and capture-all leaves exactly fifteen.

If the valid baseline fails, duplicate timestamps are observed, and all delayed runs pass, timestamp collision ordering is confirmed. Otherwise the evidence determines a narrower follow-up.

## KDirModel sequence

A/B/A:

1. canonical hidden HOME;
2. audited truly visible HOME;
3. canonical hidden HOME again.

If A and A-repeat reproduce the two historical expansion failures while B passes, the hidden HOME component controls the failure. If B also reproduces them, the hidden-component hypothesis is rejected and the next diagnostic must inspect expansion/listing state.

## Invariants

Canonical state remains:

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
```

Round 20 produces evidence only. Any source remediation, revision allocation, package build, or Attempt 9 activation requires a later lifecycle step.
