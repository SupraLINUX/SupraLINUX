# Aurora KSQ-1 — accepted range 081–090 on immutable r3

Status: **PASS / INDEPENDENTLY ACCEPTED**

This record covers the maintained local-only KSQ-1 build and independent acceptance of source orders 81–90. It advances the maintained package checkpoint from order 80 / 345 DEBs to order 90 / 376 DEBs. It does not certify the complete 101-source candidate and does not satisfy the dedicated reproducibility obligation for order 81 `kf6-ktexteditor`.

## Fixed inputs

- Ubuntu base: `26.04 LTS Resolute`, amd64;
- snapshot timestamp: `20260829T022000Z`;
- immutable corrective slice: `20260829T022000Z-r3`;
- certified build-order SHA-256: `9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`;
- predecessor acceptance: orders 66–80 accepted by run `33978315934`, artifact `9972976872`, digest `sha256:ebd60471d9834efbb4fad9f5680c6a153000aa8b9393f4821a70ff148edc2511`;
- predecessor checkpoint: order `80` / `345` DEBs;
- APT Recommends: normal/default.

Maintained build architecture:

`GitHub-hosted Ubuntu 26.04 -> immutable local r3 slice -> mmdebstrap --mode=unshare --variant=buildd -> sbuild --chroot-mode=unshare --no-enable-network`

No Docker, custom AppArmor profile or uidmap/file-capability rewrite is part of the maintained path.

## Source-build run

- run: `33978550975`;
- source HEAD: `8b54e2aa98e7df0d82a09b0d840cd2163913c409`;
- artifact: `9974023708` (`aurora-ksq-native-range-081-090-r3`);
- artifact size: `155218992` bytes;
- artifact digest: `sha256:dfa78a851139b279f08d58bef9a0d95fc9261a26c18b6c1dc85a65afe29401ed`;
- sources: `10 / 10 PASS`;
- new DEBs: `31`;
- accumulated DEBs: `376`;
- applied packaging adaptations in this range: `0`;
- external APT HTTP(S) during source builds: `0`;
- relevant AppArmor denials: `0`;
- Docker/custom AppArmor/uidmap-filecap workaround: `0 / 0 / 0`.

Independent artifact inspection outside the workflow verified all 31 DEB payload hashes and all ten `.build` logs. Every build log contains the maintained network-isolation proof markers and `Status: successful`.

Exact evidence-file identities:

- `new-debs.sha256`: `55ca76a914d936daff2de9da1c55d372e16b6c4491a34a06a4dbbd36419a57f8`;
- `build-manifest.tsv`: `1d0bcef5e136fe7ac8e8fc1f91d43fa5c070fc658966cf7f16800aef15e2b82b`.

## Independent acceptance

The first acceptance attempt, run `33994677077`, failed closed before acceptance because the validator assumed the source artifact would extract below `build/ksq-1/...`; the actual 81–90 artifact is rooted at `ksq-1/...`. Its prior/source provenance checks and artifact downloads had passed. This was a validator path-layout defect, not a source-build, package or r3 failure, and it did not promote the checkpoint.

The downstream consumers were corrected to locate exactly one supported artifact root (`ksq-1/...` or `build/ksq-1/...`) and reject ambiguous/missing layouts. The same correction was applied proactively to both 91–101 build and acceptance consumers because the 66–80 and 81–90 raw artifacts intentionally have heterogeneous extraction roots.

Successful acceptance retry:

- run: `33994817042`;
- acceptance HEAD: `ddffb2dfb6aa6c48e56cc07b11a11696d6cb5c9b`;
- artifact: `9977725295` (`aurora-ksq-accept-081-090-r3`);
- artifact size: `8115` bytes;
- artifact digest: `sha256:aa4d0499623073108161750881eee06804d1a1d20e5cd45e4a83ab4de3ad7d04`;
- acceptance result: `PASS`;
- accepted checkpoint: **order 90 / 376 DEBs**;
- next range: `91-101`.

The acceptance artifact was independently downloaded after the workflow and its complete `evidence.sha256` manifest verified successfully. Its `acceptance.env` records 31 new DEBs, 376 accumulated DEBs, zero range adaptations, zero external build HTTP and zero relevant AppArmor denials.

## Reproducibility boundary

Order 81 `kf6-ktexteditor` has a normal-build PASS and is valid for dependency progress through the accepted package checkpoint. It is one of the six dedicated nodes in the fixed `95 + 6` reproducibility contract, so:

`AURORA_KSQ_R3_081_090_KTEXTEDITOR_REPRODUCIBILITY_CERTIFIED=no`

remains mandatory until the dedicated independent rebuild comparison against the final 101-source candidate passes.

This acceptance does not alter the corresponding pending dedicated obligations for orders 29, 68, 99, 100 and 101.

## Resulting gate state

- orders 1–90 package build chain: **accepted**;
- maintained package checkpoint: **order 90 / 376 DEBs**;
- orders 91–101: authorized to build from this exact checkpoint;
- complete 101-source candidate: **not yet accepted**;
- dedicated reproducibility: **not certified**;
- KWallet automatic session unlock: **not certified**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**.
