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

No KSQ-0 decision is reopened by the local-slice correction. The upstream Ubuntu snapshot identity remains `20260829T022000Z`; the corrected SupraLINUX durable slice has the separate immutable identity `20260829T022000Z-r2`.

## Selected execution infrastructure

The selected KSQ execution host is GitHub-hosted `ubuntu-26.04` with the native unshare path:

`Ubuntu 26.04 runner -> local immutable snapshot slice -> mmdebstrap --mode=unshare --variant=buildd -> sbuild --chroot-mode=unshare`

The current maintained qualification path does **not** use Docker, privileged containers, outer `CAP_SYS_ADMIN`, host AppArmor relaxation or a custom AppArmor profile.

GitHub labels `ubuntu-26.04` Public Preview. Ubuntu 26.04 LTS itself is stable; the preview status belongs to external CI infrastructure. SupraLINUX therefore accepts the runner only through fail-closed qualification of the exact behavior required by KSQ and rechecks relevant host/tool/security invariants per workflow.

## Canonical corrected snapshot input

Repository pointer:

`scripts/ci/aurora-ksq-snapshot-release.env`

Current immutable local slice:

- upstream Ubuntu snapshot: `20260829T022000Z`;
- Supra slice identity: `20260829T022000Z-r2`;
- status `INDEPENDENTLY_VALIDATED`;
- generic architecture `amd64`;
- `APT::Architecture-Variants` disabled for slice materialization;
- APT Recommends policy: default;
- Release ID `381836501`;
- tag `ksq-snapshot-20260829T022000Z-r2`;
- archive asset ID `542414026`;
- archive `aurora-ubuntu-snapshot-20260829T022000Z-r2-amd64.tar`;
- archive bytes `1054177280`;
- archive SHA-256 `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`;
- manifest asset ID `542414028`;
- manifest SHA-256 `6ed95b495ded7744f081335684c2918eeae96dbc822fa53b0d9fb5bc2da0f481`.

The accepted r2 closure contains:

- 244 exact certified binary/version seeds;
- 1783 binary `.deb` objects;
- 785219274 binary bytes;
- 301 Ubuntu source objects;
- 4 Debian source objects.

Independent publication re-download/validation is PASS: job `100569481825`, artifact `9883714959`, digest `sha256:c628aadcb577d5d1777ebf0b6d6c2e0d9c737fbfc82aa920e60f624a30c23b36`.

## Proven r1 -> r2 root cause

The historical r1 slice was generated using explicit `apt-get --no-install-recommends`, yielding 1541 objects / 704826504 bytes. The real `sbuild 0.91.2ubuntu3` path uses normal APT dependency semantics, where Recommends are considered unless explicitly disabled.

At order 43, `pipewire-bin` caused APT to request `dbus-user-session=1.16.2-2ubuntu4`; that exact package was absent from r1 because the slice closure policy differed from the real builder policy.

Controlled native A/B run `33729123389` proved the difference on the same snapshot and 244 pinned seeds:

- explicit no-Recommends: 1541 objects / 704826504 bytes;
- default Recommends: 1783 objects / 785219274 bytes.

The correction was to rebuild the complete durable slice closure with the real builder policy, not to add `dbus-user-session` manually, patch `kpipewire`, or change `sbuild` to suppress Recommends.

Canonical detailed record: `docs/validation/AURORA_KSQ_1_SNAPSHOT_R2_RANGE_041_043.md`.

## Maintained build chain

Canonical build-order SHA-256 remains:

`9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

### Orders 001-020

- run `33546093974`, job `99983826266`;
- result **PASS**;
- artifact `9818465016`, digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`;
- 20/20 sources PASS;
- accumulated DEBs `103`.

### Orders 021-040

- run `33561782526`, job `100035734787`;
- result **PASS**;
- artifact `9824689982`, digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`;
- exact 001-020 checkpoint revalidated before order 21;
- 20/20 sources PASS;
- new DEBs `89`;
- accumulated DEBs `192`.

### Orders 041-043 — corrected r2 regression

Historical r1 range evidence is superseded for this affected segment.

The isolated causal retest of order 43 passed first:

- run `33752870935`, job `100640242141`;
- artifact `9892373802`, digest `sha256:43e8abc95d0eeb57952488ce4b48653a8c736d0de48f166259d9cd5f15891b82`;
- `kpipewire` PASS, 6 DEBs, RC 0, zero relevant AppArmor denials, zero external build acquisition.

Mandatory full regression then rebuilt orders 41, 42 and 43 from the exact 001-040 checkpoint against r2:

- commit `67ca6afd74373b2d52bcf40fd6321ec9fe615ba3`;
- run `33753437984`, job `100642085362`;
- result **PASS**;
- artifact `9892762100`;
- digest `sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0`;
- orders `41..43` all PASS;
- new DEBs `13`;
- accumulated DEBs `205`;
- build-manifest SHA-256 `e4311aeba5c7856ac2c0ff803c9adc2fdcb63adb104d1a8f2707a1fc45696ab1`;
- `new-debs.sha256` file SHA-256 `d5e6cbd51cac0ac2d2dca953722ccbd1a43beb3c981766f683ae69ace539105c`;
- command RC `0`, tee RC `0`;
- relevant AppArmor denials `0`;
- external HTTP/HTTPS build acquisition `0`.

The maintained candidate is therefore qualified through order 43 on r2. Orders 044-060 are not yet qualified on r2.

## Checkpoint-chain hardening

`scripts/ci/restore-ksq-1-checkpoint-chain.py` remains the fail-closed checkpoint restorer. Later ranges must verify contiguous source-order coverage, PASS state, expected internal manifest identities, every DEB SHA-256, filename/package uniqueness and exact cumulative counts before reconstructing the accumulated candidate set.

For the next range the accepted chain is exactly:

- 001-020 artifact `9818465016`;
- 021-040 artifact `9824689982`;
- 041-043 r2 artifact `9892762100`.

Any workflow that silently substitutes the historical r1 041-043 output is invalid.

## KWallet PAM local-only validation

The legacy remote/root-mode KWallet validation is not accepted for the current contract.

Replacement:

`scripts/ci/validate-ksq-1-kwallet-pam-local.sh`

The replacement remains **IMPLEMENTED / NOT YET QUALIFIED**. It must run on the r2 candidate chain when the build reaches `kwallet-pam`, using the same local-only unshare architecture and exact rebuilt KWallet/PAM packages. It must verify candidate package versions, dependency/substvar assertions, `apt-get check`, PAM registration in `common-auth` and `common-session`, and zero HTTP/HTTPS package acquisition.

061-080 remains blocked until 041-060 is closed and the local KWallet validator has passed on the resulting r2 candidate chain.

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
- accumulated candidate through order 43: **205 DEBs**;
- maintained 044-060 r2: **NOT YET QUALIFIED**;
- KWallet PAM local-only validator: **IMPLEMENTED / NOT YET QUALIFIED**;
- 061-080: **BLOCKED**;
- complete 101-source candidate: **NOT RUN**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
