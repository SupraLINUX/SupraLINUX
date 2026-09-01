# Aurora KSQ certified snapshot slice

Status: **DESIGN ACCEPTED — NOT YET MATERIALIZED**

This document defines the local archive slice used to remove Ubuntu Snapshot Service transport from the KSQ-1 critical path without changing Aurora's certified archive identity.

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

## Local layout

Final immutable path on `espadarunica`:

`/srv/supralinux/archive/20260829T022000Z/`

Resumable, non-consumable staging path:

`/srv/supralinux/archive/.staging-20260829T022000Z/`

The final tree contains:

- `ubuntu/dists/...`: original Ubuntu `InRelease`, `Packages.xz` and `Sources.xz` bytes required for Resolute and Stonking source metadata;
- `ubuntu/dists/.../by-hash/SHA256/...`: hardlinks to the retained signed index bytes;
- `ubuntu/pool/...`: exactly the whitelisted Ubuntu binary/source objects required by the certified closure;
- `debian-sources/wayland-protocols-1.48/`: the four already-certified Debian Snapshot objects for `wayland-protocols 1.48-1`;
- `manifests/`: exact object identities and sizes;
- `provenance/`: the two canonical GitHub artifacts plus the source/closure evidence needed to reconstruct why each retained object is present;
- `aurora-local.sources`: the only APT source definition accepted for local-slice validation;
- `provenance.env` and `COMPLETE`: machine-readable completion/provenance state.

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

## APT contract

The accepted local source uses `file:` transport, Ubuntu's archive keyring, and explicitly disables snapshot URI rewriting because the local tree is already the byte-preserved snapshot:

```text
Types: deb deb-src
URIs: file:/srv/supralinux/archive/20260829T022000Z/ubuntu
Suites: resolute resolute-updates resolute-security resolute-backports
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no

Types: deb-src
URIs: file:/srv/supralinux/archive/20260829T022000Z/ubuntu
Suites: stonking
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no
```

Stonking remains source-only. A Stonking binary `Packages` index is not retained or enabled.

The local-consumption gate must run APT with HTTP and HTTPS deliberately made unreachable and still pass. Any active `http:`/`https:` source or any missing local object is a hard failure. There is no live-archive or Snapshot Service fallback.

## Materialization and promotion

Downloads are resumable only inside the staging path. A partial or hash-failed object can never be promoted as final evidence.

Promotion is fail-closed:

1. verify canonical input artifact digests and their declared snapshot/counts;
2. acquire and verify signed Ubuntu metadata;
3. materialize the exact binary/source whitelist;
4. verify every object hash and byte count;
5. verify the metadata and pool trees contain no unmanifested files;
6. verify `by-hash` identities;
7. verify local-only APT source configuration;
8. mark the slice read-only;
9. atomically rename staging to the final snapshot path;
10. validate the final path again.

If any step fails, staging is retained for a resumable rerun and the final path is not created.

## Required local-only acceptance before builder integration

Materialization by itself is not sufficient. Before changing the KSQ-1 build scripts, a self-hosted job in the pinned Ubuntu 26.04 container must prove all of the following:

- the final slice validator passes;
- `apt-get update` passes using only `file:` sources while remote HTTP/HTTPS is deliberately unusable;
- all 244 certified seed candidates equal the certified versions;
- an empty-status `apt-get --no-install-recommends --print-uris` solve of the same Essential/build/tooling + seed roots resolves exactly 1541 binary objects and `704826504` bytes;
- every resolved binary URI is inside the final local slice;
- no remote archive/snapshot URI is active or used.

Only after this gate passes may `prepare-ksq-1-build-environment.sh`, source-fetch logic, or the canonical self-hosted sbuild path be switched from remote Snapshot Service transport to the local slice.

## Upstream documentation basis

Design is based on current stable documentation rather than transport assumptions:

- Ubuntu Snapshot Service: `https://documentation.ubuntu.com/server/explanation/software/about-apt-upgrade-and-snapshots/`
- Ubuntu Resolute `sources.list(5)`: `https://manpages.ubuntu.com/manpages/resolute/man5/sources.list.5.html`
- Ubuntu Resolute `apt-secure(8)`: `https://manpages.ubuntu.com/manpages/resolute/man8/apt-secure.8.html`
- GitHub Actions job containers and bind mounts: `https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/run-jobs-in-a-container`

The `file:` transport does not replace signature verification; APT still verifies the retained signed repository metadata. The local slice removes repeated network transport from the critical path, not archive authentication.

## Current gate state

- local slice design: **ACCEPTED**;
- local slice materialized: **NO**;
- local-only APT gate: **NOT RUN**;
- canonical mmdebstrap regression on local slice: **NOT RUN**;
- canonical sbuild smoke on local slice: **NOT RUN**;
- source DAG 001 on local slice: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
