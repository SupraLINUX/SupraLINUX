# KDE Tier 3 KIO Round 26 — hidden-HOME causality and combined remediation proof

Status: **remediation-PASS; closed historical evidence**.  
Candidate package execution / Attempt 9: **not authorized**.  
Canonical KIO: **6.30.0-0supralinux8 = FAIL**.

## Why Round 26 exists

Round 25 proved the KRecent ordering candidate itself:

- native: 100/100 PASS;
- forced timestamp ties: 100/100 PASS;
- monotonic no-tie control: 20/20 PASS;
- KRecent also passed in the complete suite.

The historical Round 25 contract nevertheless remained FAIL because the full suite reproduced the independent `kiowidgets-kdirmodeltest` failure already present in Attempt 8.

The exact assertions are:

- `testShowRoot()`: `indexForUrl(homeUrl).isValid()` false at line 1353;
- `testShowRootAndExpandToUrl()`: the same assertion false at line 1393.

## Upstream and packaging evidence

The KDirModel test and relevant implementation are byte-identical between KIO v6.30.0 and current master at definition time.

KCoreDirLister defaults to hidden files disabled:

```cpp
setShowHiddenFiles(false);
```

The historical SupraLINUX test HOME is:

```text
/build/reproducible-path/kf6-kio-6.30.0/debian/.supralinux-test-home/sbuild
```

Both failing tests start from `file:///` and recursively `expandToUrl(homeUrl)`. That requires discovering `.supralinux-test-home`, but the default lister does not expose hidden path components.

The direct-home ShowRoot test historically passes, which is consistent with this mechanism because it does not need to discover the HOME through a hidden parent.

## Round 26 experiment

Round 26 preserves the exact Attempt 8 rootfs, source materialization, predecessor packages, sbuild/unshare path and the exact proven Round 25 KRecent candidate patch.

It changes only the test HOME for the controlled lane:

| Lane | Runs | HOME | Expected |
| --- | ---: | --- | --- |
| hidden-home | 10 | `debian/.supralinux-test-home/sbuild` | exact two historical KDirModel assertions in 10/10 |
| visible-home | 20 | `debian/supralinux-test-home/sbuild` | 20/20 KDirModel PASS |
| full-suite-visible | 1 | visible HOME | 69/69 PASS |

The KRecent candidate patch SHA-256 must remain:

```text
8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602
```

The full-suite lane must additionally show KRecent final order `12,13,14`.

## PASS meaning

A PASS proves both:

1. the remaining KDirModel failure is caused by SupraLINUX's hidden test-HOME path rather than by the KRecent source remediation;
2. the combined candidate — deterministic KRecent ordering plus a visible packaging test HOME — closes all 69 KIO tests in the retained historical build path.

This still does not authorize Attempt 9. Round 26 remains non-promoting and produces no candidate package.

## Result

Round 26 completed successfully in workflow `36366972800`, job `108755265236`.

Evidence artifact:

- artifact ID: `10948970106`
- artifact SHA-256: `7c8b91266fd9ecd79638c8c4bfc5419dadac937b911517522b083900e9bc9f98`

Causal controls:

| Lane | Result |
| --- | --- |
| historical hidden HOME | **10/10 reproduced the exact historical KDirModel signature** |
| visible HOME | **20/20 PASS** |
| full suite with visible HOME + exact KRecent candidate | **69/69 PASS** |

The full-suite lane also retained the expected KRecent final order `12,13,14`.

Conclusion: `hidden-home-causality-and-combined-kio-remediation-PASS`.

The evidence confirms that the remaining KDirModel failure was caused by the hidden SupraLINUX test-HOME path. The proven combined remediation is therefore:

1. the exact deterministic KRecent ordering candidate from Round 25;
2. a visible packaging test HOME instead of `debian/.supralinux-test-home/sbuild`.

Round 26 remained non-promoting. No package revision was allocated and Attempt 9 was not executed.

## Current state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Round 24 = diagnostic-PASS / timestamp-tie-causality-confirmed
Round 25 historical contract = FAIL
Round 25 target KRecent remediation = PASS
Round 26 = remediation-PASS / combined KIO proof 69/69
Next gate = tier3-attempt9-kio-remediation-definition
```
