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

## Current host policy

There is currently **no canonical KSQ-1 certification host selected**.

GitHub-hosted `ubuntu-26.04` has been technically qualified for research, including a complete local-only snapshot consumer gate and a real source-DAG-order-001 build. However, GitHub still labels that runner image/service **Public Preview** as of 2026-09-01.

Ubuntu 26.04 LTS itself is stable. The restriction applies to GitHub's hosted runner infrastructure, not to Ubuntu.

Under SupraLINUX's stable-product rules, preview hosted infrastructure is not promoted to canonical certification infrastructure. Its successful runs remain valuable research/root-cause evidence and define the behavior that a future stable Ubuntu 26.04 certification host must reproduce.

Pinned builder userspace retained for that contract:

`ubuntu:26.04@sha256:2260313b31c8c011cd2eebe728008efac1b3982be73eb71348ea2648d2c0e09b`

## Durable certified snapshot input

The snapshot slice is now published, independently validated, and repository-pinned:

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

Live current Ubuntu archive resolution is not acceptable for this contract; archive drift was already demonstrated by the KSQ live-control run.

## Local-only consumer qualification

Workflow:

`.github/workflows/ksq-github-hosted-local-snapshot-gate.yml`

Qualifying commit:

`94f3e0b03e17704828cfb0325b744fffe32911a9`

Run / job:

- run `33528728431`;
- job `99926115300`;
- result **SUCCESS**.

Artifact:

- ID `9808961368`;
- digest `sha256:8216edf709c99aa39148f3c788f7ae2d6be26b91efa4aaefa36280f772ba99ef`;
- inner evidence TAR SHA-256 `1780e351dbbd2b5ad002a81e178a3c67536f19627d6951a38962fe947fbea1b9`.

With container networking physically absent, the gate proved:

- exact Release pin and safe extraction;
- full slice validation;
- 244 exact package candidates;
- exact 1541-object / `704826504`-byte empty-status closure;
- all APT package URIs `file:`;
- local-only toolchain install;
- namespace preflight;
- local-only `mmdebstrap` PASS;
- local-only `sbuild` PASS;
- native `.build` status successful;
- zero scoped AppArmor denials.

This closes the technical local-only consumer gate on the research host.

## Real source DAG 001 qualification

Certified DAG order 001 is:

- source `kf6-extra-cmake-modules`;
- packaging base `6.29.0-0ubuntu1`;
- candidate decision `rebuild`;
- SupraLINUX version `6.29.0-0ubuntu1~supra26.04.1`.

Research workflow:

`.github/workflows/ksq-source-001-local-slice-probe.yml`

Qualifying commit:

`3072e7945811d9ce226551fd9fab3ffbb6e5a5d2`

Run / job:

- run `33531933805`;
- job `99936944948`;
- result **SUCCESS**.

Artifact:

- ID `9810147299`;
- GitHub digest `sha256:997074576b9ef9b9d0743d931e061d222f6911fde53b809ef223e8aa4f354125`;
- inner evidence TAR SHA-256 `03f9ba7eeeaaf16ddab8345ec31da97e55c9195ae1518e5dd2c8b2ae13c12912`.

The run proved end-to-end:

1. source objects acquired from the published local `stonking` `deb-src` only;
2. exactly one `.dsc`, with `Source: kf6-extra-cmake-modules` and `Version: 6.29.0-0ubuntu1`;
3. all three source objects materialized as ordinary files using supported `Acquire::Source-Symlinks=false`;
4. maintained source preparation produced `6.29.0-0ubuntu1~supra26.04.1`;
5. no source-001 override or packaging adaptation was required;
6. local-only `mmdebstrap` PASS;
7. local-only `sbuild` RC 0, `Status: successful`;
8. output DEBs:
   - `extra-cmake-modules_6.29.0-0ubuntu1~supra26.04.1_amd64.deb`;
   - `extra-cmake-modules-doc_6.29.0-0ubuntu1~supra26.04.1_all.deb`;
9. network mode `none`;
10. zero scoped AppArmor denials.

This is a **research PASS**, not canonical source-001 certification, because the execution host is still a GitHub Public Preview runner.

## Root causes closed during hosted research

### sbuild post-check false FAIL

Normal `sbuild` output did not contain the build-time procfs marker; the native generated `.build` did. Purge and invocation matrices proved that sbuild itself returned zero under all tested combinations. The gate now reads native build evidence and preserves command/pipeline exit codes separately.

### source acquisition URL false positive

`apt-get source` can print upstream VCS URLs as informational notices. These are not acquisition transport. The gate now evaluates actual APT transport lines, while the builder also has no usable network interface.

### local `file:` source symlinks

Ubuntu Resolute APT defaults `Acquire::Source-Symlinks` to true. With a local source repository, APT can therefore produce symlinks instead of regular source files. This behavior was independently reproduced and checked against current Resolute `apt.conf(5)`. The research path uses the supported `Acquire::Source-Symlinks=false` option so the existing source-preparation contract receives regular files without bypassing APT verification.

## Formal KSQ-1 workflows are not yet promoted

`.github/workflows/ksq-1-full-builds.yml` must not be treated as ready for canonical qualification yet.

Current helper scripts still contain legacy assumptions that must be migrated only after stable certification infrastructure is selected:

- `scripts/ci/prepare-ksq-1-runner.sh` still installs tooling through the runner's active APT configuration;
- `scripts/ci/prepare-ksq-1-build-environment.sh` still points `mmdebstrap` directly at `https://snapshot.ubuntu.com/...`;
- `scripts/ci/fetch-prepare-ksq-1-source.sh` still consumes the earlier KSQ-0 generated APT metadata model and must be adapted to the published local slice, including intentional handling of `Acquire::Source-Symlinks`.

No formal 001-020 or larger candidate range is promoted until this architecture migration is implemented and regressed on the selected stable Ubuntu 26.04 certification host.

## Preserved historical candidate evidence

Previous KSQ-1 candidate/discovery runs remain historical evidence. They are not automatically accepted under a new host/toolchain contract.

The forward 081-101 discovery run `33264431724` proved orders 81-98 completed and order 99 was interrupted by configured timeout rather than a demonstrated KDE/package failure. Preserved artifacts include:

- evidence `9723899912`, SHA-256 `636382ea83362a944a1dd756c64c64095eff8727df92b4cf3f9165c827feb9cd`;
- DEBs `9723899191`, SHA-256 `0319295375a765753aa615715342a532adeabb8f3916cc19d72ab3631b588781`.

Any required certification regression will be rerun; prior PASS is not transferred merely because source/package versions look unchanged.

## Reproducibility contract

KSQ-1 retains the 95+6 reproducibility contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against an independent reference build;
- orders 29, 68, 81, 99, 100, and 101 require dedicated independent rebuild proof against the final patched candidate.

This contract is unchanged by the hosted research.

## Next engineering gate

The next architectural task is to select and qualify **stable Ubuntu 26.04 certification infrastructure**. Candidate approaches may include a stable self-hosted Ubuntu 26.04 runner or GitHub-hosted `ubuntu-26.04` once it reaches GA; no option is accepted without evidence.

On the selected host, rerun at minimum:

1. host identity/security qualification;
2. published snapshot local-only consumer gate;
3. real source DAG 001 local-only regression.

Only after those regressions PASS may the formal KSQ-1 builder/helpers be migrated and the 101-source candidate be rebuilt for certification.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- published snapshot Release: **PUBLISHED / INDEPENDENTLY VALIDATED / PINNED**;
- GitHub-hosted Ubuntu 26.04 research architecture: **QUALIFIED**;
- hosted local-only consumer gate: **PASS (RESEARCH)**;
- hosted real source DAG 001 local-only: **PASS (RESEARCH)**;
- GitHub hosted `ubuntu-26.04` as canonical certification host: **NO — PUBLIC PREVIEW**;
- stable canonical Ubuntu 26.04 host: **NOT YET SELECTED / QUALIFIED**;
- formal local-slice KSQ-1 workflow migration: **NOT YET PROMOTED**;
- complete 101-source candidate under final host contract: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
