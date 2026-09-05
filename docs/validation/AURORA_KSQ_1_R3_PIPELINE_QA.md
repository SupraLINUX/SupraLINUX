# Aurora KSQ-1 — r3 pipeline QA record

Status: **QA PASS FOR PREPARED PIPELINE / r3 NOT MATERIALIZED / NOT CANONICAL**

This record supplements `AURORA_KSQ_1_R3_PREPARATION.md` while the authoritative 66–101 witness is still running. It does not advance KSQ-1 beyond accepted order 65 / 295 DEBs and it does not create or promote r3.

## Authoritative witness identity

The only witness run authorized as input to the future explicit analysis is:

- run: `33929720702`;
- workflow: `Aurora KSQ snapshot build-context witness 066-101`;
- head: `84596eaf2f7d7735b74f48a48fdde82229500f7a`;
- branch: `feature/kde-stack-qualification`.

Range 66–80 is already PASS as witness-only evidence. Range 81–90 is still executing. Range 91–101 remains pending behind it.

A later code change to the analyzer caused GitHub path filtering to start another full witness, run `33936827576` at head `68472911dfc0225e52dd6f24f56b2c5d32f1cf0f`. That run is explicitly **redundant and non-authoritative**. No artifact from it may be used to derive r3. The connected GitHub action surface exposed no run-cancel operation, so provenance is enforced by fixing the future analysis trigger to run `33929720702` / head `84596eaf...` exactly.

## QA-1 — canonical local archive path

The slice validators intentionally require `aurora-local.sources` to point to the exact filesystem path at which the slice is mounted. Canonical r2 is bound to:

`/opt/supralinux/archive/20260829T022000Z-r2/ubuntu`

The first mechanics probe, run `33935394602`, extracted r2 below `$RUNNER_TEMP`; archive hash, size and Ubuntu signatures passed, then the validator correctly failed the local-path invariant.

No validator was relaxed. Commit `78f77fed00796e2952b5af1e64365193af120dd2` changed the probe to use `/opt/supralinux/archive`. Corrected run `33936466728` completed SUCCESS end-to-end.

Its inspected artifact:

- artifact ID `9960344170`;
- digest `sha256:e633384754022d0f8742bc41775f70f58f1dd13f850fee6e0d4b9709241c688a`;
- `evidence.sha256`: PASS;
- synthetic r3 fixture: `1784 = 1783 r2 + 1` objects;
- inherited signed Ubuntu metadata: PASS;
- base metadata/source identity: PASS;
- manual additions: `0`;
- promotable: `no`;
- witness evidence: `no`;
- release published: `no`.

The same path-class bug was then found statically in the prepared explicit r3 validation workflow. Commit `9cec624b234b83f8fc8c7b511689e46008fc0ed9` changed independent r2/r3 extraction and validation to the canonical `/opt/supralinux/archive` root. The explicit publication workflow and the local-only 66–80 r3 regression already used that canonical root and required no change.

## QA-2 — real APT snapshot URL token

The prepared witness analyzer originally defined the accepted prefix with a mandatory trailing slash:

`https://snapshot.ubuntu.com/ubuntu/20260829T022000Z/`

Inspection of the real accepted 66–80 witness artifact showed that APT prints transport tokens as the exact base URL without that trailing slash:

`https://snapshot.ubuntu.com/ubuntu/20260829T022000Z`

Measured against the actual 66–80 evidence:

- remote transport lines: `8091`;
- lines accepted by the old trailing-slash test: `0`;
- `Get:` package acquisition matches: `7836`;
- unique package/version/architecture selections: `804`.

The corrected policy accepts a transport URL only when it is exactly the fixed snapshot base or a child below `base/`. It still rejects every other host and every other timestamp.

The functional change is represented by commits `700384c85160947500265becee3b59b5f0944de7` and `68472911dfc0225e52dd6f24f56b2c5d32f1cf0f`; the second restores an invariant comment accidentally dropped while constructing the Git-data commit. Comparison from parent `9cec624b...` to final `68472911...` is exactly one file with two additions and two deletions: only the intended two functional lines differ.

Re-test against the real 66–80 artifact after the correction:

- remote transport lines: `8091`;
- non-snapshot lines: `0`;
- `Get:` matches: `7836`;
- unique package selections: `804`;
- result: PASS.

## QA-3 — r2 object-list input remains exact

The explicit analyzer's historical r2 object-list input was redownloaded independently:

- artifact ID: `9883249125`;
- ZIP SHA-256: `2281ab4655dc8d33639d9a3bbfb75d60325829a6b0af19902c20e4406e0c945b`;
- ZIP bytes: `136259`;
- `binary-objects.tsv`: exactly `1783` rows.

This matches the constants already enforced by the explicit analysis workflow.

## QA-4 — artifact transport in independent r3 validation

GitHub's REST artifact download endpoint is redirect-based. The prepared independent validation previously used the raw ZIP endpoint for the original analysis artifact after separately checking metadata.

Commit `2e1eda676f4a68134dfd4359b4634b3c5afe3adf` keeps API checks for exact run/artifact identity but moves the actual analysis-artifact download to `actions/download-artifact@v8` with:

- exact artifact ID;
- exact run ID;
- exact repository;
- GitHub token;
- `digest-mismatch: error`.

The downloaded `gap-objects.tsv` is still compared byte-for-byte with the r3 embedded gap and the slice is revalidated with the exact witness-analysis directory.

## QA-5 — static pipeline preflight

The static preflight now compiles both Python programs and parses all four prepared r3 workflows. It is triggered when either analyzer/materializer Python or any r3 chain workflow changes.

Verified runs:

- `33935224782`: PASS — initial r3 pipeline syntax/preflight;
- `33936649305`: PASS — after canonical archive-root correction;
- `33936849387`: PASS — analyzer added to Python preflight;
- `33936904837`: PASS — after exact artifact-transport hardening.

The latest preflight therefore covers the current prepared pipeline state through commit `2e1eda676f4a68134dfd4359b4634b3c5afe3adf`.

## Current gate

- accepted KSQ checkpoint: **order 65 / 295 DEBs**;
- r2: **canonical and immutable**;
- authoritative 66–101 witness: **ACTIVE** (`33929720702`);
- witness 66–80: **PASS AS WITNESS ONLY**;
- witness 81–90: **ACTIVE**;
- witness 91–101: **PENDING**;
- duplicate witness `33936827576`: **NON-AUTHORITATIVE / MUST NOT BE USED**;
- explicit witness-analysis trigger: **NOT CREATED**;
- r3 release: **DOES NOT EXIST**;
- r3 canonical pointer updated: **NO**;
- orders 66–80 accepted: **NO**;
- KSQ-1 certified: **NO**.
