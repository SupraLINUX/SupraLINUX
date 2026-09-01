# Aurora KSQ certified snapshot slice

Status: **MATERIALIZATION/PUBLICATION IN PROGRESS — NOT YET CANONICAL**

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

The slice is not designed around persistent storage on `espadarunica`.

The current canonical execution-host qualification is GitHub-hosted `ubuntu-26.04`:

- qualifying workflow `.github/workflows/ksq-github-hosted-builder-profile-probe.yml`;
- commit `067d6b160f0b8c0b2411a36beecc21cd7e8dc5da`;
- run `33467690494`;
- job `99730854792`;
- result **SUCCESS**;
- artifact `9785447790`;
- digest `sha256:fbcaa74ec5810f4495396c1f0afe8eb3f1b1ab67ed34723ded0ffed12e293988`.

The qualifying run observed Ubuntu 26.04 LTS, runner image version `20260824.116.1`, kernel `7.0.0-1012-azure`, AppArmor enforcing, then proved real unprivileged `mmdebstrap` and `sbuild` inside the pinned Resolute container.

GitHub currently labels the runner image/service **Public preview**. Ubuntu 26.04 LTS itself is stable. SupraLINUX therefore treats runner-image changes as an infrastructure regression trigger rather than transferring PASS evidence blindly between images.

The previous GitHub-hosted Ubuntu 24.04 and `espadarunica` Ubuntu 24.04 investigations remain historical evidence only; neither is the selected canonical KSQ host.

## Durable distribution model

The final certified slice is a content-addressed engineering input, not a machine-local cache.

Target durable representation:

- exact asset name `aurora-ubuntu-snapshot-20260829T022000Z-amd64.tar`;
- dedicated engineering Release tag `ksq-snapshot-20260829T022000Z`;
- deterministic uncompressed GNU tar;
- repository-pinned SHA-256 and byte size after independent publication validation;
- committed provenance tying the asset back to snapshot `20260829T022000Z`, KSQ-0 artifact `9708738867`, and size artifact `9781553137`;
- exact internal manifests and original Ubuntu signed metadata retained inside the archive.

The archive is intentionally uncompressed. Nearly all large retained payloads are already compressed (`.deb`, `.xz`, ZIP provenance), and the certified raw upper bound is only `0.9324 GiB`. Avoiding an additional compressor removes compressor-version output from the canonical asset identity while remaining safely below GitHub's documented per-asset limit of 2 GiB.

GitHub documents up to 1000 assets per Release, each file under 2 GiB, with no total Release size or bandwidth limit. The selected slice therefore requires no splitting. The Release is explicitly created with `--latest=false` and is an engineering reproducibility input, not an Aurora product release.

The Release asset is the durable transport object. Its committed SHA-256 will be the entry-point identity; the internal Ubuntu trust chain and object manifests remain independently verified after extraction.

Actions artifacts are not the durable storage mechanism because they have lifecycle/storage semantics intended for workflow artifacts. Actions cache is used only as a temporary resumable staging accelerator after failed remote acquisition and never as the canonical identity source.

## Deterministic path and layout

Materialization and consumption both use the deterministic root:

`/opt/supralinux/archive/20260829T022000Z/`

This is intentional because `aurora-local.sources` contains the deterministic `file:` URI consumed inside the pinned Resolute builder. The GitHub runner's random `${RUNNER_TEMP}` path is not embedded in the certified slice.

The tree contains:

- `ubuntu/dists/...`: original Ubuntu `InRelease`, `Packages.xz` and `Sources.xz` bytes required for Resolute and Stonking source metadata;
- `ubuntu/dists/.../by-hash/SHA256/...`: hardlinks matching the signed index identities;
- `ubuntu/pool/...`: exactly the whitelisted Ubuntu binary/source objects required by the certified closure;
- `debian-sources/wayland-protocols-1.48/`: the four already-certified Debian Snapshot objects for `wayland-protocols 1.48-1`;
- `manifests/`: exact object identities and sizes;
- `provenance/`: canonical source/closure evidence needed to reconstruct why each retained object is present;
- `aurora-local.sources`: deterministic local-only APT source definition;
- `provenance.env` and `COMPLETE`: machine-readable completion/provenance state.

The final tree is hardened read-only before publication. Consumer jobs extract it to the same deterministic host path and then mount it read-only into the pinned Resolute container at that exact path.

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

The local-consumption gate must run with remote networking deliberately unavailable and still pass. Any active `http:`/`https:` source or any missing local object is a hard failure. There is no live-archive or Snapshot Service fallback.

## Materialization and publication workflow

Workflow:

`.github/workflows/ksq-snapshot-slice-materialize.yml`

Hosted publication implementation commit:

`3ff18e9f24c7619fe978fd1a6ca5cffa12c57089`

Initial hosted publication run:

`33468142369`

The workflow runs on GitHub-hosted `ubuntu-26.04` and is fail-closed:

1. assert the publication host is Ubuntu 26.04;
2. optionally restore `.staging-20260829T022000Z` from a GitHub Actions cache using `actions/cache/restore@v5`;
3. treat restored cache bytes as untrusted and normalize only metadata hardlinks whose content hash matches the signed canonical peer;
4. download canonical artifacts `9781553137` and `9708738867` and verify their exact ZIP SHA-256 values before materialization;
5. acquire and verify signed Ubuntu metadata;
6. materialize the exact binary/source whitelist;
7. verify every object hash and byte count;
8. verify the metadata and pool trees contain no unmanifested files;
9. verify `by-hash` identities;
10. harden the completed tree read-only;
11. create the deterministic GNU tar with sorted names, numeric owner/group zero and fixed mtime epoch `1787970000` (`2026-08-29T02:20:00Z`);
12. require the archive to remain below 2 GiB;
13. calculate exact SHA-256 and byte size and include both in a companion provenance asset;
14. refuse to overwrite an existing Release tag or same-name asset;
15. publish the engineering Release with `--latest=false`;
16. start a second fresh GitHub-hosted Ubuntu 26.04 job;
17. independently re-download both published assets;
18. compare the re-downloaded archive against the publisher job's exact SHA-256 and byte size;
19. reject unsafe archive member names and symlinks before extraction;
20. extract to `/opt/supralinux/archive` and rerun the full slice validator.

If remote Snapshot Service acquisition fails, only the partial staging directory may be saved in an Actions cache. A subsequent attempt must still revalidate all signed metadata/object identities before final promotion. Cache identity is never sufficient for acceptance.

The Release does **not** become canonical merely because this workflow publishes it. After the independent publication re-download succeeds, its exact SHA-256 and byte size must be committed to the repository. A fresh consumer gate must then trust only that repository pin before extraction.

## Required local-only acceptance before builder integration

Before changing formal KSQ-1 source-build workflows, a fresh GitHub-hosted `ubuntu-26.04` job must:

1. load the narrow AppArmor profile on the ephemeral host;
2. download the exact Release asset and verify its repository-pinned SHA-256 and byte size **before extraction**;
3. reject unsafe archive layout and extract it to `/opt/supralinux/archive`;
4. rerun the full slice validator;
5. launch the pinned Ubuntu 26.04 container with the slice mounted read-only at the same deterministic path;
6. make remote networking unavailable and configure APT exclusively with the retained `file:` sources;
7. prove all 244 certified seed candidates equal the certified versions;
8. prove an empty-status `apt-get --no-install-recommends --print-uris` solve of the same Essential/build/tooling + seed roots resolves exactly 1541 binary objects and `704826504` bytes;
9. prove every resolved binary URI is inside the local slice;
10. install the required build tooling exclusively from the local slice;
11. run canonical `mmdebstrap --mode=unshare` against that local source;
12. run the trivial `sbuild --chroot-mode=unshare` smoke and require `.deb`, `.buildinfo` and `.changes`;
13. prove no remote archive/snapshot URI is active or used.

Only after this gate passes may the formal candidate/reference/reproducibility workflows be switched to the hosted local-slice path and source DAG 001 be rerun.

For sbuild unshare, current Ubuntu Resolute documentation explicitly provides `UNSHARE_BIND_MOUNTS` for binding an outside directory to a mountpoint inside the chroot. If the local snapshot path must be visible within the sbuild chroot, that supported mechanism must be exercised and its exact mount operation added narrowly to the AppArmor profile only after observing/proving the required contract. No broad mount permission will be added speculatively.

## Upstream documentation basis

Design is based on current stable documentation rather than transport assumptions:

- Ubuntu Snapshot Service: `https://documentation.ubuntu.com/server/explanation/software/about-apt-upgrade-and-snapshots/`;
- Ubuntu Resolute `sources.list(5)`: `https://manpages.ubuntu.com/manpages/resolute/man5/sources.list.5.html`;
- Ubuntu Resolute `apt-secure(8)`: `https://manpages.ubuntu.com/manpages/resolute/man8/apt-secure.8.html`;
- Ubuntu Resolute `sbuild.conf(5)`: `https://manpages.ubuntu.com/manpages/stonking/man5/sbuild.conf.5.html`;
- GitHub standard hosted runners: `https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job`;
- GitHub Releases quotas: `https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas`;
- GitHub CLI `gh release create`: `https://cli.github.com/manual/gh_release_create`;
- `actions/cache` v5 documentation: `https://github.com/actions/cache`.

The `file:` transport does not replace signature verification; APT still verifies the retained signed repository metadata. The local slice removes repeated network transport from the critical path, not archive authentication.

## Current gate state

- snapshot slice design: **ACCEPTED**;
- GitHub-hosted Ubuntu 26.04 builder architecture: **QUALIFIED**;
- hosted materialization/publication implementation: **RUNNING**;
- durable snapshot Release asset: **NOT YET ACCEPTED**;
- independently validated published asset: **PENDING**;
- repository-pinned Release SHA-256/size: **NOT YET COMMITTED**;
- local-only APT gate from repository-pinned published asset: **NOT RUN**;
- canonical mmdebstrap regression on published local slice: **NOT RUN**;
- canonical sbuild smoke on published local slice: **NOT RUN**;
- source DAG 001 on hosted local-slice path: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
