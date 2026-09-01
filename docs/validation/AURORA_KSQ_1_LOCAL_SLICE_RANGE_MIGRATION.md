# Aurora KSQ-1 maintained local-slice range migration

Status: **001-020 PASS — 021-040 NEXT**

This document tracks migration of the maintained KSQ-1 range builder from legacy remote Snapshot Service assumptions to the published local snapshot slice.

It does not certify KSQ-1 by itself. KSQ-0 remains **CERTIFIED / CLOSED** and its decisions are consumed unchanged.

## Migration design

The migration deliberately keeps `scripts/ci/build-ksq-1-range.sh` as the range/build engine. New local-slice helpers provide its environment instead of creating a second package-build implementation.

Maintained helpers:

- `scripts/ci/restore-ksq-0-certified-evidence.py` restores canonical KSQ-0 evidence from the exact embedded artifact ZIP inside the immutable snapshot slice and verifies its certified digest/build-order identity;
- `scripts/ci/prepare-ksq-1-local-apt-metadata.sh` recreates the existing KSQ APT metadata interface from signed `file:` sources only;
- `scripts/ci/prepare-ksq-1-local-build-environment.sh` creates the buildd tarball with local `mmdebstrap` and writes the `sbuild` unshare bind configuration for the snapshot;
- `scripts/ci/prepare-ksq-1-local-runner.sh` verifies outer security/network invariants, installs the toolchain from the local slice, restores closed KSQ-0 source-audit evidence, regenerates the closure locally and requires byte-identical certified closure/build order;
- `scripts/ci/run-ksq-1-local-range.sh` invokes the existing range builder with the local `SBUILD_CONFIG` contract.

KSQ-0's source-audit workflow is **not rerun**. The immutable slice contains `provenance/github-artifact-9708738867.zip`, whose SHA-256 remains the certified `5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`. The local runner restores the already-certified source-audit bytes from that object rather than consulting Debian Snapshot again.

Local source acquisition in `fetch-prepare-ksq-1-source.sh` uses `Acquire::Source-Symlinks=false`, the supported Resolute APT option required to materialize ordinary files from the signed `file:` source repository.

## Maintained range 001-005 qualification

Workflow: `.github/workflows/ksq-1-local-range-probe.yml`

- commit `0e9a009b23a91a3eb6575fc8cde0968db6dd47bf`;
- run `33534104089`;
- job `99944060131`;
- result **SUCCESS**;
- artifact ID `9811368088`;
- artifact digest `sha256:4ec26fcd935120b190b08621b0443a0d3fee13e8194b77e9c43b62750393d948`;
- sources `5`;
- DEBs `12`;
- AppArmor denials `0`;
- HTTP/HTTPS package/source acquisition `0`.

This initial gate proved the existing maintained range builder could run unchanged against the local-slice environment, including the KDE-adjacent backports and the Debian `wayland-protocols` source restored from certified KSQ-0 evidence.

## Maintained range 001-020 qualification

The first formal-sized chunk has now passed the same local-slice path.

Workflow: `.github/workflows/ksq-1-local-range-probe.yml`

- commit `05615aa0bfca4c6bee5a0d520f7332cb6bc5506e`;
- run `33546093974`;
- job `99983826266`;
- result **SUCCESS**;
- artifact ID `9818465016`;
- artifact name `aurora-ksq-1-local-range-001-020`;
- artifact bytes `163328618`;
- artifact digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`.

Observed runner:

- Ubuntu 26.04 LTS;
- `ImageOS=ubuntu26`;
- `ImageVersion=20260824.116.1`;
- kernel `7.0.0-1012-azure`;
- Docker `29.4.2`.

The locally regenerated certified build order remained byte-identical to KSQ-0:

`SHA-256 = 9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

`closure-status.env` remained:

- snapshot `20260829T022000Z`;
- status `COMPLETE`;
- sources `101`;
- unresolved `0`;
- build ordered `101`.

The range evidence proves:

- `AURORA_KSQ_1_RANGE_STATUS=PASS`;
- first order `1`;
- last order `20`;
- sources `20`;
- new DEBs `103`;
- accumulated DEBs `103`;
- container RC `0`;
- `tee` RC `0`;
- 20/20 build-manifest rows `PASS`;
- 20/20 native `.build` logs contain `Status: successful`;
- 20/20 `build-status.env` records are `PASS`;
- scoped AppArmor denied lines `0`;
- actual APT `Get/Hit/Ign/Err` HTTP/HTTPS acquisition lines inside the package builder `0`;
- remote fallback remains `forbidden`.

Orders 1-20 are:

| Order | Source | Packaging base | Supra version | Decision | DEBs | Result |
|---:|---|---|---|---|---:|---|
| 1 | `kf6-extra-cmake-modules` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 2 | PASS |
| 2 | `plasma-wayland-protocols` | `1.21.0-1` | `1.21.0-1~supra26.04.1` | backport | 1 | PASS |
| 3 | `qtkeychain` | `0.17.0-1` | `0.17.0-1~supra26.04.1` | backport | 5 | PASS |
| 4 | `wayland-protocols` | `1.48-1` | `1.48-1~supra26.04.1` | backport | 1 | PASS |
| 5 | `kf6-attica` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 3 | PASS |
| 6 | `kf6-bluez-qt` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 5 | PASS |
| 7 | `kf6-breeze-icons` | `4:6.29.0-0ubuntu2` | `4:6.29.0-0ubuntu2~supra26.04.1` | rebuild | 6 | PASS |
| 8 | `kf6-karchive` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 4 | PASS |
| 9 | `kf6-kcodecs` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 4 | PASS |
| 10 | `kf6-kconfig` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 9 | PASS |
| 11 | `kf6-kcoreaddons` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 5 | PASS |
| 12 | `kf6-kdbusaddons` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 5 | PASS |
| 13 | `kf6-kglobalaccel` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 4 | PASS |
| 14 | `kf6-kguiaddons` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 6 | PASS |
| 15 | `kf6-kholidays` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 5 | PASS |
| 16 | `kf6-ki18n` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 8 | PASS |
| 17 | `kf6-kidletime` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 3 | PASS |
| 18 | `kf6-kirigami` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 19 | PASS |
| 19 | `kf6-kitemmodels` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 4 | PASS |
| 20 | `kf6-kitemviews` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 4 | PASS |

The 001-020 exit criteria for the first formal-sized chunk are therefore **100% satisfied**.

## Remaining migration boundary

The formal full-build workflow is not yet switched wholesale because later chunks have not yet completed equivalent local-slice regressions. In addition, `scripts/ci/validate-ksq-1-kwallet-pam.sh`, executed after chunk 061-080, still creates its validation rootfs directly from the remote Ubuntu Snapshot Service. That validator must be migrated and independently proven local-only before chunk 061-080 can be promoted.

Next gate:

1. restore the exact 001-020 binary checkpoint from run `33546093974`;
2. run orders 021-040 through the same local-slice builder;
3. require exact DAG identity, complete PASS evidence, no remote acquisition, and zero scoped AppArmor denials;
4. only then proceed to 041-060.

## Current state

- source 001 isolated local-slice proof: **PASS**;
- maintained local-slice range 001-005: **PASS**;
- maintained local-slice range 001-020: **PASS**;
- maintained local-slice range 021-040: **NEXT**;
- KWallet PAM local-only validator migration: **REQUIRED BEFORE 061-080 PROMOTION**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
