# Aurora KSQ-1 maintained local-slice range migration

Status: **001-043 PASS ON CANONICAL R2 — 044-060 NEXT**

This document tracks the maintained KSQ-1 range builder on the published local snapshot slice. It does not certify KSQ-1 by itself. KSQ-0 remains **CERTIFIED / CLOSED** and its source/package decisions are consumed unchanged.

## Current slice identity

Upstream Ubuntu archive snapshot:

`20260829T022000Z`

Canonical SupraLINUX local materialization:

`20260829T022000Z-r2`

The separate r2 identity is required because the original local slice was proven incomplete for the real builder's default APT Recommends semantics. r2 preserves the same upstream snapshot and certified 101-source DAG while correcting the complete binary closure and pinning generic `amd64` behavior.

Canonical pointer:

`scripts/ci/aurora-ksq-snapshot-release.env`

Status: `INDEPENDENTLY_VALIDATED`.

## Migration design

The maintained build engine remains `scripts/ci/build-ksq-1-range.sh`. The local-slice path supplies it with:

- certified KSQ-0 metadata restored from immutable evidence;
- signed local `file:` APT metadata;
- unprivileged `mmdebstrap --mode=unshare --variant=buildd` build roots;
- `sbuild --chroot-mode=unshare`;
- fail-closed checkpoint restoration;
- package/source transport isolated from the external network during builds.

The current selected path is native on GitHub-hosted Ubuntu 26.04. Docker is not part of the maintained 041+ r2 build path.

Local source acquisition uses Resolute APT `Acquire::Source-Symlinks=false` so source preparation receives ordinary files from the signed local repository.

## Stable closure identity

Every qualifying range regenerates the 101-node DAG and requires byte-identical equality against certified KSQ-0.

Canonical `build-order.tsv` SHA-256:

`9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

`closure-status.env` remains snapshot `20260829T022000Z`, status `COMPLETE`, sources `101`, unresolved `0`, build ordered `101`.

## Maintained range 001-020

- run `33546093974`, job `99983826266`;
- result **PASS**;
- artifact `9818465016`;
- digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`;
- sources `20/20 PASS`;
- new/accumulated DEBs `103/103`;
- native successful `.build` files `20/20`;
- HTTP/HTTPS acquisition lines `0`;
- scoped AppArmor denials `0`.

Checkpoint internal identities:

- `new-debs.sha256`: `b0be04014893808a79aaea514e2a5c4bc968b5c9c9769d8d7ea6cae7992b01f9`;
- `build-manifest.tsv`: `ff87f96c85bc4ba1553f16b3700cf701eca04e9b749a1c739bb1088cceb3485b`.

## Maintained range 021-040

- run `33561782526`, job `100035734787`;
- result **PASS**;
- artifact `9824689982`;
- digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`;
- exact 001-020 checkpoint verified before order 21;
- sources `20/20 PASS`;
- new DEBs `89`;
- accumulated DEBs `192`;
- native successful `.build` files `20/20`;
- HTTP/HTTPS acquisition lines `0`;
- scoped AppArmor denials `0`.

Checkpoint internal identities:

- `new-debs.sha256`: `3924d0151581a53f505ca8cd0a615b4ffee9c246afeabec003633905db159bfa`;
- `build-manifest.tsv`: `6e121efdeb62b8c0c6c48ae14f60e41e452e16fe177f03536f1c2677848b111a`.

## Historical 041-060 attempt and root cause

The earlier r1 range reached orders 41 and 42 successfully but failed at order 43 `kpipewire` during dependency installation because the local slice did not contain `dbus-user-session=1.16.2-2ubuntu4`.

Investigation proved this was not a `kpipewire` defect. The r1 slice closure had been computed with explicit `--no-install-recommends`, while the real sbuild/APT path used normal default Recommends semantics.

Controlled A/B run `33729123389` proved:

- no-Recommends closure: 1541 binary objects / 704826504 bytes;
- default-Recommends closure: 1783 binary objects / 785219274 bytes.

The corrected r2 slice was therefore rematerialized as the complete default-Recommends generic-amd64 closure. No one-off package injection, `kpipewire` patch or sbuild policy override was accepted.

Detailed evidence: `docs/validation/AURORA_KSQ_1_SNAPSHOT_R2_RANGE_041_043.md`.

## Maintained range 041-043 r2

Order 43 was first retested in isolation against r2 and passed. Because the slice changed, the affected range was then rebuilt from the exact 001-040 chain.

Canonical regression:

- commit `67ca6afd74373b2d52bcf40fd6321ec9fe615ba3`;
- run `33753437984`;
- job `100642085362`;
- result **PASS**;
- artifact `9892762100`;
- digest `sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0`.

Results:

- order 41 `kf6-kunitconversion`: PASS / 4 DEBs;
- order 42 `knighttime`: PASS / 3 DEBs;
- order 43 `kpipewire`: PASS / 6 DEBs;
- new DEBs `13`;
- accumulated DEBs `205`;
- command RC `0`;
- tee RC `0`;
- relevant AppArmor denials `0`;
- external HTTP/HTTPS build acquisition `0`;
- build-manifest SHA-256 `e4311aeba5c7856ac2c0ff803c9adc2fdcb63adb104d1a8f2707a1fc45696ab1`;
- `new-debs.sha256` file SHA-256 `d5e6cbd51cac0ac2d2dca953722ccbd1a43beb3c981766f683ae69ace539105c`.

The maintained candidate is now qualified through order 43 on r2.

## Checkpoint chain for 044-060

The next workflow must restore exactly these accepted artifacts before order 44:

1. 001-020: artifact `9818465016`;
2. 021-040: artifact `9824689982`;
3. 041-043 r2: artifact `9892762100`.

The restorer must verify PASS state, exact expected order ranges, internal manifest identities and every DEB checksum, require no filename/package overlap and reconstruct exactly 205 accumulated DEBs before order 44 starts.

Historical r1 041/42 checkpoint bytes may not be substituted for the accepted r2 041-043 regression.

The next build range is exactly **044-060**. It must not rerun 041-043 blindly and must not advance into 061-080.

## KWallet PAM local-only boundary

The legacy remote/root-mode KWallet validator is not accepted for the current contract.

Replacement implementation:

`scripts/ci/validate-ksq-1-kwallet-pam-local.sh`

It remains **IMPLEMENTED / NOT YET QUALIFIED**. The validator is scheduled for the candidate chain that reaches `kwallet-pam`; it must use the same r2 local-only unshare environment and exact rebuilt KWallet/PAM packages.

061-080 remains blocked until:

1. 044-060 completes and the entire 041-060 segment is closed on r2; and
2. the local KWallet validator passes on the appropriate rebuilt candidate packages.

## Reproducibility boundary

The 95+6 contract remains unchanged:

- 95 unaffected nodes require exact prepared-source identity and byte-identical independent DEBs;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild evidence against the final patched candidate.

## Current state

- source/DAG identity: **UNCHANGED / KSQ-0 CLOSED**;
- upstream Ubuntu snapshot: **20260829T022000Z**;
- canonical local slice: **20260829T022000Z-r2 / INDEPENDENTLY VALIDATED**;
- maintained 001-020: **PASS**;
- maintained 021-040: **PASS**;
- maintained 041-043 r2: **PASS**;
- accumulated candidate through order 43: **205 DEBs**;
- maintained 044-060 r2: **NEXT / NOT YET QUALIFIED**;
- KWallet PAM local-only validator: **IMPLEMENTED / NOT YET QUALIFIED**;
- 061-080 promotion: **BLOCKED**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
