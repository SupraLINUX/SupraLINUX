# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This file records the current engineering state of KSQ-1. It is not an acceptance record and does not authorize entry into KSQ-2.

## Fixed prerequisite

KSQ-0 remains **CERTIFIED / CLOSED**.

KSQ-1 consumes:

- the certified 101-source DAG closure;
- Ubuntu Resolute snapshot `20260829T022000Z`;
- exact package/source identities established by KSQ-0;
- unprivileged `mmdebstrap --mode=unshare` and `sbuild --chroot-mode=unshare` isolation.

KSQ-2 remains **BLOCKED** and C4.1 remains **PAUSED**.

## Selected execution infrastructure

The selected KSQ execution host is GitHub-hosted:

`runs-on: ubuntu-26.04`

GitHub still labels this runner image/service **Public Preview** as of 2026-09-01. Ubuntu 26.04 LTS itself is stable.

This preview status applies to external CI infrastructure, not to software shipped in SupraLINUX. The project rule against beta/RC/git/experimental product software therefore does not automatically reject the runner. Instead, SupraLINUX accepts the hosted runner only through empirical qualification of the exact behavior KSQ needs.

The hosted architecture has now passed:

- host Ubuntu 26.04 identity and AppArmor qualification;
- pinned Ubuntu 26.04 container execution;
- uidmap normalization and namespace preflight;
- local-only snapshot consumer gate;
- real local-only `mmdebstrap`;
- real local-only `sbuild`;
- certified DAG source order 001 end-to-end.

Every formal KSQ job must record the GitHub runner image/version, kernel, Docker version and AppArmor state and rerun the required infrastructure invariants. A runner-image/toolchain/security change that affects those invariants is a regression trigger; previous PASS is not transferred blindly.

Pinned builder userspace:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

The builder uses `scripts/ci/ksq-docker-builder.py` so Docker's default `/proc` masks are removed only where required for nested unshare procfs, while sensitive `/sys` masks are retained. The outer container remains non-privileged, without `CAP_SYS_ADMIN`, under scoped AppArmor, and with network mode `none` for package/build work.

## Durable certified snapshot input

The snapshot slice is published, independently validated, and repository-pinned:

- snapshot `20260829T022000Z`;
- Release ID `380209318`;
- tag `ksq-snapshot-20260829T022000Z`;
- asset ID `538944111`;
- asset `aurora-ubuntu-snapshot-20260829T022000Z-amd64.tar`;
- bytes `973148160`;
- SHA-256 `8dc9087b53e90c085333644ffdb828b87ce0af6cd61ec5f1d516fe35e80529e7`;
- manifest asset ID `538944115`;
- manifest SHA-256 `f3b30842f18fdaf868af74bbb3c6309f90e6b15a1fed2fe29bfd36a633536afd`;
- repository status `INDEPENDENTLY_VALIDATED` in `scripts/ci/aurora-ksq-snapshot-release.env`.

Certified closure represented by the slice:

- 244 binary/version seeds;
- 1541 binary `.deb` objects;
- `704826504` binary bytes;
- 301 Ubuntu source objects;
- 4 Debian source objects.

Live current Ubuntu archive resolution is not acceptable for the KSQ package identity contract.

## Local-only consumer qualification

Workflow:

`.github/workflows/ksq-github-hosted-local-snapshot-gate.yml`

Qualifying commit `94f3e0b03e17704828cfb0325b744fffe32911a9`.

Run / job:

- run `33528728431`;
- job `99926115300`;
- result **SUCCESS**.

Artifact:

- ID `9808961368`;
- digest `sha256:8216edf709c99aa39148f3c788f7ae2d6be26b91efa4aaefa36280f772ba99ef`;
- inner evidence TAR SHA-256 `1780e351dbbd2b5ad002a81e178a3c67536f19627d6951a38962fe947fbea1b9`.

With container networking physically absent, the gate proved exact Release identity, full slice validation, 244 exact candidates, exact 1541-object closure, local-only APT/toolchain, namespace preflight, `mmdebstrap` PASS, `sbuild` PASS and zero scoped AppArmor denials.

## Real source DAG 001 qualification

Certified DAG order 001:

- source `kf6-extra-cmake-modules`;
- packaging base `6.29.0-0ubuntu1`;
- decision `rebuild`;
- SupraLINUX version `6.29.0-0ubuntu1~supra26.04.1`.

Workflow:

`.github/workflows/ksq-source-001-local-slice-probe.yml`

Qualifying commit `3072e7945811d9ce226551fd9fab3ffbb6e5a5d2`.

Run / job:

- run `33531933805`;
- job `99936944948`;
- result **SUCCESS**.

Artifact:

- ID `9810147299`;
- digest `sha256:997074576b9ef9b9d0743d931e061d222f6911fde53b809ef223e8aa4f354125`;
- inner evidence TAR SHA-256 `03f9ba7eeeaaf16ddab8345ec31da97e55c9195ae1518e5dd2c8b2ae13c12912`.

The run proved local source acquisition, exact `.dsc` identity, maintained SupraLINUX source preparation, local-only buildd creation and successful `sbuild`, producing:

- `extra-cmake-modules_6.29.0-0ubuntu1~supra26.04.1_amd64.deb`;
- `extra-cmake-modules-doc_6.29.0-0ubuntu1~supra26.04.1_all.deb`.

`Acquire::Source-Symlinks=false` is required for local `file:` source acquisition because Resolute APT defaults this option to true and may otherwise represent source objects as symlinks. The option keeps acquisition/checksum verification inside APT while materializing ordinary files for the existing source-preparation contract.

## Formal KSQ-1 migration

The next task is to migrate the maintained KSQ-1 range builder from the legacy remote Snapshot Service assumptions to the qualified local-slice architecture.

Legacy points that must be removed from the formal path:

- `prepare-ksq-1-runner.sh` using the runner's generic active APT configuration;
- `prepare-ksq-1-build-environment.sh` pointing `mmdebstrap` at `https://snapshot.ubuntu.com/...`;
- `fetch-prepare-ksq-1-source.sh` relying on the old remote/generated metadata contract and implicit source symlink behavior.

Migration must preserve the current 101-source DAG, packaging decisions, overrides/adaptations, binary checkpoint chaining and 95+6 reproducibility contract. It must not change package versions merely to simplify CI.

The first maintained regression after migration is source range 001-020. The existing source-001 PASS is the reference for validating that migration before proceeding farther through the DAG.

## Reproducibility contract

KSQ-1 retains the 95+6 reproducibility contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against an independent reference build;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final patched candidate.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- published snapshot Release: **PUBLISHED / INDEPENDENTLY VALIDATED / PINNED**;
- GitHub-hosted Ubuntu 26.04 execution architecture: **QUALIFIED / SELECTED**;
- hosted local-only consumer gate: **PASS**;
- hosted real source DAG 001 local-only: **PASS**;
- formal local-slice KSQ-1 workflow migration: **NEXT**;
- complete 101-source candidate under final local-slice contract: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
