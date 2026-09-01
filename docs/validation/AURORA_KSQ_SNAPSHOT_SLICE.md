# Aurora KSQ certified snapshot slice

Status: **PUBLISHED / INDEPENDENTLY VALIDATED / REPOSITORY-PINNED**

This document records the durable byte-preserved archive slice for Aurora snapshot `20260829T022000Z`. It removes live Ubuntu Snapshot Service transport from the KSQ build critical path without changing identities certified by KSQ-0.

The snapshot engineering input is accepted. KSQ-1 itself remains **ACTIVE / NOT CERTIFIED**.

## Certified origin

Canonical KSQ-0 closure evidence:

- snapshot `20260829T022000Z`;
- run `33231879994`;
- artifact `9708738867`;
- digest `sha256:5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`;
- closure `COMPLETE`;
- 101 source nodes;
- unresolved dependency/source decisions `0`.

Canonical size/identity evidence:

- run `33455898813`;
- artifact `9781553137`;
- digest `sha256:39672453ba364d81cfa8621cd060201f845a6d940fb4ac04d45aa25be1ce0e19`;
- 244 certified binary/version seeds;
- 1541 binary `.deb` objects;
- `704826504` binary bytes;
- 301 Ubuntu source objects / `212283819` bytes;
- 4 Debian source objects / `161155` bytes;
- conservative raw upper bound `1001129661` bytes (`0.9324 GiB`).

The live-archive control run `33456358421` already proved archive drift by showing that certified versions of `freerdp3-dev`, `libssl-dev` and `libwinpr3-dev` were no longer available live. Current-live resolution cannot replace this snapshot.

## Published immutable engineering Release

- Release ID `380209318`;
- tag `ksq-snapshot-20260829T022000Z`;
- asset ID `538944111`;
- asset `aurora-ubuntu-snapshot-20260829T022000Z-amd64.tar`;
- exact bytes `973148160`;
- SHA-256 `8dc9087b53e90c085333644ffdb828b87ce0af6cd61ec5f1d516fe35e80529e7`;
- manifest asset ID `538944115`;
- manifest SHA-256 `f3b30842f18fdaf868af74bbb3c6309f90e6b15a1fed2fe29bfd36a633536afd`.

Repository pin:

`scripts/ci/aurora-ksq-snapshot-release.env`

with:

`AURORA_KSQ_SNAPSHOT_RELEASE_STATUS=INDEPENDENTLY_VALIDATED`

The Release is an engineering reproducibility input, not an Aurora product release.

## Trust model

The slice is byte-preserving. It is not a regenerated repository and introduces no local archive-signing key.

Ubuntu trust remains:

`Ubuntu archive key -> signed InRelease -> Packages/Sources identity -> retained object checksum`

The slice retains original signed metadata, the exact selected Ubuntu pool objects, the four certified Debian `wayland-protocols 1.48-1` source objects, manifests/provenance and deterministic local APT source configuration.

## Consumer path

Deterministic root:

`/opt/supralinux/archive/20260829T022000Z/`

APT contract inside the pinned Resolute builder:

```text
Types: deb deb-src
URIs: file:/opt/supralinux/archive/20260829T022000Z/ubuntu
Suites: resolute resolute-updates resolute-security resolute-backports
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no

Types: deb-src
URIs: file:/opt/supralinux/archive/20260829T022000Z/ubuntu
Suites: stonking
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no
```

Stonking remains source-only.

## Local-only consumer qualification

Workflow `.github/workflows/ksq-github-hosted-local-snapshot-gate.yml`:

- commit `94f3e0b03e17704828cfb0325b744fffe32911a9`;
- run `33528728431`;
- job `99926115300`;
- result **SUCCESS**;
- artifact `9808961368`;
- artifact digest `sha256:8216edf709c99aa39148f3c788f7ae2d6be26b91efa4aaefa36280f772ba99ef`;
- inner evidence TAR SHA-256 `1780e351dbbd2b5ad002a81e178a3c67536f19627d6951a38962fe947fbea1b9`.

With network mode `none`, that gate proved:

1. exact repository pin before extraction;
2. safe archive layout and full validator PASS;
3. all 244 certified candidates exact;
4. exact empty-status closure: 1541 objects / `704826504` bytes;
5. package transport exclusively `file:`;
6. toolchain installation from the slice;
7. namespace preflight;
8. local-only `mmdebstrap` PASS;
9. local-only `sbuild` PASS;
10. functional procfs inside the build;
11. zero scoped AppArmor denials.

## Real source-node proof

Workflow `.github/workflows/ksq-source-001-local-slice-probe.yml`:

- final commit `3072e7945811d9ce226551fd9fab3ffbb6e5a5d2`;
- run `33531933805`;
- job `99936944948`;
- result **SUCCESS**;
- artifact `9810147299`;
- digest `sha256:997074576b9ef9b9d0743d931e061d222f6911fde53b809ef223e8aa4f354125`.

Certified source identity:

- `kf6-extra-cmake-modules`;
- packaging base `6.29.0-0ubuntu1`;
- prepared version `6.29.0-0ubuntu1~supra26.04.1`.

The run acquired the exact source objects from the local signed `stonking` source index and produced successful local-only DEBs.

For source acquisition, Resolute APT's supported `Acquire::Source-Symlinks=false` option is part of the maintained local contract. APT defaults it to true and may otherwise represent local source archives as symlinks. Disabling source symlinks preserves APT metadata/checksum verification while giving the source-preparation pipeline ordinary files.

## Execution-host policy

The selected execution infrastructure is GitHub-hosted `ubuntu-26.04` plus the pinned Resolute builder image and the qualified selective Docker/AppArmor contract.

GitHub's runner image/service remains Public Preview as of 2026-09-01. That is external CI infrastructure, not product software. SupraLINUX accepts it only through explicit empirical qualification and per-job invariant checks. A runner/security/tool change that invalidates a required invariant triggers regression; it does not change the snapshot bytes or trust identity.

## Current state

- certified snapshot identity: **FIXED**;
- durable Release asset: **PUBLISHED**;
- independent publication re-download/validation: **PASS**;
- repository SHA-256/byte pin: **COMMITTED**;
- local-only consumer gate: **PASS**;
- local-only mmdebstrap regression: **PASS**;
- local-only sbuild smoke: **PASS**;
- real source DAG 001 local-slice proof: **PASS**;
- GitHub-hosted Ubuntu 26.04 execution infrastructure: **QUALIFIED / SELECTED**;
- formal 101-source local-slice migration: **NEXT**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
