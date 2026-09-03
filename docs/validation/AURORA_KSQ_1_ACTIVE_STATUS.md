# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This file records the current engineering state of KSQ-1. It is not an acceptance record and does not authorize entry into KSQ-2.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Fixed contract

KSQ-1 consumes:

- the certified 101-source DAG closure;
- Ubuntu Resolute snapshot `20260829T022000Z`;
- exact package/source identities established by KSQ-0;
- unprivileged `mmdebstrap --mode=unshare --variant=buildd` and `sbuild --chroot-mode=unshare` isolation;
- the maintained 95+6 reproducibility contract.

The upstream Ubuntu snapshot identity remains `20260829T022000Z`; the corrected SupraLINUX durable slice has the separate immutable identity `20260829T022000Z-r2`.

## Selected execution infrastructure

The selected KSQ execution path is:

`GitHub-hosted Ubuntu 26.04 -> immutable local r2 slice -> mmdebstrap --mode=unshare --variant=buildd -> sbuild --chroot-mode=unshare --no-enable-network`

The maintained qualification path does **not** use Docker, privileged containers, outer `CAP_SYS_ADMIN`, host AppArmor relaxation, a custom AppArmor profile, or the historical uidmap file-capability rewrite.

GitHub labels `ubuntu-26.04` Public Preview. Ubuntu 26.04 LTS itself is stable; the preview status belongs to external CI infrastructure. SupraLINUX therefore accepts the runner for qualification only through fail-closed verification of the exact required behavior. A future canonical productive release builder is tracked separately as a post-project architecture requirement.

## Canonical corrected snapshot input

Repository pointer: `scripts/ci/aurora-ksq-snapshot-release.env`.

Current immutable local slice:

- upstream Ubuntu snapshot `20260829T022000Z`;
- Supra slice `20260829T022000Z-r2`;
- status `INDEPENDENTLY_VALIDATED`;
- generic `amd64`, architecture variants disabled;
- normal/default APT Recommends policy;
- Release ID `381836501`;
- tag `ksq-snapshot-20260829T022000Z-r2`;
- archive asset `542414026`, bytes `1054177280`;
- archive SHA-256 `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`;
- manifest asset `542414028`;
- manifest SHA-256 `6ed95b495ded7744f081335684c2918eeae96dbc822fa53b0d9fb5bc2da0f481`;
- 244 exact certified binary/version seeds;
- 1783 binary `.deb` objects / `785219274` bytes;
- 301 Ubuntu source objects;
- 4 Debian source objects.

Independent publication re-download/validation is PASS: job `100569481825`, artifact `9883714959`, digest `sha256:c628aadcb577d5d1777ebf0b6d6c2e0d9c737fbfc82aa920e60f624a30c23b36`.

## Proven r1 -> r2 root cause

The historical r1 slice was generated using explicit `apt-get --no-install-recommends`, yielding 1541 objects / 704826504 bytes. The real `sbuild 0.91.2ubuntu3` path uses normal APT dependency semantics, where Recommends are considered unless explicitly disabled.

At order 43, `pipewire-bin` caused APT to request `dbus-user-session=1.16.2-2ubuntu4`; that object was absent from r1 because the slice closure policy differed from the real builder policy.

Controlled native A/B run `33729123389` proved:

- explicit no-Recommends: 1541 objects / 704826504 bytes;
- default Recommends: 1783 objects / 785219274 bytes.

The correction was to rebuild the complete durable slice closure with the real builder policy, not to add `dbus-user-session` manually, patch `kpipewire`, or change `sbuild` to suppress Recommends.

Detailed record: `docs/validation/AURORA_KSQ_1_SNAPSHOT_R2_RANGE_041_043.md`.

## Maintained build chain

Canonical build-order SHA-256 remains `9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`.

### Orders 001-020

- run `33546093974`, job `99983826266`;
- **PASS**;
- artifact `9818465016`, digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`;
- 20/20 sources PASS;
- accumulated DEBs `103`.

### Orders 021-040

- run `33561782526`, job `100035734787`;
- **PASS**;
- artifact `9824689982`, digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`;
- 20/20 sources PASS;
- new DEBs `89`;
- accumulated DEBs `192`.

### Orders 041-043 — corrected r2 regression

- run `33753437984`, job `100642085362`;
- **PASS**;
- artifact `9892762100`;
- digest `sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0`;
- 3/3 sources PASS including `kpipewire`;
- new DEBs `13`;
- accumulated DEBs `205`;
- build-manifest SHA-256 `e4311aeba5c7856ac2c0ff803c9adc2fdcb63adb104d1a8f2707a1fc45696ab1`;
- `new-debs.sha256` file SHA-256 `d5e6cbd51cac0ac2d2dca953722ccbd1a43beb3c981766f683ae69ace539105c`;
- command RC `0`, relevant AppArmor denials `0`, external build acquisition `0`.

### Orders 044-060 — native r2

- workflow `.github/workflows/ksq-native-range-044-060-r2.yml`;
- commit `2f167566ad2d60bf013336ae834c4b37c5e4e9b4`;
- run `33767306768`, job `100688352977`;
- **PASS / job SUCCESS**;
- artifact `9900367299`;
- digest `sha256:41a50bb17ea5ca4ab63c43a6aa6d6d030dae310ba716866824ac72d6c61dc4f3`;
- exact prior checkpoint `205` DEBs verified before order 44;
- orders `44..60`, sources `17/17 PASS`;
- new DEBs `70`;
- accumulated DEBs `275`;
- build-manifest SHA-256 `4ac871dc0865bb10b27f0b23db8b8969e595c67ab4faa75dd295b0877ccaf709`;
- `new-debs.sha256` file SHA-256 `a712b2f8d67d2bbb8aea4f3ccc6f7af930e4cfc3974f5562c923b12ea23267a5`;
- command RC `0`, tee RC `0`;
- 17 successful `.build` logs with the native build-network isolation proof;
- relevant AppArmor denials `0`;
- Docker/custom AppArmor/uidmap filecap adaptation `0`.

The maintained r2 candidate is therefore qualified through **order 60**, with **275 accumulated DEBs**.

## Checkpoint-chain hardening

`scripts/ci/restore-ksq-1-checkpoint-chain.py` is the fail-closed checkpoint restorer. It validates contiguous source-order coverage, PASS state, internal manifest identities, every DEB SHA-256, filename/package uniqueness and exact cumulative counts before reconstructing the candidate set.

The accepted chain through order 60 is exactly:

- 001-020 artifact `9818465016`;
- 021-040 artifact `9824689982`;
- 041-043 r2 artifact `9892762100`;
- 044-060 r2 artifact `9900367299`.

The two newer native artifacts retain a top-level `build/` directory; consumers must account for that layout explicitly. The failed run `33777276308` demonstrated this fail-closed by rejecting an incorrect artifact root before any source build began.

## KWallet PAM native validation

Order 65 is `kwallet-pam`. The old Docker/root/custom-AppArmor validator is rejected for the current architecture.

`scripts/ci/validate-ksq-1-kwallet-pam-local.sh` has been ported to the native unprivileged contract. It consumes the canonical r2 slice and exact rebuilt candidate packages and requires:

- `libpam-kwallet-common` and `libpam-kwallet5` from order 65;
- rebuilt `kwallet6`, `libkf6wallet-data`, `libkf6wallet6`, `libkf6walletbackend6` from the candidate chain;
- compat 13 and restored `${misc:Depends}`, `${qml6:Depends}`, `${shlibs:Depends}` source-control contract;
- expected binary runtime dependencies including `kwallet6`, `libpam-runtime`, `libpam-kwallet-common` and `socat` where applicable;
- clean `mmdebstrap --mode=unshare` installation from local r2 plus local candidate DEBs;
- `apt-get check`;
- exact installed candidate versions;
- `pam_kwallet5.so` registered in `common-auth` and `common-session`;
- no HTTP/HTTPS package transport;
- no Docker or custom AppArmor dependency.

This gate certifies package/install/PAM registration. Runtime session auto-unlock remains a later functional certification and is explicitly not claimed here.

Workflow `.github/workflows/ksq-native-range-061-065-r2-kwallet.yml` is currently qualifying orders 61-65 and this KWallet installation gate. Orders 66-80 remain blocked until that workflow passes.

## Reproducibility contract

KSQ-1 retains the 95+6 contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against independent reference evidence;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final patched candidate.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- upstream Ubuntu snapshot: **20260829T022000Z / FIXED**;
- canonical local slice: **20260829T022000Z-r2 / INDEPENDENTLY VALIDATED**;
- GitHub-hosted Ubuntu 26.04 native unshare architecture: **QUALIFIED / SELECTED**;
- maintained 001-020: **PASS**;
- maintained 021-040: **PASS**;
- maintained 041-043 r2: **PASS**;
- maintained 044-060 r2: **PASS**;
- accumulated candidate through order 60: **275 DEBs**;
- orders 061-065 + KWallet PAM native gate: **IN PROGRESS / NOT YET ACCEPTED**;
- orders 066-080: **BLOCKED ON 061-065 + KWALLET GATE**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
