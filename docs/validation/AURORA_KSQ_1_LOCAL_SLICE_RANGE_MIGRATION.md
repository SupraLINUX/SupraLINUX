# Aurora KSQ-1 maintained local-slice range migration

Status: **001-040 PASS — 041-060 IN PROGRESS**

This document tracks migration of the maintained KSQ-1 range builder from legacy remote Snapshot Service assumptions to the published local snapshot slice.

It does not certify KSQ-1 by itself. KSQ-0 remains **CERTIFIED / CLOSED** and its decisions are consumed unchanged.

## Migration design

The migration deliberately keeps `scripts/ci/build-ksq-1-range.sh` as the range/build engine. Local-slice helpers provide its environment instead of creating a second package-build implementation.

Maintained helpers:

- `scripts/ci/restore-ksq-0-certified-evidence.py` restores canonical KSQ-0 evidence from the exact embedded artifact ZIP inside the immutable snapshot slice and verifies its certified digest/build-order identity;
- `scripts/ci/prepare-ksq-1-local-apt-metadata.sh` recreates the existing KSQ APT metadata interface from signed `file:` sources only;
- `scripts/ci/prepare-ksq-1-local-build-environment.sh` creates the buildd tarball with local `mmdebstrap` and writes the `sbuild` unshare bind configuration for the snapshot;
- `scripts/ci/prepare-ksq-1-local-runner.sh` verifies outer security/network invariants, installs the toolchain from the local slice, restores closed KSQ-0 source-audit evidence, regenerates the closure locally and requires byte-identical certified closure/build order;
- `scripts/ci/run-ksq-1-local-range.sh` invokes the existing range builder with the local `SBUILD_CONFIG` contract.

KSQ-0's source-audit workflow is **not rerun**. The immutable slice contains `provenance/github-artifact-9708738867.zip`, whose SHA-256 remains the certified `5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`. The local runner restores those already-certified bytes rather than consulting Debian Snapshot again.

Local source acquisition uses the supported Resolute APT option `Acquire::Source-Symlinks=false` so the maintained source-preparation code receives regular files from the signed `file:` repository.

## Stable closure identity

Every qualifying range regenerates the 101-node DAG from the signed local slice and requires byte-identical equality against certified KSQ-0.

Canonical `build-order.tsv` SHA-256:

`9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

`closure-status.env` remains snapshot `20260829T022000Z`, status `COMPLETE`, sources `101`, unresolved `0`, build ordered `101`.

## Maintained range 001-005

- commit `0e9a009b23a91a3eb6575fc8cde0968db6dd47bf`;
- run `33534104089`;
- job `99944060131`;
- result **SUCCESS**;
- artifact `9811368088`;
- digest `sha256:4ec26fcd935120b190b08621b0443a0d3fee13e8194b77e9c43b62750393d948`;
- sources `5`;
- DEBs `12`;
- AppArmor denials `0`;
- HTTP/HTTPS package/source acquisitions `0`.

This proved the maintained range builder could run unchanged against the local-slice environment, including KDE-adjacent backports and Debian `wayland-protocols` restored from certified KSQ-0 evidence.

## Maintained range 001-020

- commit `05615aa0bfca4c6bee5a0d520f7332cb6bc5506e`;
- run `33546093974`;
- job `99983826266`;
- result **SUCCESS**;
- artifact `9818465016`;
- artifact bytes `163328618`;
- digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`;
- sources `20/20 PASS`;
- new/accumulated DEBs `103/103`;
- native `.build` logs successful `20/20`;
- container RC `0`, tee RC `0`;
- AppArmor denials `0`;
- HTTP/HTTPS package/source acquisitions `0`.

The 001-020 checkpoint is pinned by artifact ID plus internal identities:

- `new-debs.sha256`: `b0be04014893808a79aaea514e2a5c4bc968b5c9c9769d8d7ea6cae7992b01f9`;
- `build-manifest.tsv`: `ff87f96c85bc4ba1553f16b3700cf701eca04e9b749a1c739bb1088cceb3485b`.

## Maintained range 021-040

The second formal-sized chunk has now passed using the exact 001-020 checkpoint.

- commit `d8fa7e6e26f002bc6ca94d04bbda8097e19607b6`;
- run `33561782526`;
- job `100035734787`;
- result **SUCCESS**;
- artifact `9824689982`;
- artifact bytes `12667773`;
- digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`.

Before building order 21, the workflow downloaded artifact `9818465016` from run `33546093974` by exact ID and verified:

- range status PASS for 001-020;
- 103 checkpoint DEBs;
- exact `new-debs.sha256` identity;
- exact build-manifest identity;
- SHA-256 of every checkpoint DEB.

The 021-040 artifact was then independently audited and proves:

- sources `20/20 PASS`;
- orders exactly `21..40`;
- new DEBs `89`;
- accumulated DEBs `192`;
- native `.build` logs successful `20/20`;
- new DEB checksum entries `89/89`, all verified;
- container RC `0`, tee RC `0`;
- AppArmor denials `0`;
- HTTP/HTTPS package/source acquisition lines `0`;
- regenerated build-order SHA-256 still `9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`.

The 021-040 checkpoint is pinned by:

- artifact ID `9824689982` / digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`;
- `new-debs.sha256`: `3924d0151581a53f505ca8cd0a615b4ffee9c246afeabec003633905db159bfa`;
- `build-manifest.tsv`: `6e121efdeb62b8c0c6c48ae14f60e41e452e16fe177f03536f1c2677848b111a`.

## Maintained range 041-060

The next run restores both exact previous artifacts, verifies both independently, requires no overlapping DEB filenames, and requires exactly 192 accumulated DEBs before order 41 starts.

- commit `a5630f5299ca58479ad062989480a2202fbdded9`;
- run `33572528721`;
- state at this documentation update: **IN PROGRESS**.

No 041-060 PASS is recorded until the run and its artifact are audited.

## KWallet PAM local-only boundary

The legacy `scripts/ci/validate-ksq-1-kwallet-pam.sh` is not acceptable for the new contract because it creates its test rootfs directly from the remote Ubuntu Snapshot Service and uses a root-mode path.

A replacement implementation now exists:

`scripts/ci/validate-ksq-1-kwallet-pam-local.sh`

Its intended contract is:

- run inside the same scoped, networkless builder;
- no outer `CAP_SYS_ADMIN`;
- `mmdebstrap --mode=unshare`;
- signed local `file:` snapshot only;
- exact built `libpam-kwallet-common` and `libpam-kwallet5` DEBs supplied through the supported `mmdebstrap --include` local-DEB mechanism;
- `file-mirror-automount` for local repository and DEB visibility;
- `mmdebstrap --unshare-helper` for operations inside the shifted-ownership rootfs;
- existing source-level dependency/substvar assertions retained;
- PAM registration in `common-auth` and `common-session` required;
- HTTP/HTTPS acquisition forbidden.

This validator is **implemented but not yet qualified**. It will be tested only against the newly chained candidate once the build reaches the `kwallet-pam` source in the 061-080 phase.

## Current state

- source 001 isolated local-slice proof: **PASS**;
- maintained local-slice range 001-005: **PASS**;
- maintained local-slice range 001-020: **PASS**;
- maintained local-slice range 021-040: **PASS**;
- maintained local-slice range 041-060: **IN PROGRESS**;
- accumulated certified-path candidate through order 40: **192 DEBs**;
- KWallet PAM local-only validator: **IMPLEMENTED / NOT YET QUALIFIED**;
- 061-080 promotion: **BLOCKED ON 041-060 PASS + KWallet LOCAL VALIDATION**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
