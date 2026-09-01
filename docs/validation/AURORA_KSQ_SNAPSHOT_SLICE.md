# Aurora KSQ certified snapshot slice

Status: **PUBLISHED / INDEPENDENTLY VALIDATED / REPOSITORY-PINNED**

This document records the durable byte-preserved archive slice for Aurora snapshot `20260829T022000Z`. The slice removes live Ubuntu Snapshot Service transport from the KSQ build critical path without changing the archive identities certified by KSQ-0.

This status certifies the snapshot engineering input itself. It does not certify a GitHub hosted runner, a KDE candidate, or KSQ-1.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-1 remains **ACTIVE / NOT CERTIFIED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Certified origin

Ubuntu archive snapshot:

`20260829T022000Z`

Canonical KSQ-0 closure evidence:

- run `33231879994`;
- artifact `9708738867`;
- digest `sha256:5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`;
- closure `COMPLETE`;
- selected source nodes `101`;
- unresolved dependency/source decisions `0`.

Canonical size/identity evidence:

- run `33455898813`;
- job `99695669970`;
- artifact `9781553137`;
- digest `sha256:39672453ba364d81cfa8621cd060201f845a6d940fb4ac04d45aa25be1ce0e19`;
- 244 certified binary/version seeds;
- 1541 binary `.deb` objects;
- binary bytes `704826504`;
- 301 Ubuntu source objects / `212283819` bytes;
- 4 Debian source objects / `161155` bytes;
- APT lists measured uncompressed `83858183` bytes;
- conservative raw upper bound `1001129661` bytes (`0.9324 GiB`);
- 25% reservation `1.1655 GiB`;
- package payloads downloaded by the measurement `0`.

The live-archive control run `33456358421` proved that current archive drift had already removed certified versions of `freerdp3-dev`, `libssl-dev`, and `libwinpr3-dev`. This confirms that current-live archive resolution cannot substitute for the certified snapshot.

## Published immutable engineering Release

The durable slice is published as:

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

Pin status:

`AURORA_KSQ_SNAPSHOT_RELEASE_STATUS=INDEPENDENTLY_VALIDATED`

The Release is an engineering reproducibility input, not an Aurora product release.

## Identity and trust model

The slice is a byte-preserving subset of the certified upstream archives. It is not a regenerated repository and introduces no local archive-signing key.

Ubuntu trust remains:

`Ubuntu archive key -> signed InRelease -> signed Packages/Sources identity -> retained object checksum`

The tree preserves:

- original signed Ubuntu `InRelease` metadata;
- retained signed `Packages.xz` and `Sources.xz` bytes;
- corresponding `by-hash/SHA256` identities;
- exactly the whitelisted Ubuntu pool objects;
- the four certified Debian `wayland-protocols 1.48-1` source objects;
- object manifests and provenance;
- deterministic `aurora-local.sources`;
- `COMPLETE` state.

No newer candidate is substituted and no index is regenerated.

## Deterministic consumer path

Materialization and consumption use:

`/opt/supralinux/archive/20260829T022000Z/`

The APT contract inside the pinned Resolute builder is:

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

Stonking remains source-only. There is no Stonking binary suite in the consumer contract.

## Consumer verification gate

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
- GitHub digest `sha256:8216edf709c99aa39148f3c788f7ae2d6be26b91efa4aaefa36280f772ba99ef`;
- inner evidence TAR SHA-256 `1780e351dbbd2b5ad002a81e178a3c67536f19627d6951a38962fe947fbea1b9`.

That fresh consumer proved with network mode `none`:

1. exact repository pin before extraction;
2. safe archive member layout;
3. complete slice validator PASS;
4. all 244 certified APT candidates exact;
5. empty-status closure exactly 1541 objects / `704826504` bytes;
6. all package transport `file:`;
7. build toolchain installation exclusively from local content;
8. `mmdebstrap --mode=unshare` PASS;
9. trivial `sbuild --chroot-mode=unshare` PASS;
10. `sbuild` native `.build` evidence reports `Status: successful`;
11. zero recorded AppArmor denials.

This closes the local-only consumer gate for the snapshot input.

## Real source-node consumer proof

The same published slice was then used to build certified DAG order 001 in an isolated research workflow:

`.github/workflows/ksq-source-001-local-slice-probe.yml`

Final commit:

`3072e7945811d9ce226551fd9fab3ffbb6e5a5d2`

Run / job:

- run `33531933805`;
- job `99936944948`;
- result **SUCCESS**.

Artifact:

- ID `9810147299`;
- GitHub digest `sha256:997074576b9ef9b9d0743d931e061d222f6911fde53b809ef223e8aa4f354125`;
- inner evidence TAR SHA-256 `03f9ba7eeeaaf16ddab8345ec31da97e55c9195ae1518e5dd2c8b2ae13c12912`.

Certified source identity:

- source `kf6-extra-cmake-modules`;
- packaging base `6.29.0-0ubuntu1`;
- prepared version `6.29.0-0ubuntu1~supra26.04.1`.

The run materialized exactly three regular source objects from the local `stonking` `deb-src`, prepared the source through the maintained KSQ-1 source-preparation code, and produced successful local-only DEBs:

- `extra-cmake-modules_6.29.0-0ubuntu1~supra26.04.1_amd64.deb`;
- `extra-cmake-modules-doc_6.29.0-0ubuntu1~supra26.04.1_all.deb`.

No actual source or package transport used HTTP/HTTPS.

### `Acquire::Source-Symlinks`

APT's supported `Acquire::Source-Symlinks` option is significant for this local repository. Ubuntu Resolute `apt.conf(5)` documents it as true by default, allowing source archives from `file:` repositories to be represented as symlinks. KSQ's prepared-source workflow requires ordinary files, so local source acquisition explicitly uses:

`Acquire::Source-Symlinks=false`

This keeps acquisition and checksum verification inside APT while materializing regular source files. It is not a bypass of repository validation.

## Execution-host boundary

The Release slice is accepted as a durable content-identified engineering input. That conclusion is separate from the host used to test it.

GitHub's `ubuntu-26.04` hosted runner remains **Public Preview** as of 2026-09-01. Consequently:

- hosted local-only and source-001 PASS results are research qualification evidence;
- they do not establish the canonical certification host;
- a future stable/GA Ubuntu 26.04 host must rerun the relevant regressions before its evidence can be used for formal KSQ acceptance.

The slice itself does not need to be regenerated merely because the execution host changes; its bytes and repository pin are independent identities.

## Current state

- certified snapshot identity: **FIXED**;
- durable Release asset: **PUBLISHED**;
- independent publication re-download/validation: **PASS**;
- repository SHA-256/byte pin: **COMMITTED**;
- local-only consumer gate: **PASS (RESEARCH HOST)**;
- local-only mmdebstrap regression: **PASS (RESEARCH HOST)**;
- local-only sbuild smoke: **PASS (RESEARCH HOST)**;
- real source DAG 001 local-slice proof: **PASS (RESEARCH HOST)**;
- GitHub `ubuntu-26.04` as canonical certification host: **NO — PUBLIC PREVIEW**;
- stable canonical certification host: **TO BE SELECTED / QUALIFIED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
