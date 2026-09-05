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

r3 may be materialized only if an independent 66–101 analysis proves all 36 source contexts and emits a non-empty `gap-objects.tsv` whose rows are machine-derived from the real build logs and APT-verified Ubuntu snapshot metadata.

No historical package list, observed JPEG/curl gap, package name, workaround or manual addition is allowed to create the r3 gap.

The materializer additionally re-resolves every proposed gap row against the signed `Packages.xz` metadata already contained in and validated with r2. Each object must match exact:

- package;
- version;
- architecture;
- `Filename`;
- `Size`;
- `SHA256`.

The original 1783 r2 binary objects and all source/metadata objects are retained. r2 itself is never modified.

## Branch-safe promotion chain

A branch-only `workflow_run` receiver is not used as the authoritative chain because GitHub evaluates that trigger from the default branch. The active KSQ work remains on `feature/kde-stack-qualification`, so promotion is explicitly bound by committed trigger files containing exact run/artifact identities.

No trigger file described below exists until its predecessor has actually passed and its output artifact has been independently inspected.

### 1. Explicit witness analysis

Workflow:

- `.github/workflows/ksq-snapshot-build-context-witness-explicit-analysis.yml`.

Trigger:

- `.github/ksq-snapshot-witness-analysis-trigger.env` — **not created yet**.

The trigger must contain the exact completed witness run ID, exact 40-hex head SHA, and order range 66–101. Before downloading artifacts the workflow verifies through the GitHub API that the referenced run is `completed/success`, belongs to `feature/kde-stack-qualification`, has the exact expected workflow name and exact head SHA.

It then downloads only these artifacts from that exact run:

- `aurora-ksq-witness-evidence-066-080`;
- `aurora-ksq-witness-evidence-081-090`;
- `aurora-ksq-witness-evidence-091-101`.

The analyzer reconstructs the signed snapshot package corpus, compares all 36 observed build contexts with the exact 1783-object r2 manifest and publishes `aurora-ksq-build-context-witness-066-101-independent-analysis` only after `PROVEN`, 36/36 logs and `MANUAL_PACKAGE_ADDITIONS=0` are established.

### 2. r3 materializer

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

### 3. Explicit r3 publication

Workflow:

- `.github/workflows/ksq-snapshot-slice-r3-explicit-materialize.yml`.

Trigger:

- `.github/ksq-snapshot-r3-materialize-trigger.env` — **not created yet**.

The trigger must bind exact analysis run ID, exact head SHA, exact artifact ID, digest and size. The workflow revalidates those identities through the GitHub API, downloads that exact analysis artifact, redownloads and validates the immutable canonical r2 release, materializes only the signed gap and refuses to overwrite an existing r3 release tag.

A published r3 remains a **candidate**. Publication never updates `scripts/ci/aurora-ksq-snapshot-release.env`.

A non-authoritative `workflow_run` prototype and its preflight are retained as engineering history, but they are not the branch-safe promotion path.

### 4. Explicit independent r3 validation

Workflow:

- `.github/workflows/ksq-snapshot-slice-r3-explicit-validation.yml`.

Trigger:

- `.github/ksq-snapshot-r3-validation-trigger.env` — **not created yet**.

The trigger must bind the exact successful r3 publication run and exact publication artifact identity. A fresh Ubuntu 26.04 runner then:

1. revalidates the publication run/artifact identity;
2. downloads the r3 release independently from the publication artifact;
3. validates the full r3 slice and signed metadata;
4. independently downloads canonical r2;
5. proves r3 is a strict byte-preserving extension of r2: identical signed metadata, source inputs and all 1783 pre-existing binary manifest rows/payload hashes, plus exactly the witness gap;
6. revalidates the original independent witness analysis and compares its `gap-objects.tsv` byte-for-byte with r3;
7. emits independent evidence while keeping `CANONICAL_POINTER_UPDATED=no` and `KSQ_REGRESSION_REQUIRED=yes`.

## Regression and promotion boundary

Even if r3 publication and independent validation pass, r3 is not automatically canonical and previous KSQ evidence is not automatically carried forward.

If strict-extension validation proves that all signed metadata, source inputs and the original 1783 payloads are byte-identical, that identity evidence may be used to define the smallest technically justified regression scope, but it does not by itself waive regression.

The next maintained build unit must be rebuilt local-only against the independently validated r3 candidate, with the exact r3 release identity and validation artifact fixed in the regression trigger. Orders 66–80 remain unaccepted until that local-only build and its full artifact inspection pass.

Only after the required regression passes may the canonical snapshot pointer be considered for promotion from r2 to r3.

## Current gate

- accepted checkpoint: **order 65 / 295 DEBs**;
- r2: **immutable / accepted through order 65 / rejected as complete 101-source payload closure**;
- 66–101 per-build witness: **ACTIVE**;
- explicit witness-analysis trigger: **NOT CREATED**;
- r3 implementation: **PREPARED**;
- explicit r3 materialization trigger: **NOT CREATED**;
- r3 release: **DOES NOT EXIST / NOT MATERIALIZED**;
- explicit r3 validation trigger: **NOT CREATED**;
- r3 canonical pointer: **NO**;
- orders 66–80: **NOT ACCEPTED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
