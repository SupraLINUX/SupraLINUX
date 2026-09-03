# Aurora KSQ-1 snapshot r2 and range 041-043 qualification

Status: **SNAPSHOT R2 ACCEPTED / RANGE 041-043 PASS / KSQ-1 ACTIVE**

This record closes the KSQ-1 blocker that appeared at build order 43 (`kpipewire`) and records the corrected immutable local snapshot input used by the maintained native builder.

This is not KSQ-1 final acceptance. Orders 044-101, the KWallet local validator, the final 101-source validator and complete reproducibility evidence remain open.

## Fixed upstream identity

KSQ-0 remains closed and continues to select Ubuntu Resolute snapshot:

`20260829T022000Z`

The source DAG, selected source/package identities and build order are unchanged. Snapshot r2 changes only the durable SupraLINUX local slice closure needed to reproduce the effective APT/sbuild dependency policy.

The corrected SupraLINUX slice has its own immutable identity:

`20260829T022000Z-r2`

Separating these identities prevents a corrected local materialization from pretending to be a different Ubuntu archive snapshot or overwriting the historical r1 engineering release.

## Proven root cause

The historical local slice contained the closure generated with explicit:

`apt-get --no-install-recommends`

That closure contained:

- 1541 binary objects;
- 704826504 binary bytes.

The real KSQ builder uses `sbuild 0.91.2ubuntu3` with its normal APT resolver behavior. Normal APT dependency resolution considers Recommends unless explicitly disabled. `pipewire-bin` in the selected Resolute snapshot declares `Recommends: dbus-user-session`.

The historical range 041-043 run therefore reached order 43 and failed during `install-deps` when APT requested:

`dbus-user-session_1.16.2-2ubuntu4_amd64.deb`

but that object had never been materialized into r1.

Historical failure evidence:

- run `33725437853`;
- artifact `9882029309`;
- artifact digest `sha256:d22cf54b2c2f2eddfe2674c45cff4d751f910a4dac3b7d81bb8562262c510acc`;
- order 41 `kf6-kunitconversion`: PASS;
- order 42 `knighttime`: PASS;
- order 43 `kpipewire`: FAIL;
- fail stage: `install-deps`;
- 7 DEBs produced before the failure;
- build-manifest SHA-256 `81db3a82b84b1620d89b3ae991c76bdc11a559c560c07c6a2cb906d34709189a`;
- `new-debs.sha256` file SHA-256 `697cec4f56368b8288a9a368b198f2a9064d67de82231041ca26018770e2590e`.

No package change was inferred from this symptom.

## Controlled Recommends A/B proof

Native A/B workflow:

`.github/workflows/ksq-native-snapshot-recommends-closure-ab.yml`

Accepted proof:

- commit `01855661b1bee5419869d2fae1d928d44babe11e`;
- run `33729123389`;
- artifact `9883165109`;
- digest `sha256:0b617d25f575efead1dbe904eb24cc1b31df94a3f07ce32a7dbd25fc1327c20d`.

Results on the same Ubuntu snapshot and exact 244 version-pinned seeds:

| Policy | Objects | Bytes |
|---|---:|---:|
| explicit no-Recommends | 1541 | 704826504 |
| APT default Recommends | 1783 | 785219274 |

The historical object set is exactly the explicit no-Recommends closure after controlling the architecture variant. The default closure contains `dbus-user-session`, `rtkit`, `wireplumber` and the other normally selected Recommends-side objects.

The A/B also exposed a separate host-dependent variable: the GitHub-hosted image could select optimized `amd64v3` package objects. Aurora's qualification architecture is generic `amd64`, so the corrected closure explicitly disables `APT::Architecture-Variants`. The accepted r2 closure contains the generic amd64 object and no `dbus-user-session ... amd64v3` object.

## Native corrected closure generator

The historical Docker-based size/closure calculation is no longer the canonical closure generator.

Native replacement evidence:

- commit `df6e7954506a9bf38a64685ddf84950ca97a5af6`;
- workflow `.github/workflows/ksq-snapshot-slice-size-probe.yml`;
- run `33729384695`;
- artifact `9883249125`;
- digest `sha256:2281ab4655dc8d33639d9a3bbfb75d60325829a6b0af19902c20e4406e0c945b`;
- Ubuntu 26.04 native host;
- default Recommends;
- generic amd64 / architecture variants disabled;
- 244 certified seeds;
- 1783 binary objects / 785219274 bytes;
- 301 Ubuntu source objects;
- 4 Debian source objects.

## Corrected immutable slice r2

Materializer and publication:

- `scripts/ci/ksq-snapshot-slice-r2.py`;
- `.github/workflows/ksq-snapshot-slice-r2-materialize.yml`;
- materializer commit `2732374413f5391867df801e8c9538c425be1e9d`;
- publication run `33729892275`;
- publication job `100567186893`: PASS;
- independent re-download/validation job `100569481825`: PASS.

Engineering Release:

- Release ID `381836501`;
- tag `ksq-snapshot-20260829T022000Z-r2`;
- archive asset ID `542414026`;
- archive `aurora-ubuntu-snapshot-20260829T022000Z-r2-amd64.tar`;
- archive bytes `1054177280`;
- archive SHA-256 `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`;
- manifest asset ID `542414028`;
- manifest SHA-256 `6ed95b495ded7744f081335684c2918eeae96dbc822fa53b0d9fb5bc2da0f481`.

Independent validation evidence:

- artifact `9883714959`;
- digest `sha256:c628aadcb577d5d1777ebf0b6d6c2e0d9c737fbfc82aa920e60f624a30c23b36`;
- validated files `2184`;
- validated disk bytes `1051413123`;
- Ubuntu signed metadata validation: PASS.

The canonical pointer is `scripts/ci/aurora-ksq-snapshot-release.env`, promoted in commit `880f1e3298f195029b9b45a15372ee9efb91305e` with status `INDEPENDENTLY_VALIDATED`.

## Isolated order 43 causal retest

Before rerunning the complete range, order 43 was retested alone. Orders 41/42 from the failed historical run were used only as a temporary causal checkpoint; they were explicitly not promoted as r2 qualification evidence.

Accepted isolated proof:

- workflow `.github/workflows/ksq-native-order-043-r2-probe.yml`;
- commit `bf5c14ddc14770532fa8f5e3611c05797816a4bc`;
- run `33752870935`;
- job `100640242141`;
- artifact `9892373802`;
- digest `sha256:43e8abc95d0eeb57952488ce4b48653a8c736d0de48f166259d9cd5f15891b82`;
- result PASS;
- command RC `0`;
- tee RC `0`;
- AppArmor denials `0`;
- new DEBs `6`;
- accumulated temporary DEBs `205`;
- build network isolated with loopback only and zero IPv4 routes.

The build log proves local installation of `dbus-user-session 1.16.2-2ubuntu4` and successful `kpipewire` completion.

## Mandatory full range 041-043 r2 regression

Because changing the snapshot slice invalidates affected prior range evidence, the temporary checkpoint was not accepted as final. Orders 41, 42 and 43 were rebuilt from the exact certified 001-040 checkpoint against r2.

Accepted regression:

- workflow `.github/workflows/ksq-native-range-041-043-r2-regression.yml`;
- commit `67ca6afd74373b2d52bcf40fd6321ec9fe615ba3`;
- run `33753437984`;
- job `100642085362`;
- artifact `9892762100`;
- artifact digest `sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0`;
- result PASS.

Range result:

| Order | Source | Candidate version | DEBs | Result |
|---:|---|---|---:|---|
| 41 | `kf6-kunitconversion` | `6.29.0-0ubuntu1~supra26.04.1` | 4 | PASS |
| 42 | `knighttime` | `6.7.4-0ubuntu1~supra26.04.1` | 3 | PASS |
| 43 | `kpipewire` | `6.7.4-0ubuntu2~supra26.04.1` | 6 | PASS |

Regression invariants:

- prior exact checkpoint: 192 DEBs from orders 001-040;
- new DEBs: 13;
- accumulated DEBs: 205;
- command RC `0`;
- tee RC `0`;
- AppArmor relevant denials `0`;
- external HTTP/HTTPS acquisition from the build logs `0`;
- Docker used `0`;
- custom AppArmor profile used `0`;
- uidmap file-capability rewrite used `0`;
- build-manifest SHA-256 `e4311aeba5c7856ac2c0ff803c9adc2fdcb63adb104d1a8f2707a1fc45696ab1`;
- `new-debs.sha256` file SHA-256 `d5e6cbd51cac0ac2d2dca953722ccbd1a43beb3c981766f683ae69ace539105c`.

## Decisions and non-decisions

This investigation changed the durable local snapshot closure because the previous closure calculation was proven inconsistent with the real builder's dependency semantics.

It did **not**:

- manually add `dbus-user-session` as a one-off exception;
- patch or otherwise change `kpipewire`;
- force `sbuild` to disable Recommends;
- change the certified KDE source DAG;
- change Ubuntu snapshot `20260829T022000Z`;
- disable or relax host AppArmor;
- add Docker privilege or `CAP_SYS_ADMIN`;
- change kernel, Mesa, Wayland, Qt, PipeWire or another Ubuntu platform layer.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- upstream Ubuntu snapshot: **20260829T022000Z / unchanged**;
- canonical local slice: **20260829T022000Z-r2 / independently validated**;
- Recommends closure mismatch: **ROOT CAUSE PROVEN / CORRECTED**;
- isolated order 43 r2: **PASS**;
- complete range 041-043 r2 regression: **PASS**;
- maintained candidate through order 43: **205 accumulated DEBs**;
- orders 044-060: **NOT YET QUALIFIED ON R2**;
- KWallet PAM local-only validator: **IMPLEMENTED / NOT YET QUALIFIED**;
- 061-080: **BLOCKED UNTIL 041-060 CLOSES AND KWALLET LOCAL VALIDATION PASSES**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
