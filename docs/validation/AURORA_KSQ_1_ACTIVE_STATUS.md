# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This file records the current engineering state of KSQ-1. It is not an acceptance record and does not authorize entry into KSQ-2.

KSQ-0 remains **CERTIFIED / CLOSED**. KSQ-2 remains **BLOCKED**. C4.1 remains **PAUSED**.

## Fixed contract

KSQ-1 consumes:

- the certified 101-source DAG closure;
- Ubuntu Resolute snapshot `20260829T022000Z`;
- exact package/source identities established by KSQ-0;
- unprivileged `mmdebstrap --mode=unshare --variant=buildd` and `sbuild --chroot-mode=unshare` isolation for source builds;
- the maintained 95+6 reproducibility contract.

The upstream Ubuntu snapshot identity remains `20260829T022000Z`; the corrected SupraLINUX durable slice has the separate immutable identity `20260829T022000Z-r2`.

## Selected execution infrastructure

The selected KSQ source-build path is:

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
- **PASS / ACCEPTED**;
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

### Orders 061-065 — native r2 + KWallet package gate

Exact source-build evidence:

- build run `33805321380`;
- build artifact `9913134271`;
- artifact digest `sha256:035b5930f3821d764f51f7bf4b3bd2b8e82a302539e70c2c612b93f41d3e2e65`;
- exact prior checkpoint `275` DEBs verified before order 61;
- orders `61..65`, sources `5/5 PASS`;
- new DEBs `20`;
- accumulated DEBs `295`.

The source-build run's first-generation KWallet enforcement was not accepted as final authority. The exact already-built artifact was independently revalidated after the validator defects were investigated to root cause; no candidate package was rebuilt or changed for those corrections.

Exact successful post-validation:

- run `33819688197`;
- commit `b35215edfa408fa2f13f2bf34d2afbbaa96c1f3a`;
- artifact `9917851669`;
- digest `sha256:12b398c5f7388844861cca60f3fac37256eb94b3a32f57a31df8802bdf258a5c`;
- **SUCCESS**.

Independent fail-closed acceptance of that exact evidence:

- workflow `.github/workflows/ksq-accept-061-065-r2-kwallet-sidecar.yml`;
- run `33821228782`;
- commit `5b021477f00ab97e03b19e19da4e681abd7af7c0`;
- artifact `9918320108`;
- artifact digest `sha256:50c33e99c7593ce6b8d4a67c8ee11c1598ad93545ed362078a57410c4a892730`;
- **SUCCESS**;
- downloaded artifact independently verifies both its relative `evidence.sha256` and top-level `artifact-manifest.sha256` after relocation.

The maintained r2 candidate is therefore accepted through **order 65**, with **295 accumulated DEBs**.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_061_065_KWALLET.md`.

## Checkpoint-chain hardening

`scripts/ci/restore-ksq-1-checkpoint-chain.py` is the fail-closed checkpoint restorer. It validates contiguous source-order coverage, PASS state, internal manifest identities, every DEB SHA-256, filename/package uniqueness and exact cumulative counts before reconstructing the candidate set.

The accepted binary build chain through order 65 is exactly:

- 001-020 artifact `9818465016`;
- 021-040 artifact `9824689982`;
- 041-043 r2 artifact `9892762100`;
- 044-060 r2 artifact `9900367299`;
- 061-065 r2 build artifact `9913134271`, whose KWallet package/install/PAM scope is accepted only in conjunction with post-validation artifact `9917851669` and independent acceptance artifact `9918320108`.

The newer native artifacts retain a top-level `build/` directory; consumers must account for that layout explicitly. The failed run `33777276308` demonstrated this fail-closed by rejecting an incorrect artifact root before any source build began.

## KWallet PAM native validation

Order 65 is `kwallet-pam`. The old Docker/root/custom-AppArmor validator is rejected for the current architecture.

The accepted gate proves the exact package/install closure without broadening r2. The KWallet solver selects `375` packages under normal/default APT Recommends semantics. Exactly `372` package objects are available through the immutable r2/Supra inputs and exactly three Ubuntu runtime objects are outside r2's build-closure purpose:

- `lsb-base=11.6build1`;
- `libwrap0=7.6.q-36build2`;
- `socat=1.8.1.1-1ubuntu0.1`.

Those three objects remain a separate immutable, independently validated runtime extension:

- ID `20260829T022000Z-kwallet-runtime-r1`;
- release `382325880` / tag `ksq-kwallet-runtime-20260829T022000Z-r1`;
- archive asset `543326513`, SHA-256 `89f9861d061a68498950bddb96b1f22ed41ddd205db118719f23b8836284b40e`;
- manifest asset `543326512`, SHA-256 `40a2a1f2e720dd07c93ecdfc52c42b1cd2202a495a749d2722109028cbdf0c32`;
- independent validation artifact `9912479235`, digest `sha256:6ae93f1906617e67734ca5afa6e675ec47aec2f27a7e0a0799c76145b84e8f1c`.

For the isolated installation proof, the accepted post-validator uses:

- `mmdebstrap --mode=unshare --variant=apt`, not `minbase`, so unrelated `Priority: required` bootstrap packages are not incorrectly folded into the KWallet runtime closure;
- explicit `Apt::Install-Recommends "true"` so installation policy matches the proven 375-package solver policy;
- the immutable r2 mirror, exact accumulated Supra candidate DEBs and exact three-object sidecar only;
- blocked HTTP/HTTPS package transport;
- resolved Ubuntu 26.04 host `chroot` path `/usr/bin/chroot`, owned by `coreutils-from-uutils`, instead of assuming the historical GNU `/usr/sbin/chroot` path.

Accepted evidence proves:

- exact solver selection `375`;
- exact selected package/version pairs installed `375/375 PASS`;
- total isolated rootfs package count `396` (375 selected packages plus the separate APT bootstrap consequences);
- `mmdebstrap` RC `0`;
- `apt-get check` success;
- exact installed candidate versions;
- `pam_kwallet5.so` registered in `common-auth` and `common-session`;
- relevant AppArmor denials `0`;
- Docker/custom AppArmor `0`;
- no HTTP/HTTPS package transport.

This gate certifies package relationships, local installation and PAM registration. Runtime session automatic unlock remains a later end-to-end functional certification and is explicitly recorded as:

`AURORA_KSQ_1_KWALLET_RUNTIME_AUTO_UNLOCK_CERTIFIED=no`

## Reproducibility contract

KSQ-1 retains the 95+6 contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against independent reference evidence;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final patched candidate.

Order 68 `drkonqi` may be built in the next range for dependency progress, but a range PASS does **not** satisfy its later dedicated reproducibility obligation.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- upstream Ubuntu snapshot: **20260829T022000Z / FIXED**;
- canonical local slice: **20260829T022000Z-r2 / INDEPENDENTLY VALIDATED**;
- GitHub-hosted Ubuntu 26.04 native unshare architecture: **QUALIFIED / SELECTED**;
- maintained 001-020: **PASS / ACCEPTED**;
- maintained 021-040: **PASS / ACCEPTED**;
- maintained 041-043 r2: **PASS / ACCEPTED**;
- maintained 044-060 r2: **PASS / ACCEPTED**;
- maintained 061-065 r2: **PASS / ACCEPTED**;
- KWallet order-65 package/install/PAM gate: **PASS / ACCEPTED**;
- KWallet runtime session auto-unlock: **NOT CERTIFIED HERE**;
- accumulated candidate through order 65: **295 DEBs**;
- orders 066-080: **UNBLOCKED / NEXT ACTIVE BUILD UNIT**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.

Orders 66–80 currently have no declared packaging adaptation in `tests/kde-stack/ksq-1-packaging-adaptations.tsv`; their native range gate must therefore fail closed unless all 15 prepared-source evidence records show zero applied adaptations.
