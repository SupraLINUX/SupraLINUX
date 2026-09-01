# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This file records the current engineering state of KSQ-1. It is not an acceptance record and does not authorize entry into KSQ-2.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Fixed contract

KSQ-1 consumes:

- the certified 101-source DAG closure;
- Ubuntu Resolute snapshot `20260829T022000Z`;
- exact package/source identities established by KSQ-0;
- unprivileged `mmdebstrap --mode=unshare` and `sbuild --chroot-mode=unshare` isolation;
- the maintained 95+6 reproducibility contract.

No KSQ-0 decision is reopened by the KSQ-1 local-slice migration.

## Selected execution infrastructure

The selected KSQ execution host is GitHub-hosted `ubuntu-26.04`.

GitHub still labels this runner image/service **Public Preview** as of 2026-09-01. Ubuntu 26.04 LTS itself is stable. The preview status belongs to external CI infrastructure, not software shipped in SupraLINUX. The runner is accepted only through empirical, fail-closed qualification of the exact behavior KSQ requires.

Every KSQ job records/rechecks host Ubuntu identity, runner image metadata, kernel, Docker and AppArmor state. Relevant infrastructure changes trigger regression rather than inheriting a prior PASS.

Pinned builder userspace:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

The builder uses `scripts/ci/ksq-docker-builder.py`: outer container non-privileged, no outer `CAP_SYS_ADMIN`, scoped AppArmor, package/build network mode `none`, Docker `/proc` masking adjusted only as required for nested unshare procfs while sensitive `/sys` masks remain.

## Durable certified snapshot input

Published, independently validated and repository-pinned snapshot:

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

The slice represents 244 certified binary/version seeds, 1541 binary `.deb` objects / `704826504` bytes, 301 Ubuntu source objects and 4 Debian source objects. Live archive resolution is not accepted for the package identity contract.

## Infrastructure and source-001 qualification

Local-only consumer gate:

- workflow `.github/workflows/ksq-github-hosted-local-snapshot-gate.yml`;
- run `33528728431`, job `99926115300`;
- result **SUCCESS**;
- artifact `9808961368`, digest `sha256:8216edf709c99aa39148f3c788f7ae2d6be26b91efa4aaefa36280f772ba99ef`.

It proves exact Release identity, full slice validation, 244 exact candidates, exact 1541-object closure, local-only APT/toolchain, namespace preflight, `mmdebstrap` PASS, `sbuild` PASS and zero scoped AppArmor denials with builder networking absent.

Real source DAG 001:

- source `kf6-extra-cmake-modules`, base `6.29.0-0ubuntu1`, Supra version `6.29.0-0ubuntu1~supra26.04.1`;
- workflow `.github/workflows/ksq-source-001-local-slice-probe.yml`;
- run `33531933805`, job `99936944948`;
- result **SUCCESS**;
- artifact `9810147299`, digest `sha256:997074576b9ef9b9d0743d931e061d222f6911fde53b809ef223e8aa4f354125`.

Local source acquisition uses `Acquire::Source-Symlinks=false`, the supported APT option needed to materialize ordinary files from the signed `file:` source repository while retaining APT checksum verification.

## Maintained local-slice range migration

The maintained build engine remains `scripts/ci/build-ksq-1-range.sh`. The migration supplies it through local-slice helpers rather than forking a second implementation.

Important properties already proven:

- KSQ-0 evidence is restored from the exact certified artifact ZIP embedded in the immutable slice;
- the DAG is regenerated from signed local metadata and must be byte-identical to certified KSQ-0;
- canonical `build-order.tsv` SHA-256 remains `9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`;
- package/source transport inside the builder is `file:` only;
- prior range artifacts are restored by exact artifact/run identity and their internal DEB/checkpoint hashes are verified before use.

### Range 001-020

- commit `05615aa0bfca4c6bee5a0d520f7332cb6bc5506e`;
- run `33546093974`, job `99983826266`;
- **SUCCESS**;
- artifact `9818465016`, digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`;
- sources `20/20 PASS`;
- new/accumulated DEBs `103/103`;
- native successful `.build` files `20/20`;
- HTTP/HTTPS acquisition lines `0`;
- scoped AppArmor denials `0`.

### Range 021-040

- commit `d8fa7e6e26f002bc6ca94d04bbda8097e19607b6`;
- run `33561782526`, job `100035734787`;
- **SUCCESS**;
- artifact `9824689982`, digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`;
- exact 001-020 checkpoint verified before order 21;
- sources `20/20 PASS`;
- new DEBs `89`;
- accumulated DEBs `192`;
- native successful `.build` files `20/20`;
- all 89 new-DEB checksums verified;
- HTTP/HTTPS acquisition lines `0`;
- scoped AppArmor denials `0`.

### Range 041-060

- commit `a5630f5299ca58479ad062989480a2202fbdded9`;
- run `33572528721`;
- current state: **IN PROGRESS**.

Before order 41, this run has already successfully restored both exact prior artifacts, verified both checkpoint manifests and DEB hashes, proved no filename overlap, reconstructed exactly 192 accumulated DEBs and revalidated the immutable snapshot.

No PASS is recorded until the 20 builds and resulting artifact are audited.

## Checkpoint-chain hardening

`scripts/ci/restore-ksq-1-checkpoint-chain.py` is now the maintained fail-closed checkpoint restorer for later ranges. It validates contiguous order ranges, PASS status, expected internal manifest hashes, every DEB SHA-256, filename/package uniqueness and cumulative counts before reconstructing the accumulated DEB set. It was independently exercised against the real 001-020 and 021-040 artifacts and restored exactly 192 DEBs with zero overlap.

## KWallet PAM local-only validation

The legacy remote/root-mode KWallet validation is not accepted for the new contract.

Replacement:

`scripts/ci/validate-ksq-1-kwallet-pam-local.sh`

The replacement is implemented but **not yet qualified**. It will run inside the same scoped networkless builder after order 65 and requires:

- `mmdebstrap --mode=unshare`;
- signed local snapshot only;
- no outer `CAP_SYS_ADMIN`;
- exact rebuilt `libpam-kwallet-common` and `libpam-kwallet5`;
- exact rebuilt KWallet runtime quartet `kwallet6`, `libkf6wallet-data`, `libkf6wallet6`, `libkf6walletbackend6`;
- exact candidate versions inside the created rootfs;
- retained source-level compat/substvar assertions;
- `apt-get check`;
- PAM registration in `common-auth` and `common-session`;
- zero HTTP/HTTPS package acquisition.

The rebuilt KWallet runtime is intentionally included so a PAM validation cannot falsely PASS against stock snapshot KWallet packages.

## Reproducibility contract

KSQ-1 retains the 95+6 contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against an independent reference build;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final patched candidate.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- snapshot Release: **PUBLISHED / INDEPENDENTLY VALIDATED / PINNED**;
- GitHub-hosted Ubuntu 26.04 execution architecture: **QUALIFIED / SELECTED**;
- local-only consumer gate: **PASS**;
- source DAG 001 local-only: **PASS**;
- maintained 001-020: **PASS**;
- maintained 021-040: **PASS**;
- maintained 041-060: **IN PROGRESS**;
- accumulated candidate through order 40: **192 DEBs**;
- KWallet PAM local-only validator: **IMPLEMENTED / NOT YET QUALIFIED**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
