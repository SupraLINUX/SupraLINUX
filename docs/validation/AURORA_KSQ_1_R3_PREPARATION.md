# Aurora KSQ-1 — r3 preparation state

Status: **PREPARED / NOT MATERIALIZED / NOT CANONICAL**

This record documents the implementation prepared while the current per-build-context witness for orders 66–101 is still running. It is not an r3 acceptance record and does not advance the maintained checkpoint beyond order 65 / 295 accumulated DEBs.

## Fixed upstream input

The upstream Ubuntu archive point remains exactly `20260829T022000Z`. r3 is not a newer Ubuntu snapshot. It is designed only as a new immutable Supra local-slice identity derived from the proven payload under-closure of r2.

Canonical r2 remains immutable:

- slice: `20260829T022000Z-r2`;
- release ID: `381836501`;
- archive asset ID: `542414026`;
- archive SHA-256: `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`;
- archive bytes: `1054177280`;
- binary objects: `1783`;
- binary bytes: `785219274`.

## Current witness

Authoritative current witness run:

- workflow: `.github/workflows/ksq-snapshot-build-context-witness-066-101.yml`;
- run: `33929720702`;
- head used by the witness: `84596eaf2f7d7735b74f48a48fdde82229500f7a`;
- accepted input reconstructed before witness: order 65 / 295 DEBs;
- first witness range: 66–80;
- state at this record: still executing the real `sbuild` range; no range result is inferred before the job closes.

The source-fetch transport was independently proven before relying on the long witness:

- probe run `33929750946`: PASS;
- source acquisition limited to `https://snapshot.ubuntu.com/ubuntu/20260829T022000Z`;
- non-snapshot HTTP(S) transport remains fail-closed;
- package builds still use `sbuild --no-enable-network`.

## r3 derivation contract

r3 may be materialized only if the independent 66–101 analysis proves all 36 source contexts and emits a non-empty `gap-objects.tsv` whose rows are machine-derived from the real build logs and APT-verified Ubuntu snapshot metadata.

No historical package list, observed JPEG/curl gap, package name, workaround or manual addition is allowed to create the r3 gap.

The materializer additionally re-resolves every proposed gap row against the signed `Packages.xz` metadata already contained in and validated with r2. Each object must match exact:

- package;
- version;
- architecture;
- `Filename`;
- `Size`;
- `SHA256`.

The original 1783 r2 binary objects and all source/metadata objects are retained. r2 itself is never modified.

## Prepared implementation

### Materializer

`scripts/ci/ksq-snapshot-slice-r3.py`

Initial implementation commit: `7e53034d4a0e98207867573df848012756a812b0`.

Properties:

- creates new identity `20260829T022000Z-r3`;
- refuses an empty witness gap;
- refuses duplicate/manual/unsigned gap identities;
- preserves metadata hardlinks while copying the validated r2 base;
- downloads only the exact witness-derived gap from the fixed Ubuntu snapshot;
- verifies each downloaded object by signed size + SHA-256;
- rewrites only the local `file:` source path from r2 identity to r3 identity;
- regenerates the binary manifest as exact `r2 union gap`;
- retains witness/base provenance;
- validates the complete object whitelist and signed metadata;
- hardens the completed slice read-only.

### Publication workflow

`.github/workflows/ksq-snapshot-slice-r3-materialize.yml`

Commit introducing the workflow: `a7fdd88b89244335b56211164b31f271742121c6`.

Push preflight run `33934340147` passed. On a normal push the materialization job is skipped. Publication is eligible only after the independent build-context analysis workflow itself finishes `success`.

A published r3 remains a **candidate**. The workflow refuses to overwrite an existing r3 release tag.

### Independent validation

Prepared independent validators:

- `.github/workflows/ksq-snapshot-slice-r3-independent-validation.yml` — fresh redownload of r3, full object/signature validation and exact cross-check against the referenced independent witness artifact;
- `.github/workflows/ksq-snapshot-slice-r3-base-identity-validation.yml` — fresh independent downloads of both r2 and r3 and proof that r3 is a strict payload-only extension: identical signed metadata/source inputs, identical 1783 pre-existing binary manifest rows/payloads, plus exactly the witness gap.

The second validator was introduced by commit `4c8dc7b069f2086ae87e4cc61beaf3adfd2ce7bd`.

Neither validator updates the canonical snapshot pointer.

## Promotion boundary

Even if r3 publication and both independent validations pass, r3 is not automatically canonical and previous KSQ evidence is not automatically carried forward.

Before promotion, the regression scope must be decided from proven identity results and executed. The next maintained local-only range must then be rebuilt against the independently validated r3 input. Orders 66–80 remain unaccepted until that occurs.

## Current gate

- accepted checkpoint: **order 65 / 295 DEBs**;
- r2: **immutable / accepted through order 65 / rejected as complete 101-source payload closure**;
- 66–101 per-build witness: **ACTIVE**;
- r3 implementation: **PREPARED**;
- r3 release: **DOES NOT EXIST / NOT MATERIALIZED**;
- r3 canonical pointer: **NO**;
- orders 66–80: **NOT ACCEPTED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
