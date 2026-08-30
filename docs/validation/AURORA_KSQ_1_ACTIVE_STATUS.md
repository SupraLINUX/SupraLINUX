# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This file records the current engineering state of KSQ-1 while the authoritative full-DAG candidate is still running. It is not an acceptance record and must not be interpreted as permission to enter KSQ-2.

## Certified prerequisite

KSQ-0 remains certified. The current KSQ-1 build contract consumes the certified 101-source closure and Ubuntu Resolute snapshot `20260829T022000Z`.

## Authoritative candidate

The authoritative patched full-DAG candidate was started as GitHub Actions run `33281736655` from commit `90fd5d3119ebfaab42f721d3bdd977a3472da498`.

At the time this record was written, its `001-020` job was still building and had not reported a package failure. No downstream checkpoint from this run may be assumed complete until its artifact and manifest are inspected.

A repository comparison from the candidate head to the later qualification-infrastructure commits showed no changes to candidate build inputs: the post-launch commits add reproducibility/tail-resume/acceptance tooling and documentation only. The tail-resume gate nevertheless verifies that build-input identity again before it may reuse any candidate artifact.

## Proven 081-101 timeout root cause

The independent forward discovery run `33264431724` reached DAG order 99 before GitHub cancelled job `99165540923` at its configured `timeout-minutes: 180` ceiling.

The build log proves the following source orders completed successfully before cancellation:

- 81 `kf6-ktexteditor`
- 82 `libplasma`
- 83 `kf6-frameworkintegration`
- 84 `libksysguard`
- 85 `sddm-kcm`
- 86 `bluedevil`
- 87 `kscreenlocker`
- 88 `plasma-keyboard`
- 89 `plasma-nm`
- 90 `plasma-pa`
- 91 `print-manager`
- 92 `breeze`
- 93 `ksystemstats`
- 94 `plasma5support`
- 95 `breeze-gtk`
- 96 `kwin`
- 97 `plasma-integration`
- 98 `kscreen`

Order 99 `plasma-workspace` had started and remained inside `sbuild` when the job-level timeout cancelled the runner. There is no package build failure recorded for order 99.

The preserved discovery evidence artifact is:

- name: `aurora-ksq-1-discovery-evidence-081-101`
- artifact ID: `9723899912`
- SHA-256: `636382ea83362a944a1dd756c64c64095eff8727df92b4cf3f9165c827feb9cd`

Its manifest contains exactly orders 81-98 as PASS. The preserved discovery DEB artifact is:

- name: `aurora-ksq-1-discovery-debs-081-101`
- artifact ID: `9723899191`
- SHA-256: `0319295375a765753aa615715342a532adeabb8f3916cc19d72ab3631b588781`

It contains 58 normal DEBs from the completed prefix. Evidence for order 99 contains prepared-source material only and is not treated as a successful build.

Conclusion: the observed stop is a **CI harness duration/granularity limit**, not evidence of a KDE dependency or package defect. No package, platform or architecture change is justified by this event.

## Timeout-safe tail continuation

To avoid discarding proven candidate work, KSQ-1 now has a dormant tail-resume gate:

- workflow: `.github/workflows/ksq-1-tail-resume.yml`
- merger: `scripts/ci/merge-ksq-1-tail-resume.py`
- functional fixture: `scripts/ci/test-merge-ksq-1-tail-resume.py`

The gate is deliberately inactive until `.github/ksq-1-tail-resume.env` is created with the exact completed authoritative base run and the actual last PASS order in its 081-101 artifact.

Before reuse, the gate requires:

1. the selected base run is a completed `Aurora KSQ-1 full source builds` run and its head SHA matches the selector;
2. the current repository has zero drift in the explicit candidate build-input set compared with that head;
3. standard base checkpoints 001-020, 021-040, 041-060 and 061-080 exist;
4. the partial 081-101 artifact is a contiguous PASS prefix from order 81 through the declared last completed order;
5. every retained DEB exists and its Package/Version/Architecture metadata matches the recorded binary index;
6. only the missing suffix is rebuilt on a fresh pinned Resolute builder;
7. the partial and completion evidence are merged only after exact source/version/order validation;
8. the resulting canonical 081-101 checkpoint is revalidated together with 001-080 by the existing `validate-ksq-1-full.py` 101-source gate.

The continuation job has a 360-minute job ceiling and a 330-minute build-step ceiling so artifact-preservation steps retain explicit headroom below GitHub's maximum job duration.

The range builder uses zero-padded chunk IDs. The resume workflow therefore derives the completion chunk with `%03d-101` rather than assuming an unpadded directory name.

## Tail merger validation

Run `33284759593` passed the helper/fixture gate. The fixture:

- creates 21 real minimal Debian packages;
- models 81-98 as the reusable completed prefix;
- retains prepared-but-not-PASS evidence for interrupted order 99;
- models 99-101 as the independent completion suffix;
- requires a successful canonical 81-101 merge;
- then removes order 98 from the partial manifest and requires the merger to reject the non-contiguous prefix.

The run emitted `AURORA_KSQ_1_TAIL_MERGER_TEST_PASS` and `AURORA_KSQ_1_REPRO_HELPERS_VALID`.

## Reproducibility gate

KSQ-1 reproducibility remains the previously fixed 95+6 contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against an independent reference build;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final patched candidate.

No reproducibility selector may be activated until the authoritative candidate, or a validated promoted tail-resume candidate derived from it, exposes a complete five-checkpoint artifact set and passes the full 101-source validator.

## Exit state

Current state remains:

- `KSQ-1 = ACTIVE`
- `KSQ-1 certified = no`
- `KSQ-2 unblocked = no`
- `C4.1 = paused pending KDE Stack Qualification`
