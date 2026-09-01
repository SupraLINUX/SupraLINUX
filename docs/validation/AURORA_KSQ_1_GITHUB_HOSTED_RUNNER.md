# Aurora KSQ-1 GitHub-hosted Ubuntu 26.04 qualification

Status: **QUALIFIED / SELECTED EXECUTION INFRASTRUCTURE — NOT KSQ-1 ACCEPTANCE**

This document records the proven GitHub-hosted `ubuntu-26.04` execution architecture selected for Aurora KSQ engineering. It qualifies CI infrastructure only. It does not certify the complete 101-source candidate or KSQ-1.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-1 remains **ACTIVE / NOT CERTIFIED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Policy decision

Ubuntu 26.04 LTS is stable. GitHub still labels the standard `ubuntu-26.04` runner image/service **Public Preview** as of 2026-09-01.

That preview status belongs to external CI infrastructure and does not introduce preview software into the SupraLINUX product. It is therefore not automatically rejected by the project's stable-product rule. Instead, the runner is accepted only through empirical qualification of every host/security behavior KSQ actually depends on.

Each formal KSQ job must record the runner image/version when available, kernel, Docker and AppArmor state and rerun the required fail-closed infrastructure invariants. A GitHub image/security/tool change that affects those invariants is a regression trigger; previous PASS is not transferred blindly.

## Selected architecture

1. GitHub-hosted x64 `runs-on: ubuntu-26.04`.
2. Load scoped AppArmor profile `scripts/ci/apparmor/supralinux-ksq-unshare` on the ephemeral VM.
3. Use exact builder image `ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`.
4. Create the container through `scripts/ci/ksq-docker-builder.py`.
5. Expose snapshot `20260829T022000Z` read-only.
6. Keep outer container non-privileged, with no parent `CAP_SYS_ADMIN`, AppArmor enforcing and package/build networking physically absent.
7. Normalize Resolute `uidmap` helpers to the qualified file-capability form.
8. Run `mmdebstrap --mode=unshare` and `sbuild --chroot-mode=unshare` inside the pinned container.

## Initial hosted qualification

Workflow `.github/workflows/ksq-github-hosted-builder-profile-probe.yml`:

- commit `067d6b160f0b8c0b2411a36beecc21cd7e8dc5da`;
- run `33467690494`;
- job `99730854792`;
- result **SUCCESS**;
- artifact `9785447790`;
- digest `sha256:fbcaa74ec5810f4495396c1f0afe8eb3f1b1ab67ed34723ded0ffed12e293988`.

Observed in that run:

- Ubuntu 26.04 LTS;
- runner image `20260824.116.1`;
- kernel `7.0.0-1012-azure`;
- Docker `29.4.2`;
- AppArmor enforcing.

Qualified container toolchain included `sbuild 0.91.2ubuntu3`, `libsbuild-perl 0.91.2ubuntu3`, `mmdebstrap 1.5.7-3`, `uidmap 1:4.17.4-2ubuntu3`, `libcap2-bin 1:2.75-10ubuntu2` and `util-linux 2.41.3-3ubuntu2`.

The uidmap normalization remains version-scoped:

```text
chmod u-s /usr/bin/newuidmap /usr/bin/newgidmap
setcap cap_setuid=ep /usr/bin/newuidmap
setcap cap_setgid=ep /usr/bin/newgidmap
```

## Procfs root cause and final Docker contract

Docker's default system-path protection creates masked/read-only submounts below `/proc`. Linux then rejects the nested procfs mount required by `sbuild-usernsexec` in the nested user namespace.

A causal `systempaths=unconfined` probe proved the mechanism, but was rejected as unnecessarily broad. The maintained helper `scripts/ci/ksq-docker-builder.py` instead uses the Docker Engine API to remove only the `/proc` submount masks that break nested user namespaces while retaining sensitive `/sys` masks.

The selective helper was proven with:

- `Privileged=false`;
- no `CapAdd`;
- effective `CAP_SYS_ADMIN` absent;
- AppArmor `supralinux-ksq-unshare (enforce)`;
- `/proc` as a single procfs mount;
- `/sys/firmware` still masked;
- network mode `none`;
- zero scoped AppArmor denials.

## Durable snapshot input

Published repository-pinned snapshot:

- Release ID `380209318`;
- tag `ksq-snapshot-20260829T022000Z`;
- asset ID `538944111`;
- asset `aurora-ubuntu-snapshot-20260829T022000Z-amd64.tar`;
- bytes `973148160`;
- SHA-256 `8dc9087b53e90c085333644ffdb828b87ce0af6cd61ec5f1d516fe35e80529e7`;
- repository status `INDEPENDENTLY_VALIDATED` in `scripts/ci/aurora-ksq-snapshot-release.env`.

## Local-only consumer gate

Workflow `.github/workflows/ksq-github-hosted-local-snapshot-gate.yml`:

- commit `94f3e0b03e17704828cfb0325b744fffe32911a9`;
- run `33528728431`;
- job `99926115300`;
- result **SUCCESS**;
- artifact `9808961368`;
- artifact digest `sha256:8216edf709c99aa39148f3c788f7ae2d6be26b91efa4aaefa36280f772ba99ef`;
- inner evidence TAR SHA-256 `1780e351dbbd2b5ad002a81e178a3c67536f19627d6951a38962fe947fbea1b9`.

With network physically absent it proved:

- exact Release pin and full slice validation;
- 244/244 exact candidates;
- exact 1541-object / `704826504`-byte empty-status closure;
- only `file:` package transport;
- toolchain install from the slice;
- namespace preflight;
- local-only `mmdebstrap` PASS;
- local-only `sbuild` RC 0 and native `.build` `Status: successful`;
- functional procfs during the build;
- zero scoped AppArmor denials.

## Source DAG 001 proof

Workflow `.github/workflows/ksq-source-001-local-slice-probe.yml`:

- final commit `3072e7945811d9ce226551fd9fab3ffbb6e5a5d2`;
- run `33531933805`;
- job `99936944948`;
- result **SUCCESS**;
- artifact `9810147299`;
- digest `sha256:997074576b9ef9b9d0743d931e061d222f6911fde53b809ef223e8aa4f354125`.

Certified order 001 is `kf6-extra-cmake-modules 6.29.0-0ubuntu1`, prepared as `6.29.0-0ubuntu1~supra26.04.1`. The run acquired the exact source objects from the local signed `stonking` source index, created the local buildd environment and built successful DEBs with no package/source network transport.

Resolute APT's default `Acquire::Source-Symlinks=true` was proven significant for `file:` source repositories. The maintained local source contract uses `Acquire::Source-Symlinks=false` so APT materializes verified ordinary files for the existing source-preparation pipeline.

## Evidence interpretation rules

Two false-failure classes are closed and must not be reintroduced:

1. Build status/procfs evidence comes from the generated native `*.build` file while the actual `sbuild` exit code is recorded separately; normal sbuild stdout is not the canonical build log.
2. `apt-get source` can print upstream VCS URLs as informational notices. Remote-transport detection evaluates actual APT acquisition records and is independently backed by network mode `none`.

## Historical infrastructure

GitHub-hosted Ubuntu 24.04 and `espadarunica` Ubuntu 24.04 remain historical root-cause evidence only. They are not the selected KSQ execution path.

## Current state

- GitHub-hosted Ubuntu 26.04 execution infrastructure: **QUALIFIED / SELECTED**;
- pinned Resolute builder: **QUALIFIED**;
- selective proc-only Docker helper: **QUALIFIED / MAINTAINED**;
- durable snapshot Release: **PUBLISHED / VALIDATED / PINNED**;
- local-only consumer gate: **PASS**;
- real source DAG 001 local-only: **PASS**;
- formal 101-source local-slice migration: **NEXT**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
