# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This file records the current engineering state of KSQ-1. It is not an acceptance record and does not authorize entry into KSQ-2.

## Certified prerequisite

KSQ-0 remains **CERTIFIED / CLOSED**.

The KSQ-1 build contract consumes:

- the certified 101-source closure;
- Ubuntu Resolute snapshot `20260829T022000Z`;
- exact package identities already established by KSQ-0;
- unprivileged `mmdebstrap --mode=unshare` and `sbuild --chroot-mode=unshare` isolation.

KSQ-2 remains **BLOCKED** and C4.1 remains **PAUSED** until KDE Stack Qualification is completed.

## Current execution-host decision

The selected GitHub Actions execution host is:

`runs-on: ubuntu-26.04`

This is intentionally different from the previously tested `ubuntu-24.04` hosted architecture and from the `espadarunica` Ubuntu 24.04 self-hosted runner.

Rationale:

- SupraLINUX Aurora is based on Ubuntu 26.04 LTS;
- the host kernel and host security mechanisms participate in user namespaces, AppArmor, seccomp, cgroups and mount behavior;
- therefore the canonical KSQ build host itself is Ubuntu 26.04 rather than a 24.04 host plus a 26.04 userspace container.

As of 2026-09-01 GitHub labels its `ubuntu-26.04` runner image **Public preview**. This is a status of GitHub's runner image/service, not of Ubuntu 26.04 LTS itself. SupraLINUX has therefore qualified the exact infrastructure behavior required by KSQ instead of assuming acceptance from the label.

The build userspace remains additionally fixed by the pinned container:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

This separates two identities that must both be recorded:

1. the GitHub-hosted Ubuntu 26.04 VM/kernel/security environment;
2. the exact Ubuntu 26.04 OCI userspace used for the disposable builder.

## Ubuntu 26.04 hosted qualification

Workflow:

`.github/workflows/ksq-github-hosted-builder-profile-probe.yml`

Qualifying commit:

`067d6b160f0b8c0b2411a36beecc21cd7e8dc5da`

Run / job:

- run `33467690494`;
- job `99730854792`;
- result **SUCCESS**.

Evidence artifact:

- `aurora-ksq-github-hosted-2604-builder-profile-probe`;
- artifact ID `9785447790`;
- size `12150` bytes;
- SHA-256 `fbcaa74ec5810f4495396c1f0afe8eb3f1b1ab67ed34723ded0ffed12e293988`.

Observed host:

- Ubuntu `26.04 LTS (Resolute Raccoon)`;
- runner image `ubuntu-26.04` version `20260824.116.1`;
- kernel `7.0.0-1012-azure`;
- Docker `29.4.2`;
- AppArmor active;
- `kernel.apparmor_restrict_unprivileged_userns=1`.

The narrow AppArmor profile loaded enforcing, the full namespace preflight passed, real `mmdebstrap --mode=unshare --variant=buildd` completed, and a real trivial source package completed through `sbuild --chroot-mode=unshare`, producing `.deb`, `.build`, `.buildinfo` and `.changes` outputs.

The workflow emitted:

`AURORA_KSQ_GITHUB_HOSTED_2604_REAL_SBUILD_PASS`

Therefore the GitHub-hosted Ubuntu 26.04 execution architecture is **QUALIFIED** for the next KSQ infrastructure gates. This is not source-build or KSQ-1 acceptance evidence.

## Snapshot requirement

The final KSQ path must not depend on the live Ubuntu archive or live Snapshot Service during source certification.

The certified slice for `20260829T022000Z` has measured identity:

- 244 certified binary/version seeds;
- 1541 binary `.deb` objects;
- 704,826,504 binary bytes;
- 301 Ubuntu source objects;
- 4 Debian source objects;
- conservative raw upper bound 1,001,129,661 bytes (`0.9324 GiB`).

The durable distribution target remains a dedicated GitHub Release asset with repository-pinned SHA-256, byte size and provenance. GitHub permits individual Release assets below 2 GiB, so the measured slice fits without splitting even before compression.

Before source node 001 may be rerun on the new architecture, a fresh GitHub-hosted Ubuntu 26.04 job must independently:

1. obtain the exact published slice;
2. verify its repository-pinned SHA-256 and internal provenance;
3. expose it read-only to the pinned Resolute builder;
4. configure APT exclusively through `file:` sources;
5. make HTTP/HTTPS fallback unusable;
6. verify all 244 exact candidates;
7. reproduce the exact empty-status solve of 1541 objects / 704826504 bytes;
8. complete canonical snapshot-backed mmdebstrap;
9. complete canonical snapshot-backed sbuild smoke.

Only after that gate passes may source DAG order 001 be rerun.

## Preserved historical candidate evidence

Earlier KSQ-1 runs remain historical evidence and are not discarded by the host migration.

The forward 081-101 discovery run `33264431724` proved orders 81-98 completed and that order 99 was interrupted by the configured job timeout rather than by a demonstrated KDE/package failure. Its preserved evidence remains:

- `aurora-ksq-1-discovery-evidence-081-101`, artifact `9723899912`, SHA-256 `636382ea83362a944a1dd756c64c64095eff8727df92b4cf3f9165c827feb9cd`;
- `aurora-ksq-1-discovery-debs-081-101`, artifact `9723899191`, SHA-256 `0319295375a765753aa615715342a532adeabb8f3916cc19d72ab3631b588781`.

The tail-resume tooling and prior candidate artifacts remain useful evidence, but no PASS from a different host/toolchain combination is automatically transferred to the new canonical execution path. Required regressions must be rerun.

## Reproducibility contract

KSQ-1 retains the 95+6 reproducibility contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against an independent reference build;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final patched candidate.

No reproducibility selector may be promoted until the Ubuntu 26.04 hosted path has passed the certified local-slice gate and produced a complete validated 101-source candidate.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- GitHub-hosted `ubuntu-26.04` host identity: **PASS**;
- GitHub-hosted `ubuntu-26.04` AppArmor/namespace path: **PASS**;
- GitHub-hosted real mmdebstrap: **PASS**;
- GitHub-hosted real sbuild smoke: **PASS**;
- GitHub-hosted Ubuntu 26.04 execution architecture: **QUALIFIED**;
- pinned Resolute build userspace: **RETAINED**;
- certified snapshot Release asset: **NOT CREATED**;
- hosted local-only APT gate: **NOT RUN**;
- hosted snapshot-backed mmdebstrap: **NOT RUN**;
- hosted snapshot-backed sbuild smoke: **NOT RUN**;
- source node 001 on new canonical path: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
