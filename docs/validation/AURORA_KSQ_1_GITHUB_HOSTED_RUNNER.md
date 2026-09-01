# Aurora KSQ-1 GitHub-hosted Ubuntu 26.04 research qualification

Status: **RESEARCH INFRASTRUCTURE QUALIFIED — NOT CANONICAL CERTIFICATION HOST**

This document records the proven behavior of GitHub-hosted `ubuntu-26.04` for Aurora KSQ engineering. It is research/infrastructure qualification evidence only. It does not promote GitHub's Public Preview runner to canonical certification infrastructure, does not certify the 101-source candidate, and does not certify KSQ-1.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-1 remains **ACTIVE / NOT CERTIFIED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Policy decision

Ubuntu 26.04 LTS is stable. As of 2026-09-01 GitHub still labels the standard `ubuntu-26.04` hosted runner image/service **Public Preview**.

SupraLINUX therefore uses this runner only for isolated qualification and research while that status remains. Successful runs prove technical behavior of the observed infrastructure, but they are not canonical product-certification evidence and are not transferred automatically to a future stable/GA host.

The canonical KSQ-1 execution host remains unresolved. Before certification builds are accepted, the same relevant gates must pass on a stable Ubuntu 26.04 host/infrastructure selected for certification.

## Proven research architecture

The qualified research path is:

1. GitHub-hosted x64 `ubuntu-26.04` VM;
2. load the narrow SupraLINUX AppArmor profile on the VM;
3. launch a manually controlled pinned Ubuntu 26.04 container;
4. no privileged Docker and no parent `CAP_SYS_ADMIN`;
5. network mode `none` for snapshot-backed builder tests;
6. normalize Resolute `uidmap` helpers to the proven file-capability model;
7. run `mmdebstrap --mode=unshare` and `sbuild --chroot-mode=unshare` inside the container;
8. expose the certified snapshot slice read-only at `/opt/supralinux/archive/20260829T022000Z`;
9. use only signed `file:` APT sources from that slice.

Pinned builder image:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

Certified snapshot:

`20260829T022000Z`

Scoped security profile:

`scripts/ci/apparmor/supralinux-ksq-unshare`

Loader:

`scripts/ci/install-ksq-apparmor-profile.sh`

The container uses the scoped profile plus `seccomp=unconfined`; it does not use `--privileged`, parent `CAP_SYS_ADMIN`, `apparmor=unconfined`, or global user-namespace weakening.

## Initial hosted Ubuntu 26.04 architecture probe

Workflow:

`.github/workflows/ksq-github-hosted-builder-profile-probe.yml`

Commit:

`067d6b160f0b8c0b2411a36beecc21cd7e8dc5da`

Run / job:

- run `33467690494`;
- job `99730854792`;
- result **SUCCESS**.

Evidence:

- artifact `9785447790`;
- digest `sha256:fbcaa74ec5810f4495396c1f0afe8eb3f1b1ab67ed34723ded0ffed12e293988`.

Observed host in that run:

- Ubuntu `26.04 LTS (Resolute Raccoon)`;
- runner image version `20260824.116.1`;
- kernel `7.0.0-1012-azure`;
- Docker `29.4.2`;
- AppArmor active;
- `kernel.apparmor_restrict_unprivileged_userns=1`.

Proven container toolchain included:

- `sbuild 0.91.2ubuntu3`;
- `libsbuild-perl 0.91.2ubuntu3`;
- `mmdebstrap 1.5.7-3`;
- `uidmap 1:4.17.4-2ubuntu3`;
- `libcap2-bin 1:2.75-10ubuntu2`;
- `util-linux 2.41.3-3ubuntu2`.

The uidmap normalization is:

```text
chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
setcap cap_setuid=ep /usr/bin/newuidmap
setcap cap_setgid=ep /usr/bin/newgidmap
```

This is version-scoped engineering behavior and must be re-qualified if the relevant package changes.

## Durable snapshot input

The certified slice is no longer hypothetical. It is published and repository-pinned:

- Release ID `380209318`;
- tag `ksq-snapshot-20260829T022000Z`;
- asset ID `538944111`;
- asset `aurora-ubuntu-snapshot-20260829T022000Z-amd64.tar`;
- bytes `973148160`;
- SHA-256 `8dc9087b53e90c085333644ffdb828b87ce0af6cd61ec5f1d516fe35e80529e7`;
- manifest asset ID `538944115`;
- manifest SHA-256 `f3b30842f18fdaf868af74bbb3c6309f90e6b15a1fed2fe29bfd36a633536afd`;
- repository status `INDEPENDENTLY_VALIDATED` in `scripts/ci/aurora-ksq-snapshot-release.env`.

The Release object is a durable content-identified engineering input. Its validity is independent of whether the consumer happens to be a preview hosted runner, a future GA hosted runner, or a qualified self-hosted Ubuntu 26.04 machine.

## Published local-only consumer gate

Workflow:

`.github/workflows/ksq-github-hosted-local-snapshot-gate.yml`

Corrected commit:

`94f3e0b03e17704828cfb0325b744fffe32911a9`

Run / job:

- run `33528728431`;
- job `99926115300`;
- result **SUCCESS**.

Artifact:

- ID `9808961368`;
- GitHub digest `sha256:8216edf709c99aa39148f3c788f7ae2d6be26b91efa4aaefa36280f772ba99ef`;
- inner evidence TAR SHA-256 `1780e351dbbd2b5ad002a81e178a3c67536f19627d6951a38962fe947fbea1b9`.

The gate proved, with the builder network physically absent:

- repository-pinned Release identity verified before extraction;
- full snapshot validator PASS;
- 244/244 certified candidates exact;
- empty-status closure exactly 1541 binary objects / `704826504` bytes;
- all package URIs `file:`;
- toolchain installed exclusively from the slice;
- `mmdebstrap --mode=unshare` PASS;
- `sbuild --chroot-mode=unshare` PASS;
- `sbuild` exit 0 and `tee` exit 0;
- build log `Status: successful`;
- scoped AppArmor profile enforcing with zero recorded denials;
- no parent `CAP_SYS_ADMIN`.

### sbuild false-failure root cause

An earlier gate result was a false FAIL because the test searched for a build-time procfs marker in normal `sbuild` stdout. In normal mode `sbuild` placed the build evidence in its generated `.build` file while stdout contained only the hostname warning.

The root cause was proven through two diagnostics before changing the gate:

- purge matrix run `33527195118`: all four purge combinations returned sbuild RC 0;
- invocation matrix run `33528052878`: default/debug × redirect/pipeline all returned sbuild RC 0; both pipeline cases also returned `tee` RC 0.

The production gate now validates `Status: successful` and the build-time markers in the native `.build` evidence and separately records command/pipeline exit codes. No hostname, purge, package, AppArmor, or sbuild workaround was introduced.

## Source DAG 001 local-slice research proof

Certified DAG order 001 comes directly from canonical KSQ-0 `build-order.tsv`:

- order `1`;
- source `kf6-extra-cmake-modules`;
- packaging base `6.29.0-0ubuntu1`;
- decision `rebuild`;
- SupraLINUX version `6.29.0-0ubuntu1~supra26.04.1`.

Research workflow:

`.github/workflows/ksq-source-001-local-slice-probe.yml`

Final qualifying commit:

`3072e7945811d9ce226551fd9fab3ffbb6e5a5d2`

Run / job:

- run `33531933805`;
- job `99936944948`;
- result **SUCCESS**.

Artifact:

- ID `9810147299`;
- GitHub digest `sha256:997074576b9ef9b9d0743d931e061d222f6911fde53b809ef223e8aa4f354125`;
- inner evidence TAR SHA-256 `03f9ba7eeeaaf16ddab8345ec31da97e55c9195ae1518e5dd2c8b2ae13c12912`.

The final artifact proves:

- source acquisition exclusively from `file:/opt/supralinux/archive/20260829T022000Z/ubuntu`;
- exactly three regular source objects materialized: `.dsc`, `.orig.tar.xz`, `.debian.tar.xz`;
- exact `.dsc` identity `kf6-extra-cmake-modules 6.29.0-0ubuntu1`;
- source preparation produced `6.29.0-0ubuntu1~supra26.04.1`;
- zero KSQ overrides/adaptations were applicable to this node;
- local-only `mmdebstrap` PASS;
- local-only `sbuild` exit 0 and `tee` exit 0;
- build log `Status: successful`;
- produced `extra-cmake-modules` amd64 and `extra-cmake-modules-doc` all DEBs at the exact SupraLINUX version;
- network mode `none` and APT source `file-only`;
- zero scoped AppArmor denials.

### APT source materialization root cause

The first source-001 probes exposed two test issues, both investigated before correction:

1. APT prints upstream VCS URLs as informational NOTICE text during `apt-get source`; these were not transport. The test was narrowed to actual `Get/Hit/Ign/Err` transport lines.
2. With a `file:` source repository, APT's `Acquire::Source-Symlinks` defaults to true and may materialize source archives as symlinks. This was verified against Ubuntu Resolute `apt.conf(5)` and reproduced independently. The probe now uses the supported option `Acquire::Source-Symlinks=false` so the prepared-source workflow receives regular files while APT still performs repository metadata/checksum validation.

No source object was fetched from Launchpad or another remote archive in the qualifying run.

## What this does and does not authorize

The research chain now proves that the proposed local-slice mechanism can carry a real KSQ source node end-to-end without live Ubuntu archive or Snapshot Service access.

It does **not** authorize:

- treating GitHub `ubuntu-26.04` Public Preview as the canonical certification host;
- transferring these PASS results to another runner image/kernel without regression;
- switching the formal 101-source workflows to this path without first selecting/qualifying stable certification infrastructure;
- declaring source 001 canonically certified;
- declaring KSQ-1 certified.

## Current state

- hosted Ubuntu 26.04 research architecture: **QUALIFIED**;
- durable Release snapshot: **PUBLISHED / INDEPENDENTLY VALIDATED / REPOSITORY-PINNED**;
- hosted local-only consumer gate: **PASS (RESEARCH)**;
- hosted local-only real source DAG 001: **PASS (RESEARCH)**;
- GitHub `ubuntu-26.04` runner service: **PUBLIC PREVIEW — NOT CANONICAL CERTIFICATION HOST**;
- stable canonical Ubuntu 26.04 certification host: **TO BE SELECTED / QUALIFIED**;
- formal 101-source local-slice migration: **NOT YET PROMOTED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
