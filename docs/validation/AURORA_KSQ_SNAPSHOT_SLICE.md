# Aurora KSQ certified snapshot slice

Status: **R2 PUBLISHED / INDEPENDENTLY VALIDATED / REPOSITORY-PINNED**

This document records the durable byte-preserved archive slice used by Aurora KSQ for upstream Ubuntu snapshot `20260829T022000Z`. The upstream snapshot identity remains fixed; the corrected local SupraLINUX slice is versioned independently as `20260829T022000Z-r2`.

The snapshot engineering input is accepted. KSQ-1 itself remains **ACTIVE / NOT CERTIFIED**.

## Certified origin

Canonical KSQ-0 closure evidence remains unchanged:

- upstream snapshot `20260829T022000Z`;
- run `33231879994`;
- artifact `9708738867`;
- digest `sha256:5b23140181ea7e7931cb744f4c43930adba8f79e446c52d0f4b1c3c568106d50`;
- closure `COMPLETE`;
- 101 source nodes;
- unresolved dependency/source decisions `0`.

The local slice is an execution/materialization artifact and does not redefine the certified source DAG or Ubuntu snapshot.

## Historical r1 and proven correction

The original local slice was materialized from the same upstream snapshot but its binary closure was calculated with explicit `apt-get --no-install-recommends`.

Historical r1 identity:

- tag `ksq-snapshot-20260829T022000Z`;
- 1541 binary `.deb` objects;
- 704826504 binary bytes;
- Release ID `380209318`;
- archive asset ID `538944111`;
- archive SHA-256 `8dc9087b53e90c085333644ffdb828b87ce0af6cd61ec5f1d516fe35e80529e7`.

Order 43 later proved that this closure did not reproduce the effective normal APT dependency semantics used by the real `sbuild` builder: `pipewire-bin` recommends `dbus-user-session`, and APT requested `dbus-user-session=1.16.2-2ubuntu4`, which r1 had never materialized.

Controlled native A/B evidence on the same snapshot and 244 exact pinned seeds:

- workflow `.github/workflows/ksq-native-snapshot-recommends-closure-ab.yml`;
- run `33729123389`;
- artifact `9883165109`;
- digest `sha256:0b617d25f575efead1dbe904eb24cc1b31df94a3f07ce32a7dbd25fc1327c20d`;
- explicit no-Recommends: 1541 objects / 704826504 bytes;
- default Recommends: 1783 objects / 785219274 bytes.

The A/B also proved a separate host-dependent architecture-variant risk. The accepted generic-amd64 closure therefore disables `APT::Architecture-Variants` during materialization so the slice does not depend on `amd64v3` host selection.

This correction is not a manual `dbus-user-session` exception and does not modify `kpipewire` or force `sbuild` into no-Recommends mode.

## Canonical corrected r2 Release

Repository pin:

`scripts/ci/aurora-ksq-snapshot-release.env`

with:

`AURORA_KSQ_SNAPSHOT_RELEASE_STATUS=INDEPENDENTLY_VALIDATED`

and distinct identities:

- `AURORA_KSQ_UBUNTU_SNAPSHOT=20260829T022000Z`;
- `AURORA_KSQ_SNAPSHOT=20260829T022000Z-r2`.

Canonical r2 materialization/publication:

- materializer `scripts/ci/ksq-snapshot-slice-r2.py`;
- workflow `.github/workflows/ksq-snapshot-slice-r2-materialize.yml`;
- materializer commit `2732374413f5391867df801e8c9538c425be1e9d`;
- publication run `33729892275`;
- publication job `100567186893`: PASS;
- independent validation job `100569481825`: PASS.

Engineering Release:

- Release ID `381836501`;
- tag `ksq-snapshot-20260829T022000Z-r2`;
- archive asset ID `542414026`;
- archive `aurora-ubuntu-snapshot-20260829T022000Z-r2-amd64.tar`;
- exact bytes `1054177280`;
- SHA-256 `23413ddf1c1820aaa01dfa81005b37e8c9611bad2d0a632664d0e08282e69c3b`;
- manifest asset ID `542414028`;
- manifest SHA-256 `6ed95b495ded7744f081335684c2918eeae96dbc822fa53b0d9fb5bc2da0f481`.

Accepted r2 closure:

- 244 certified binary/version seeds;
- 1783 binary `.deb` objects;
- `785219274` binary bytes;
- 301 Ubuntu source objects / `212283819` bytes;
- 4 Debian source objects / `161155` bytes;
- generic `amd64`;
- architecture variants disabled;
- default APT Recommends semantics.

Independent re-download/validation evidence:

- artifact `9883714959`;
- digest `sha256:c628aadcb577d5d1777ebf0b6d6c2e0d9c737fbfc82aa920e60f624a30c23b36`;
- validated files `2184`;
- validated disk bytes `1051413123`;
- Ubuntu signed metadata validation: PASS.

The Release is an engineering reproducibility input, not an Aurora product release.

## Trust model

The slice is byte-preserving. It is not a regenerated Ubuntu repository and introduces no local archive-signing key.

Ubuntu trust remains:

`Ubuntu archive key -> signed InRelease -> Packages/Sources identity -> retained object checksum`

The slice retains original signed metadata, exact selected Ubuntu pool objects, the four certified Debian `wayland-protocols 1.48-1` source objects, manifests/provenance and deterministic local APT source configuration.

## Native consumer path

The maintained KSQ consumer architecture is native GitHub-hosted Ubuntu 26.04 plus unprivileged namespaces:

`ubuntu-26.04 -> local r2 slice -> mmdebstrap --mode=unshare --variant=buildd -> sbuild --chroot-mode=unshare`

The current path does not require Docker, privileged containers, outer `CAP_SYS_ADMIN`, custom AppArmor policy or host AppArmor relaxation.

APT package/source transport inside the qualified builder is local `file:` only. Local source acquisition uses Resolute APT `Acquire::Source-Symlinks=false` so source archives are materialized as ordinary files while retaining metadata/checksum validation.

## r2 build proof through order 43

Order 43 was first retested alone against r2 to establish causality:

- run `33752870935`, job `100640242141`;
- artifact `9892373802`;
- digest `sha256:43e8abc95d0eeb57952488ce4b48653a8c736d0de48f166259d9cd5f15891b82`;
- `kpipewire`: PASS;
- six new DEBs;
- zero relevant AppArmor denials;
- zero external build acquisition.

Because changing the local slice invalidated affected prior evidence, orders 41-43 were then rebuilt from the exact qualified 001-040 checkpoint against r2:

- run `33753437984`, job `100642085362`;
- artifact `9892762100`;
- digest `sha256:7a118c3225143021056781e2b45af114e719a1e5382bda5a1819c7346312b0f0`;
- 41 `kf6-kunitconversion`: PASS;
- 42 `knighttime`: PASS;
- 43 `kpipewire`: PASS;
- 13 new DEBs;
- 205 accumulated DEBs;
- build-manifest SHA-256 `e4311aeba5c7856ac2c0ff803c9adc2fdcb63adb104d1a8f2707a1fc45696ab1`;
- `new-debs.sha256` file SHA-256 `d5e6cbd51cac0ac2d2dca953722ccbd1a43beb3c981766f683ae69ace539105c`.

Detailed record: `docs/validation/AURORA_KSQ_1_SNAPSHOT_R2_RANGE_041_043.md`.

## Execution-host policy

GitHub's `ubuntu-26.04` runner remains external Public Preview infrastructure. SupraLINUX accepts it for qualification only through explicit empirical invariant checks. A runner/kernel/security/tool change that invalidates a required property triggers regression; it does not change the pinned snapshot bytes or source identity.

## Current state

- certified upstream snapshot identity: **20260829T022000Z / FIXED**;
- historical r1 slice: **SUPERSEDED FOR CURRENT KSQ BUILD INPUT**;
- canonical r2 slice: **20260829T022000Z-r2**;
- r2 Release asset: **PUBLISHED**;
- r2 independent publication re-download/validation: **PASS**;
- repository SHA-256/byte pin: **COMMITTED**;
- r2 closure policy: **DEFAULT RECOMMENDS / GENERIC AMD64**;
- native `mmdebstrap`/`sbuild` path: **QUALIFIED THROUGH ORDER 43**;
- complete 041-043 r2 regression: **PASS**;
- orders 044-060 r2: **NOT YET QUALIFIED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
