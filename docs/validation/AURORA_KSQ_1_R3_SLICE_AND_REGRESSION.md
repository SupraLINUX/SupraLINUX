# Aurora KSQ-1 — immutable r3 slice and accepted-order-65 regression

Status: **r3 MATERIALIZED / INDEPENDENTLY VALIDATED — accepted-order-65 regression PASS**

This record covers creation of the corrective Ubuntu payload slice `20260829T022000Z-r3` and the regression required before any later KSQ-1 range may consume it. It does not accept orders 66–101 and does not close KSQ-1.

## 1. Fixed input

- Ubuntu release: `26.04 LTS Resolute`;
- architecture: `amd64`;
- Ubuntu Snapshot Service timestamp: `20260829T022000Z`;
- APT Recommends policy: normal/default;
- certified build-order SHA-256: `9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`;
- predecessor slice: immutable `20260829T022000Z-r2`;
- predecessor binary objects: `1783`;
- predecessor binary bytes: `785219274`.

r2 remains immutable. r3 has a distinct identity and does not replace or overwrite r2 evidence.

## 2. Authoritative build-context witness input

A current real sbuild witness rebuilt all sources 66–101 from the accepted order-65 checkpoint against the same fixed Ubuntu snapshot.

Parent witness:

- run `33929720702`;
- HEAD `84596eaf2f7d7735b74f48a48fdde82229500f7a`;
- 66–80: 15/15 builds SUCCESS;
- 81–90: 10/10 builds SUCCESS;
- 91–101: 11/11 builds SUCCESS;
- total: **36/36 source builds SUCCESS**;
- new packaging adaptations in 66–101: `0`.

The parent run's global failure came only from its obsolete embedded analysis job. No build range failed.

Independent explicit analysis:

- run `33962296018`;
- artifact `9968317241`;
- artifact digest `sha256:b7db4224c5bd7cd89f6e274cb8a0c617327bc917cee1185cff9e0b2a07ea0694`;
- analyzer HEAD `b3ce2817f207e2d37e7ba041938b5dfa52ae1bb1`;
- witness status: `PROVEN`;
- sources/logs: `36 / 36`;
- observed package objects: `1114`;
- observed bytes: `492106800`;
- r2 objects: `1783`;
- exact r2 set difference: **3 objects / 547318 bytes**;
- signed metadata policy: `apt-verified-snapshot-packages`;
- manual package additions: `0`.

The artifact's `evidence.sha256` was verified before r3 materialization.

## 3. Machine-derived gap

The complete witness-derived gap is:

| Package | Version | Filename | Size | SHA-256 | Witness order(s) |
|---|---|---|---:|---|---|
| `libcurl4-openssl-dev` | `8.18.0-1ubuntu2.4` | `pool/main/c/curl/libcurl4-openssl-dev_8.18.0-1ubuntu2.4_amd64.deb` | 544358 | `997e26288998c0243109bf60b4f8c9a90b6f3613c30e58c977e4ad0a8b84b2c7` | 75 `flatpak-kcm` |
| `libjpeg-dev` | `8c-2ubuntu12` | `pool/main/libj/libjpeg8-empty/libjpeg-dev_8c-2ubuntu12_amd64.deb` | 1480 | `6606cd1c27def2b3d7290b7dff160a282bd04c4307bc94e9edfff529ad1c6c52` | 74 `xdg-desktop-portal-kde`, 91 `print-manager` |
| `libjpeg8-dev` | `8c-2ubuntu12` | `pool/main/libj/libjpeg8-empty/libjpeg8-dev_8c-2ubuntu12_amd64.deb` | 1480 | `a78cf5d66c47f957441c019ab2316a028bb14ee70fb503cc4fad35ec2ac467ff` | 74 `xdg-desktop-portal-kde`, 91 `print-manager` |

These rows are **derived output evidence**, not manually maintained package seeds. The materializer consumes the witness result and re-resolves each object against the preserved signed Ubuntu package metadata.

The result agrees 3/3 with the older historical regression oracle, while the current witness additionally covers orders 99–101.

## 4. r3 materialization and publication

Materialization/publication run:

- run `33964548214`;
- slice ID: `20260829T022000Z-r3`;
- release tag: `ksq-snapshot-20260829T022000Z-r3`;
- archive: `aurora-ubuntu-snapshot-20260829T022000Z-r3-amd64.tar`;
- archive bytes: `1055590400`;
- archive SHA-256: `cb904b478afe186b96823b1b2872d5937517e3de10c6d2dd3170ec29fea09bc6`;
- manifest: `aurora-ubuntu-snapshot-20260829T022000Z-r3-amd64.env`;
- manifest SHA-256: `b683797c7850c47bcd6d80e093504301deac05e78010f6395af0885fb9ce005e`;
- binary objects: `1786`;
- binary payload bytes: `785766592`;
- exact delta versus r2: `3` objects / `547318` bytes;
- manual package additions: `0`.

The arithmetic is exact:

- objects: `1783 + 3 = 1786`;
- bytes: `785219274 + 547318 = 785766592`.

r3 preserves the signed Ubuntu package universe inherited from the same fixed snapshot and materializes the previously absent proven payload objects. It does not introduce new package versions/providers into the signed metadata universe.

## 5. Independent r3 validation

Independent validation run:

- run `33964782073`;
- artifact `9969086882`;
- artifact size `3736`;
- artifact digest `sha256:6fc4c3cae63f53d5484d1e5c168f51c01fb285af5697bc6f1f8438a2cb899907`.

The independent validator proved:

- publication identity: PASS;
- exact slice ID: PASS;
- strict r2 extension: PASS;
- signed metadata identity: PASS;
- all pre-existing r2 binary identities byte-preserved: PASS;
- source-input identity: PASS;
- exact witness gap: PASS;
- manual package additions: `0`;
- r2 canonical evidence not mutated: PASS.

At this point r3 was a technically validated candidate slice, not yet authorized to inherit the accepted order-65 checkpoint.

## 6. Required regression of accepted orders 1–65

Adding payload availability can in principle alter later acquisition results, so previous PASS evidence was not carried forward by assumption.

The regression examined every accepted build log through order 65 and compared its Ubuntu acquisitions against the r3 delta.

Final successful regression:

- run `33965237362`;
- source HEAD `0146e50b1143b56d56af2fab089c6a483aa240c9`;
- artifact `9969240177`;
- artifact size `181246`;
- artifact digest `sha256:8b829f4cd81afc26c340d727561b2ea2c5438487c4e1a945ce01f1eaa940165f`.

Proven results:

- exact accepted checkpoint restored: order `65`;
- accepted candidate DEBs: `295`;
- accepted successful source build logs: `65`;
- Ubuntu acquisition events: `28215`;
- unique Ubuntu package identities acquired by those builds: `1052`;
- r3 delta objects: `3`;
- r3 delta bytes: `547318`;
- intersection between accepted 1–65 acquisition identities and the r3 delta: **0**;
- all historical payload identities needed by accepted 1–65 evidence physically present in r3: PASS.

Therefore a full source rebuild of 1–65 is not required solely because r3 materialized three payloads already present in the same signed package universe. This is an evidence-based equivalence result, not a blanket rule for future slice changes.

## 7. KWallet regression under r3

KWallet was replayed rather than inherited by assumption.

The regression proved:

- original accepted solver selection: `375` packages;
- current r3 solver selection: `375` packages;
- exact package/version selection identity: PASS;
- selected package installation: PASS;
- runtime sidecar identity unchanged: PASS;
- local-only APT/package transport: PASS;
- AppArmor denials: `0`.

The sidecar remains `20260829T022000Z-kwallet-runtime-r1` and is not merged into r3.

Certification scope remains unchanged:

- package relationships: certified;
- complete local selected-package installation: certified;
- PAM registration: certified;
- runtime login/session automatic KWallet unlock: **NOT CERTIFIED**.

## 8. Generic local buildd bootstrap regression

The same regression successfully recreated a generic build environment from r3 using:

`mmdebstrap --mode=unshare --variant=buildd`

with local-only r3 APT inputs.

Result:

- bootstrap: PASS;
- external package transport: none;
- Docker: `0`;
- custom AppArmor profile: `0`;
- uidmap/file-capability hack: `0`;
- relevant AppArmor denials: `0`.

## 9. Local APT configuration isolation correction

A later 66–80 pre-build run `33965423386` exposed a tooling defect before any source build: although its package sources were local, APT still loaded host `/etc/apt/apt.conf.d` fragments, including command-not-found configuration, and attempted to acquire `cnf/Commands-amd64` metadata from the local slice.

This did not prove missing r3 build payload. It proved incomplete APT configuration isolation.

Commit `1f034d99c604a11918a673db9a9e49e9d717221a` fixes the helper by setting `Dir::Etc::Parts` and `Dir::Etc::main` inside the early `APT_CONFIG` preload itself. A subsequent clean run proved:

`AURORA_KSQ_1_LOCAL_APT_HOST_FRAGMENTS=disabled`

and completed local APT metadata preparation without CNF/Components acquisition.

A second pre-build run `33972965871` then failed only because its workflow compared generated DAG files against a non-versioned ephemeral `build/ksq-0/canonical` path absent in a clean checkout. The generated build-order SHA-256 was nevertheless exactly the certified value. That workflow assumption was removed rather than materializing hidden runner state.

## 10. Downstream authorization boundary

The accepted KSQ-1 checkpoint remains **order 65 / 295 DEBs** until the next real local-only range receives independent acceptance.

The current 66–80 path must prove all of the following before checkpoint promotion:

- exact independently validated r3 provenance;
- exact accepted-order-65 r3 regression provenance;
- 15/15 source builds PASS;
- `sbuild --no-enable-network` for every build;
- isolated network namespace evidence in every `.build` log;
- zero external HTTP package transport during source builds;
- zero relevant AppArmor denials;
- zero Docker/custom AppArmor/uidmap-filecap hacks;
- zero new packaging adaptations in orders 66–80;
- correct source/build/binary manifests and hashes;
- independent post-build acceptance artifact.

Order 68 `drkonqi` may pass its normal range build without satisfying its separate reproducibility obligation.

`DRKONQI_REPRODUCIBILITY_CERTIFIED=no`

remains mandatory until its dedicated independent rebuild proof passes.

## 11. Gate state after r3 regression

- r2: **IMMUTABLE / historical / proven universal-payload under-closure**;
- build-context witness 66–101: **PROVEN**;
- witness gap: **3 objects / 547318 bytes**;
- r3: **MATERIALIZED / INDEPENDENTLY VALIDATED**;
- r3 accepted-order-65 regression: **PASS**;
- accepted KSQ-1 checkpoint: **order 65 / 295 DEBs**;
- KWallet regression under r3: **PASS**;
- KWallet auto-unlock: **NOT CERTIFIED**;
- orders 66–80: **NOT ACCEPTED until local-only build + independent acceptance**;
- orders 81–101: **NOT ACCEPTED**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
