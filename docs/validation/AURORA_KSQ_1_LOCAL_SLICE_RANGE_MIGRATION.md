# Aurora KSQ-1 maintained local-slice range migration

Status: **001-005 PASS — 001-020 NEXT**

This document tracks migration of the maintained KSQ-1 range builder from legacy remote Snapshot Service assumptions to the published local snapshot slice.

It does not certify KSQ-1 by itself. KSQ-0 remains **CERTIFIED / CLOSED** and its decisions are consumed unchanged.

## Migration design

The migration deliberately keeps `scripts/ci/build-ksq-1-range.sh` as the range/build engine. New local-slice helpers provide its environment instead of creating a second package-build implementation.

New maintained helpers:

- `scripts/ci/restore-ksq-0-certified-evidence.py` — restores canonical KSQ-0 evidence from the exact embedded artifact ZIP inside the immutable snapshot slice and verifies its certified digest/build-order identity;
- `scripts/ci/prepare-ksq-1-local-apt-metadata.sh` — recreates the existing KSQ APT metadata interface from signed `file:` sources only;
- `scripts/ci/prepare-ksq-1-local-build-environment.sh` — creates the buildd tarball with local `mmdebstrap` and writes the `sbuild` unshare bind configuration for the snapshot;
- `scripts/ci/prepare-ksq-1-local-runner.sh` — verifies outer security/network invariants, installs the toolchain from the local slice, restores closed KSQ-0 source-audit evidence, regenerates the closure locally and requires byte-identical certified closure/build order;
- `scripts/ci/run-ksq-1-local-range.sh` — invokes the existing range builder with the local `SBUILD_CONFIG` contract.

KSQ-0's source-audit workflow is **not rerun**. The immutable slice contains `provenance/github-artifact-9708738867.zip`, whose SHA-256 remains the certified `5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`. The local runner restores the already-certified source-audit bytes from that object rather than consulting Debian Snapshot again.

Local source acquisition in `fetch-prepare-ksq-1-source.sh` uses `Acquire::Source-Symlinks=false`, the supported Resolute APT option required to materialize ordinary files from the signed `file:` source repository.

## Maintained range 001-005 qualification

Workflow:

`.github/workflows/ksq-1-local-range-probe.yml`

Commit:

`0e9a009b23a91a3eb6575fc8cde0968db6dd47bf`

Run / job:

- run `33534104089`;
- job `99944060131`;
- result **SUCCESS**.

Artifact:

- ID `9811368088`;
- name `aurora-ksq-1-local-range-001-005`;
- bytes `144032737`;
- GitHub digest `sha256:4ec26fcd935120b190b08621b0443a0d3fee13e8194b77e9c43b62750393d948`.

Observed hosted runner:

- Ubuntu 26.04 LTS;
- `ImageOS=ubuntu26`;
- `ImageVersion=20260824.116.1`;
- kernel `7.0.0-1012-azure`;
- Docker `29.4.2`;
- runc `1.4.3`.

The maintained runner regenerated the certified DAG from local signed APT metadata and required exact identity:

`build/ksq-0/build-order.tsv SHA-256 = 9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

This equals the canonical KSQ-0 `build-order.tsv` identity. `closure-status.env` also matched the certified KSQ-0 bytes.

The range result was:

- status `PASS`;
- sources `5`;
- new DEBs `12`;
- accumulated DEBs `12`;
- remote fallback `forbidden`;
- outer container RC `0`;
- pipeline `tee` RC `0`;
- scoped AppArmor denials `0`.

Source results:

| Order | Source | Packaging base | Supra version | Decision | DEBs | Result |
|---:|---|---|---|---|---:|---|
| 1 | `kf6-extra-cmake-modules` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 2 | PASS |
| 2 | `plasma-wayland-protocols` | `1.21.0-1` | `1.21.0-1~supra26.04.1` | backport | 1 | PASS |
| 3 | `qtkeychain` | `0.17.0-1` | `0.17.0-1~supra26.04.1` | backport | 5 | PASS |
| 4 | `wayland-protocols` | `1.48-1` | `1.48-1~supra26.04.1` | backport | 1 | PASS |
| 5 | `kf6-attica` | `6.29.0-0ubuntu1` | `6.29.0-0ubuntu1~supra26.04.1` | rebuild | 3 | PASS |

Every generated native `.build` records `Status: successful`. No actual `Get/Hit/Ign/Err` acquisition line used HTTP/HTTPS inside the package builder.

Order 4 is especially important: `wayland-protocols 1.48-1` was built from the Debian source objects restored from the certified KSQ-0 evidence embedded in the slice, not re-downloaded from Debian Snapshot.

## Exit criterion for formal workflow promotion

Before replacing the first formal `001-020` chunk, run the same maintained local-slice path for orders 001-020 and require:

1. exact regenerated 101-node certified build order;
2. all orders 001-020 PASS;
3. checkpoint DEBs preserved and internally consistent;
4. no remote package/source acquisition;
5. outer host/container security invariants PASS;
6. zero scoped AppArmor denials;
7. artifact evidence successfully preserved.

Only after 001-020 passes is the formal `.github/workflows/ksq-1-full-builds.yml` first chunk migrated. Later chunks remain gated by their own incremental regressions.

## Current state

- source 001 isolated local-slice proof: **PASS**;
- maintained local-slice range 001-005: **PASS**;
- maintained local-slice range 001-020: **NEXT**;
- formal 001-020 workflow promotion: **BLOCKED ON 001-020 PASS**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
