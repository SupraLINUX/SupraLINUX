# KDE Tier 3 KIO Round 19 diagnostic

Status: **definition pending diagnostic CI**.

## Purpose

Attempt 8 closed MIXED: KXMLGui remained PASS, while KIO 6.30.0-0supralinux8 reached 67/69 upstream tests. The Qt SVG provider remediation is proven useful because both the previous KNewFileMenu icon failure and KDirModelTest::testIcon now PASS.

Round 19 isolates the two remaining failures without allocating a package revision, suppressing tests, or changing canonical package/DAG state.

## Attempt 8 residual failures

### KRecentDocument

`testXbelBookmarkMaxEntries()` performs 15 immediate additions with `MaxEntries=3` and expects files 12, 13 and 14. KIO prunes by parsed `modified` timestamps. Round 19 records exact XBEL timestamps, measures duplicate timestamp groups, and compares the exact baseline with a diagnostic-only 5 ms spacing between additions.

The extracted source is restored byte-for-byte after the test-only probe.

### KDirModel

The failing functions open `file:///` and then call `expandToUrl(QDir::homePath())`. Attempt 8 sets HOME below:

`debian/.supralinux-test-home/sbuild`

That path contains a hidden HOME component. The trailing-slash test opens HOME directly and already passes.

Round 19 performs an A/B/A with the exact unmodified KDirModel test binary:

1. hidden HOME component;
2. equivalent visible HOME component;
3. hidden HOME component again.

If the two hidden phases reproduce the ShowRoot failures while the visible phase passes, the HOME fixture is causal rather than KDirModel itself.

## Safety

- no Debian package build;
- no KIO revision bump;
- no test suppression;
- no canonical source modification;
- no DAG/downstream eligibility change;
- diagnostic workflow is reusable and invoked only by the PR router, not directly by `pull_request`.

Next gate: `tier3-round19-kio-residual-test-diagnostic-evidence`.
