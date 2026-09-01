# Aurora KSQ certified snapshot slice

Status: **DESIGN ACCEPTED — NOT YET MATERIALIZED/PUBLISHED**

This document defines the archive slice used to remove Ubuntu Snapshot Service transport from the KSQ-1 critical path without changing Aurora's certified archive identity.

It is infrastructure qualification evidence, not KSQ-1 acceptance. KSQ-0 remains certified/closed, KSQ-1 remains active/not certified, KSQ-2 remains blocked, and C4.1 remains paused.

## Certified inputs

Ubuntu archive snapshot:

`20260829T022000Z`

Canonical KSQ-0 closure evidence:

- run `33231879994`;
- artifact `9708738867`;
- digest `sha256:5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`;
- closure status `COMPLETE`;
- selected sources `101`;
- unresolved dependencies/source decisions `0`.

Canonical metadata-only size measurement:

- run `33455898813`;
- job `99695669970`;
- artifact `9781553137`;
- digest `sha256:39672453ba364d81cfa8621cd060201f845a6d940fb4ac04d45aa25be1ce0e19`;
- certified binary/version seeds `244`;
- selected binary objects `1541`;
- binary bytes `704826504`;
- Ubuntu source objects `301`;
- Ubuntu source bytes `212283819`;
- Debian source objects `4`;
- Debian source bytes `161155`;
- APT lists measured uncompressed `83858183` bytes;
- conservative raw upper bound `1001129661` bytes = `0.9324 GiB`;
- recommended reservation with 25% headroom `1.1655 GiB`;
- package payloads downloaded by the measurement `0`.

The size artifact contains the exact 1541 snapshot binary URIs selected by an empty-dpkg-state APT solve over the certified 244 seeds plus Essential/buildd/tooling roots. Materialization must not recompute that set from a newer archive.

## Live archive control

The non-canonical live archive control run `33456358421` / job `99697042924` failed because the current archive no longer offered the certified versions of:

- `freerdp3-dev=3.30.0+dfsg-0ubuntu0.26.04.2`;
- `libssl-dev=3.5.5-1ubuntu3.4`;
- `libwinpr3-dev=3.30.0+dfsg-0ubuntu0.26.04.2`.

Diagnostic artifact `9781682967` has digest `sha256:2edf9c572a2c134de83216beaae641e66e43cb50a8c5ddf19f6c90a8f1bce419`.

This is evidence of normal live-archive drift. It is not a KDE/package defect and it cannot replace the snapshot-backed evidence.

## Execution-host decision

The slice is no longer designed around persistent storage on `espadarunica`.

GitHub-hosted architecture probe run `33466042319`, job `99726002249`, proved that a stable `ubuntu-24.04` GitHub-hosted VM can:

- load `supralinux-ksq-unshare` in enforce mode;
- launch the pinned Ubuntu 26.04 container;
- apply the proven Resolute `uidmap` file-capability normalization;
- pass the required user/mount/PID/UTS/IPC namespace preflight;
- complete real `mmdebstrap --mode=unshare`;
- complete real `sbuild --chroot-mode=unshare` and produce `.deb`, `.buildinfo` and `.changes`.

Evidence artifact `9784900766` has digest `sha256:65546e6b93a08525bda0527eacf6953b92cede173374023d764605c62bf58354`.

The selected architecture is therefore GitHub-hosted `ubuntu-24.04` + manually launched pinned Resolute container. `espadarunica` is retained only until the replacement local-slice path passes its canonical regressions.

## Durable distribution model

The final certified slice is a content-addressed engineering input, not a machine-local cache.

Target durable representation:

- one compressed archive such as `aurora-ubuntu-snapshot-20260829T022000Z-amd64.tar.zst`;
- published as an asset of a dedicated GitHub Release;
- repository-pinned SHA-256 and byte size;
- committed provenance tying the asset back to snapshot `20260829T022000Z`, KSQ-0 artifact `9708738867`, and size artifact `9781553137`;
- exact internal manifests and original Ubuntu signed metadata retained inside the archive.

GitHub documents a per-Release-asset limit below 2 GiB and no total Release/bandwidth limit. The certified raw upper bound is `0.9324 GiB`, so the selected slice fits before compression.

The Release asset is the durable transport object. Its SHA-256 is the entry-point identity; the internal Ubuntu trust chain and object manifests remain independently verified after extraction.

Actions artifacts are not the durable storage mechanism because they have lifecycle/storage semantics intended for workflow artifacts. Actions cache may later be used only as an optional verified acceleration layer and never as the canonical identity source.

## Ephemeral hosted layout

Each certification job downloads and verifies the Release asset before extraction.

Recommended job-local tree:

`${RUNNER_TEMP}/aurora-ksq-snapshot/20260829T022000Z/`

The extracted tree contains:

- `ubuntu/dists/...`: original Ubuntu `InRelease`, `Packages.xz` and `Sources.xz` bytes required for Resolute and Stonking source metadata;
- `ubuntu/dists/.../by-hash/SHA256/...`: hardlinks or byte-identical retained copies matching the signed index identities;
- `ubuntu/pool/...`: exactly the whitelisted Ubuntu binary/source objects required by the certified closure;
- `debian-sources/wayland-protocols-1.48/`: the four already-certified Debian Snapshot objects for `wayland-protocols 1.48-1`;
- `manifests/`: exact object identities and sizes;
- `provenance/`: canonical source/closure evidence needed to reconstruct why each retained object is present;
- `aurora-local.sources`: local-only APT source template;
- `provenance.env` and `COMPLETE`: machine-readable completion/provenance state.

The tree is mounted read-only into the pinned Resolute container at a deterministic path, for example:

`/opt/supralinux/archive/20260829T022000Z/`

Certification scripts must not depend on the GitHub runner's random host temp path inside the container.

## Identity model

The slice is a byte-preserving copy of the certified upstream archives. It is deliberately **not** a newly generated APT repository.

For Ubuntu content, the trust chain remains the Ubuntu archive trust chain:

`Ubuntu archive key -> signed InRelease -> Packages/Sources checksum -> selected object checksum`.

Materialization therefore must:

1. verify each original Ubuntu `InRelease` with `ubuntu-archive-keyring.gpg`;
2. obtain each retained `Packages.xz`/`Sources.xz` identity from that signed `InRelease`;
3. obtain each binary `.deb` SHA-256 and size from the retained signed `Packages` metadata;
4. obtain each Ubuntu source object SHA-512 and size from the retained signed `Sources` metadata and prove it matches the canonical KSQ-0 selected source record;
5. retain only objects belonging to the certified closure;
6. preserve the four Debian `wayland-protocols 1.48-1` objects using their already-fixed Debian Snapshot object identities and SHA-256 hashes.

No index is regenerated, no local signing key is introduced, and no newer candidate version is substituted.

## APT contract inside the pinned container

The accepted source uses `file:` transport, Ubuntu's archive keyring, and explicitly disables snapshot URI rewriting because the local tree is already the byte-preserved snapshot.

With the deterministic container mount above, the source definition is:

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

Stonking remains source-only. A Stonking binary `Packages` index is not retained or enabled.

The local-consumption gate must run APT with HTTP and HTTPS deliberately made unusable and still pass. Any active `http:`/`https:` source or any missing local object is a hard failure. There is no live-archive or Snapshot Service fallback.

## Materialization and publication

Materialization is a one-time engineering operation. Transport errors while acquiring the upstream snapshot must never produce a partially accepted slice.

Publication is fail-closed:

1. verify canonical input artifact digests and their declared snapshot/counts;
2. acquire and verify signed Ubuntu metadata;
3. materialize the exact binary/source whitelist;
4. verify every object hash and byte count;
5. verify the metadata and pool trees contain no unmanifested files;
6. verify `by-hash` identities;
7. verify local-only APT source configuration against the completed tree;
8. create a deterministic compressed archive;
9. calculate and record its SHA-256 and byte size;
10. upload that exact archive as the dedicated GitHub Release asset;
11. download the published asset independently, verify the pinned SHA-256, extract it, and rerun the full slice validator/local-only APT gate.

Only the independently re-downloaded published asset may be promoted as the durable hosted input.

## Required local-only acceptance before builder integration

Materialization/publication alone is not sufficient. Before changing formal KSQ-1 source-build workflows, a GitHub-hosted `ubuntu-24.04` job must:

1. load the narrow AppArmor profile on the ephemeral host;
2. download the exact Release asset and verify its repository-pinned SHA-256;
3. extract it to ephemeral SSD;
4. launch the pinned Ubuntu 26.04 container with the slice mounted read-only;
5. validate the final slice;
6. run `apt-get update` using only `file:` sources while remote HTTP/HTTPS is deliberately unusable;
7. prove all 244 certified seed candidates equal the certified versions;
8. prove an empty-status `apt-get --no-install-recommends --print-uris` solve of the same Essential/build/tooling + seed roots resolves exactly 1541 binary objects and `704826504` bytes;
9. prove every resolved binary URI is inside the local slice;
10. run canonical `mmdebstrap --mode=unshare` against that local source;
11. run the trivial `sbuild --chroot-mode=unshare` smoke and require `.deb`, `.buildinfo` and `.changes`;
12. prove no remote archive/snapshot URI is active or used.

Only after this gate passes may the formal candidate/reference/reproducibility workflows be switched to the hosted local-slice path and source DAG 001 be rerun.

## Upstream documentation basis

Design is based on current stable documentation rather than transport assumptions:

- Ubuntu Snapshot Service: `https://documentation.ubuntu.com/server/explanation/software/about-apt-upgrade-and-snapshots/`
- Ubuntu Resolute `sources.list(5)`: `https://manpages.ubuntu.com/manpages/resolute/man5/sources.list.5.html`
- Ubuntu Resolute `apt-secure(8)`: `https://manpages.ubuntu.com/manpages/resolute/man8/apt-secure.8.html`
- GitHub standard hosted runners: `https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job`
- GitHub Releases storage/bandwidth quotas: `https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas`

The `file:` transport does not replace signature verification; APT still verifies the retained signed repository metadata. The local slice removes repeated network transport from the critical path, not archive authentication.

## Current gate state

- snapshot slice design: **ACCEPTED**;
- GitHub-hosted builder architecture: **PASS**;
- durable snapshot Release asset: **NOT CREATED**;
- independently validated published asset: **NO**;
- local-only APT gate from published asset: **NOT RUN**;
- canonical mmdebstrap regression on published local slice: **NOT RUN**;
- canonical sbuild smoke on published local slice: **NOT RUN**;
- source DAG 001 on hosted local-slice path: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
