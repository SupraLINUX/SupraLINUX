# KDE Tier 3 KIO Round 25 — deterministic XBEL ordering remediation proof

Status: **closed historical evidence**.  
Historical Round 25 contract: **FAIL**.  
Target KRecent remediation: **PASS**.  
Candidate package execution / Attempt 9: **not authorized**.

## Result

Round 25 ran through the valid historical Attempt 8 build path.

Evidence:

- workflow run: `36359842892`
- job: `108734756942`
- branch commit: `5d8b72cf6d468550aa520d0a09c169ff9c1bf05f`
- artifact: `10945592004`
- artifact SHA-256: `0ac55c97c3efb725bd46500d9f899fcc0222368f8b60973b574356975b2dd1ce`
- candidate patch SHA-256: `8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602`
- candidate source SHA-256: `57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b`

The declared Round 25 contract required the complete CTest suite to exit zero, so the historical result remains **FAIL** and is not rewritten.

## KRecent target evidence

The deterministic XBEL ordering candidate itself succeeded:

| Lane | Runs | KRecent failures | Non-zero CTest | Final order |
| --- | ---: | ---: | ---: | --- |
| native | 100 | 0 | 0 | 100× `12,13,14` |
| fixed/all timestamps tied | 100 | 0 | 0 | 100× `12,13,14` |
| monotonic/no ties | 20 | 0 | 0 | 20× `12,13,14` |
| full suite | 1 | KRecent PASS | suite non-zero | `12,13,14` |

Therefore the target KRecent remediation is **PASS**: 220/220 isolated executions passed, including 100 forced-tie executions, and KRecent also passed in the complete suite.

## Why the Round 25 contract failed

The complete suite had 68/69 tests PASS. The only remaining failure was the already-historical independent blocker `kiowidgets-kdirmodeltest`.

The two assertions are identical to Attempt 8:

- `KDirModelTest::testShowRoot()`: `dirModel.indexForUrl(homeUrl).isValid()` is false at line 1353;
- `KDirModelTest::testShowRootAndExpandToUrl()`: the same assertion is false at line 1393.

KDirModel's test and relevant implementation are unchanged between KIO 6.30.0 and current upstream master, so Round 25 did not introduce this failure.

## Hidden-HOME causal candidate

The historical test HOME is:

```text
/build/reproducible-path/kf6-kio-6.30.0/debian/.supralinux-test-home/sbuild
```

Both failing tests open `file:///` with `ShowRoot` and then call `expandToUrl(homeUrl)`. KDE's `KCoreDirLister` defaults to `setShowHiddenFiles(false)`.

That means expansion from `/` must traverse the hidden path component `.supralinux-test-home`, which the default lister does not expose. This also explains why the direct-home `testShowRootWithTrailingSlash()` path passes.

This is a strong causal hypothesis, not yet canonical evidence. Round 26 tests the hidden path against an otherwise equivalent visible HOME.

## Canonical state

```text
12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED
KIO 6.30.0-0supralinux8 = FAIL
Attempt 8 = CLOSED-MIXED
Attempt 9 = NOT AUTHORIZED
Round 24 = diagnostic-PASS / timestamp-tie-causality-confirmed
Round 25 historical contract = FAIL
Round 25 target KRecent remediation = PASS
Next gate = tier3-round26-kio-kdirmodel-hidden-home-causality-definition
```

Round 25 changes diagnostic/remediation knowledge only. It does not suppress tests, change the canonical KIO state, unblock dependents, allocate a package revision or authorize Attempt 9.
