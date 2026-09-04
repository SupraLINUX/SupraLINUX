# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This is the current engineering status of KSQ-1. It is not an acceptance record and does not authorize entry into KSQ-2.

- KSQ-0: **CERTIFIED / CLOSED**.
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
- KSQ-2: **BLOCKED**.
- C4.1: **PAUSED**.

## Fixed contract

KSQ-1 consumes the certified 101-source DAG, Ubuntu Resolute snapshot `20260829T022000Z`, and the exact package/source identities established by KSQ-0.

The selected maintained source-build architecture is:

`GitHub-hosted Ubuntu 26.04 -> immutable local snapshot slice -> mmdebstrap --mode=unshare --variant=buildd -> sbuild --chroot-mode=unshare --no-enable-network`

The maintained path does not use Docker, privileged containers, host AppArmor relaxation, a custom AppArmor profile, or the historical uidmap file-capability rewrite.

Canonical build-order SHA-256:

`9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

## Immutable r2 input

The accepted-through-order-65 evidence uses the immutable slice `20260829T022000Z-r2`:

- upstream snapshot: `20260829T022000Z`;
- release ID: `381836501`;
- tag: `ksq-snapshot-20260829T022000Z-r2`;
- archive asset: `542414026`;
- archive bytes: `1054177280`;
- archive SHA-256: `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`;
- manifest asset: `542414028`;
- manifest SHA-256: `6ed95b495ded7744f081335684c2918eeae96dbc822fa53b0d9fb5bc2da0f481`;
- generic `amd64`, architecture variants disabled;
- normal/default APT Recommends policy;
- 244 certified binary/version seeds;
- 1783 binary `.deb` objects / `785219274` bytes;
- 301 Ubuntu source objects;
- 4 Debian source objects.

Independent r2 publication validation remains PASS. r2 is immutable and remains the exact input of the already accepted build evidence through order 65.

r2 is **not** being mutated to correct later closure deficiencies.

## Accepted maintained checkpoint chain

### Orders 001–020

- run `33546093974`;
- artifact `9818465016`;
- digest `sha256:0eb45c7938b84db35ee734591622a6c621709117100d29376c01323ca0ab14ba`;
- 20/20 sources PASS;
- accumulated DEBs: `103`.

### Orders 021–040

- run `33561782526`;
- artifact `9824689982`;
- digest `sha256:08dffb19fe6d3fda5b8079ed862d3215440cfabaf51a249f79b5af49d3539d8e`;
- 20/20 sources PASS;
- accumulated DEBs: `192`.

### Orders 041–043 — r2 regression

- run `33753437984`;
- artifact `9892762100`;
- digest `sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0`;
- 3/3 sources PASS;
- accumulated DEBs: `205`.

### Orders 044–060

- run `33767306768`;
- artifact `9900367299`;
- digest `sha256:41a50bb17ea5ca4ab63c43a6aa6d6d030dae310ba716866824ac72d6c61dc4f3`;
- 17/17 sources PASS;
- accumulated DEBs: `275`.

### Orders 061–065 + KWallet package/install/PAM gate

Build evidence:

- run `33805321380`;
- artifact `9913134271`;
- digest `sha256:035b5930f3821d764f51f7bf4b3bd2b8e82a302539e70c2c612b93f41d3e2e65`;
- 5/5 sources PASS;
- 20 new DEBs;
- accumulated DEBs: `295`.

Independent post-validation:

- run `33819688197`;
- artifact `9917851669`;
- digest `sha256:12b398c5f7388844861cca60f3fac37256eb94b3a32f57a31df8802bdf258a5c`;
- SUCCESS.

Independent fail-closed acceptance:

- run `33821228782`;
- artifact `9918320108`;
- digest `sha256:50c33e99c7593ce6b8d4a67c8ee11c1598ad93545ed362078a57410c4a892730`;
- SUCCESS.

The maintained candidate is accepted through **order 65 / 295 accumulated DEBs**.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_061_065_KWALLET.md`.

## KWallet scope

The accepted order-65 solver selects exactly `375` packages. Exactly three runtime objects needed by that isolated installation proof are outside r2's build-closure purpose:

- `lsb-base=11.6build1`;
- `libwrap0=7.6.q-36build2`;
- `socat=1.8.1.1-1ubuntu0.1`.

They remain in the separate immutable runtime sidecar `20260829T022000Z-kwallet-runtime-r1`:

- release `382325880`;
- archive asset `543326513`, SHA-256 `89f9861d061a68498950bddb96b1f22ed41ddd205db118719f23b8836284b40e`;
- manifest asset `543326512`, SHA-256 `40a2a1f2e720dd07c93ecdfc52c42b1cd2202a495a749d2722109028cbdf0c32`;
- independent validation artifact `9912479235`, digest `sha256:6ae93f1906617e67734ca5afa6e675ec47aec2f27a7e0a0799c76145b84e8f1c`.

This certifies package relationships, local installation and PAM registration. Runtime session automatic unlock is still explicitly **not certified** in this gate.

## Orders 066–080: r2 blocker

The first maintained 66–80 attempt is run `33821750759`, artifact `9919609367`, digest `sha256:e04615715fcee3450c14db3f1a7085d09cd937c7db8d2520c0bff49f60546998`.

Orders 66–73 built successfully inside that run but are **not accepted as a checkpoint** because the range failed at order 74 `xdg-desktop-portal-kde`.

The order-74 failure is a local-slice payload under-closure, not a KDE source/Build-Depends defect. Real `sbuild` dependency resolution selected:

- `libjpeg-turbo8-dev=2.1.5-4ubuntu4`;
- `libjpeg8-dev=8c-2ubuntu12`;
- `libjpeg-dev=8c-2ubuntu12`.

r2 contains the first payload but not the two `libjpeg8-empty` development payloads advertised by its own signed metadata.

Controlled A/B run `33862761542`, artifact `9933323436`, digest `sha256:4cdc54e59e77238cfc9d8c9c238e8dc947fb531241dcb43a3263f6278db7f987`, proves the root cause:

- the original aggregate 244-seed r2 transaction selects `libjpeg-turbo8-dev` but omits `libjpeg8-dev` and `libjpeg-dev`;
- isolated direct `libcups2-dev=2.4.16-1ubuntu1.3` selects all three;
- an isolated sbuild-style dependency dummy with the same `libcups2-dev` relation also selects all three.

Therefore the sbuild dummy model is not the cause. The invalid assumption was that one aggregate APT transaction over the Build-Depends seeds of many independent sources necessarily yields a payload superset of every real per-source build transaction. It does not: provider/transition-package decisions change with transaction context.

Detailed causal record: `docs/validation/AURORA_KSQ_1_RANGE_066_080_R2_BLOCKER.md`.

## Corrective witness now active

No missing package is being appended manually, no package source is being patched, and r2 is not being modified.

The active correction is workflow:

`.github/workflows/ksq-snapshot-build-context-witness-066-101.yml`

It reconstructs the exact accepted order-65 state, then executes current real build contexts in three sequential witness ranges:

- 66–80;
- 81–90;
- 91–101.

The package build itself keeps `sbuild --no-enable-network`. During this explicitly non-acceptance witness phase, APT may retrieve Build-Depends only from the fixed timestamped Ubuntu snapshot `20260829T022000Z` so the exact package/version selections of each real build can be observed.

The final analyzer maps those observed selections through APT-verified signed snapshot `Packages` metadata to exact `Filename`, `Size` and `SHA256`, unions all 36 source-build contexts, and computes the exact set difference against the 1783 r2 objects.

Only that machine-derived complete difference can be considered as input to a new immutable slice. The historical three observed gaps (`libjpeg8-dev`, `libjpeg-dev`, `libcurl4-openssl-dev`) are regression oracles only, not a manual inclusion list.

A future replacement slice will have a new immutable identity and must be independently materialized and validated. Because the snapshot input changes, required earlier regressions must be re-run before previous PASS evidence can be carried forward.

## Reproducibility contract

KSQ-1 retains the maintained 95+6 contract:

- 95 unaffected source nodes require exact prepared-source identity and byte-identical DEBs against independent reference evidence;
- orders 29, 68, 81, 99, 100 and 101 require dedicated independent rebuild proof against the final candidate.

A witness or range PASS does not satisfy those dedicated reproducibility obligations.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- Ubuntu snapshot: **20260829T022000Z / FIXED**;
- r2 slice: **IMMUTABLE / independently validated / accepted input through order 65**;
- r2 as complete 101-source build payload closure: **REJECTED / proven under-closed**;
- r2 aggregate-closure root cause: **PROVEN**;
- maintained 001–065: **PASS / ACCEPTED**;
- accumulated accepted candidate: **295 DEBs**;
- orders 066–080: **BLOCKED ON r2 / NOT ACCEPTED**;
- orders 081–101: **NOT ACCEPTED**;
- per-build snapshot closure witness 066–101: **ACTIVE**;
- complete 101-source candidate: **NOT ACCEPTED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
