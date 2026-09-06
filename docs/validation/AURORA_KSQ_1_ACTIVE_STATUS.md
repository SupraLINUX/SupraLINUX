# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This is the canonical current engineering status of KSQ-1. It is not a final KSQ-1 acceptance record and does not authorize entry into KSQ-2.

- KSQ-0: **CERTIFIED / CLOSED**.
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
- KSQ-2: **BLOCKED**.
- C4.1: **PAUSED**.

## Fixed product/build contract

KSQ-1 consumes the certified 101-source DAG, Ubuntu 26.04 LTS Resolute, immutable snapshot slice `20260829T022000Z-r3`, and the exact source/package decisions accepted by KSQ-0.

Maintained source-build architecture:

`GitHub-hosted Ubuntu 26.04 -> immutable local snapshot slice -> mmdebstrap --mode=unshare --variant=buildd -> sbuild --chroot-mode=unshare --no-enable-network`

Maintained builds do not use Docker, privileged containers, host AppArmor relaxation, custom AppArmor profiles, or uidmap file-capability rewrites.

Canonical build-order SHA-256:

`9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`

APT Recommends use normal/default semantics. The obsolete aggregate closure computed with `--no-install-recommends` is not used to emulate real sbuild dependency installation.

## Immutable r3 input

Slice: `20260829T022000Z-r3`.

r3 is an immutable strict extension of historical r2. It adds exactly the three payload objects proven necessary by the complete real-build witness while preserving the signed Ubuntu package universe, versions and pre-existing payload identities.

Independent r3 validation:

- run `33964782073`;
- artifact `9969086882`;
- digest `sha256:6fc4c3cae63f53d5484d1e5c168f51c01fb285af5697bc6f1f8438a2cb899907`;
- archive SHA-256 `cb904b478afe186b96823b1b2872d5937517e3de10c6d2dd3170ec29fea09bc6`;
- strict r2 extension: PASS;
- signed metadata identity: PASS;
- pre-existing payload identity: PASS;
- exact witness-gap inclusion: PASS.

Required r3 regression through the accepted order-65 boundary is PASS in run `33965237362`, artifact `9969240177`, digest `sha256:8b829f4cd81afc26c340d727561b2ea2c5438487c4e1a945ce01f1eaa940165f`.

## Maintained normal-build checkpoint — ACCEPTED THROUGH ORDER 101

The complete certified 101-source DAG now has an independently accepted normal-build checkpoint.

### Orders 001–065

Previously accepted evidence remains valid under the explicit r3 regression proof. The order-65 checkpoint is `295` accumulated DEBs.

KWallet package relationships, exact package installation and PAM registration are accepted. Runtime login/session automatic KWallet unlock remains explicitly **NOT CERTIFIED**.

### Orders 066–080

Source-build run:

- run `33973287438`;
- artifact `9972463409`;
- digest `sha256:e1c9dccad9164a8e8445ff2487fc17d61c55816bfa3c22da385c336cca3feda5`;
- 15/15 sources PASS;
- 50 new DEBs;
- accumulated DEBs `345`.

Independent acceptance:

- run `33978315934`;
- artifact `9972976872`;
- digest `sha256:ebd60471d9834efbb4fad9f5680c6a153000aa8b9393f4821a70ff148edc2511`;
- accepted checkpoint **order 80 / 345 DEBs**.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_066_080_R3.md`.

### Orders 081–090

Source-build run:

- run `33978550975`;
- artifact `9974023708`;
- digest `sha256:dfa78a851139b279f08d58bef9a0d95fc9261a26c18b6c1dc85a65afe29401ed`;
- 10/10 sources PASS;
- 31 new DEBs;
- accumulated DEBs `376`.

Independent acceptance:

- run `33994817042`;
- artifact `9977725295`;
- digest `sha256:aa4d0499623073108161750881eee06804d1a1d20e5cd45e4a83ab4de3ad7d04`;
- accepted checkpoint **order 90 / 376 DEBs**.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_081_090_R3.md`.

### Orders 091–101

Normal local-only source-build evidence:

- run `33994908104`;
- source HEAD `7f680a9eb18096bf5908abe131bc943c3564a6f4`;
- artifact `9979632407`;
- digest `sha256:0595106d646d61dcd0d65066b69f109823b00802b78ebc2e6547d3fa1eab9e42`;
- artifact size `248721436` bytes;
- 11/11 sources PASS;
- 48 new DEBs;
- accumulated DEBs `424`;
- packaging adaptations in this range `0`;
- external build APT HTTP(S) `0`;
- relevant AppArmor denials `0`.

Independent fail-closed acceptance:

- run `34002503177`;
- artifact `9979901723`;
- digest `sha256:7ac66159e76374685f88d734d52afd1398eee60e8032e8fa17abde20d117548b`;
- artifact size `8028` bytes;
- extracted `evidence.sha256`: PASS;
- accepted checkpoint **order 101 / 424 DEBs**.

`plasma-workspace`, `plasma-desktop` and `powerdevil` therefore have normal-build PASS, but their dedicated reproducibility obligations remain separate and are not satisfied by this acceptance.

## Reproducibility contract

KSQ-1 uses the fixed `95 + 6` reproducibility contract:

- 95 source nodes whose prepared inputs are unchanged may reuse independent earlier build evidence only after exact source identity, binary shape and byte-identical DEBs are proven;
- six dependency-affected nodes require dedicated independent rebuilds against final candidate inputs.

Dedicated nodes:

1. order 29 `kf6-syntax-highlighting`;
2. order 68 `drkonqi`;
3. order 81 `kf6-ktexteditor`;
4. order 99 `plasma-workspace`;
5. order 100 `plasma-desktop`;
6. order 101 `powerdevil`.

A normal-build PASS never substitutes for a required dedicated rebuild.

## Reproducibility evidence accepted so far

### Orders 006–040 reusable range — PASS

The preserved independent rebuild from run `33995573548` completed all 35 source builds and produced 180 repeated DEBs. Its original validator did not encode an authoritative relation between an order and the candidate checkpoint root.

That validator defect was corrected fail-closed: candidate roots are bound to exact order ranges, either explicitly or by one unique PASS `range-status.env`. Ambiguous or overlapping ownership is rejected.

Independent analyzer:

- run `34002943660`;
- artifact `9980034262`;
- digest `sha256:82344f3647e583d9cf01e7973d39d0e1295b4deea538d061422b52b6fcdd6b30`;
- 35 source identities PASS;
- 180 binary identities PASS;
- source-preparation umask `0002`;
- Docker/custom AppArmor/uidmap-filecap workaround `0/0/0`;
- relevant AppArmor denials `0`.

This evidence also closes order 29 dedicated reproducibility:

- order 29 `kf6-syntax-highlighting`: **PASS**;
- prepared-source identity: PASS;
- binary byte identity: PASS;
- declared adaptation: `kf6-syntax-highlighting-deterministic-jinja-order`.

Tooling compatibility was subsequently restored in commit `aca9cd3998fbddccdc0f18f06eca9a1e772dec2a`: legacy multiple `--candidate-root` inputs infer their authoritative ranges from one unique PASS `range-status.env`, while explicit `--candidate-root-range` remains supported and overlapping ownership fails closed.

### Dedicated orders 068 and 081 — PASS

Dedicated run:

- run `34003504416`;
- run HEAD `ac282338079e635b2c2d05243bc967df00eaa7dc`;
- artifact `9980459788`;
- digest `sha256:a76eac5620e6768dc525f8dce64e50f561b035359690ebebee941e8db133bbbd`;
- artifact size `285568` bytes;
- Ubuntu runner `26.04.1`;
- `sbuild 0.91.2ubuntu3`;
- `mmdebstrap 1.5.7-3`;
- immutable r3 validation PASS;
- local-only build environment PASS;
- native network-isolation proof PASS;
- relevant AppArmor denials `0`;
- Docker/custom AppArmor/uidmap-filecap workaround `0/0/0`;
- source-preparation umask `0022`.

Order 68 `drkonqi`:

- source identity PASS;
- rebuild PASS;
- byte-identical DEBs: yes;
- dedicated reproducibility: **PASS**.

Order 81 `kf6-ktexteditor`:

- source identity PASS;
- rebuild PASS;
- six produced DEBs byte-identical to the accepted candidate;
- dedicated reproducibility: **PASS**.

The two preceding red attempts were pre-build tooling defects, not product/package reproducibility failures: one relative-workdir path bug and one source-delta selector that incorrectly included `.build`, `.buildinfo` and `.changes` artifacts. Both causes were corrected before the accepted run.

## Current reproducibility work

Formal reusable proof for orders 091–098 is the next gate. A local preliminary comparison already found exact prepared-source identity for all 8 sources and byte identity for all 27 DEBs, but that result is **not yet a formal accepted gate** until the independent analyzer workflow completes and its artifact is verified.

Historical run `33281736655` may be reused only for orders whose per-source build evidence is complete and whose exact source identity is proven. The globally cancelled historical job is not itself accepted as evidence. Orders 099–101 are explicitly excluded from this reuse and require fresh dedicated rebuilds.

After reusable 091–098, remaining KSQ-1 reproducibility work is:

- dedicated order 99 `plasma-workspace`;
- dedicated order 100 `plasma-desktop`;
- dedicated order 101 `powerdevil`;
- consolidated final 95+6 environment/evidence gate.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- Ubuntu snapshot: **20260829T022000Z / FIXED**;
- r3: **IMMUTABLE / INDEPENDENTLY VALIDATED**;
- complete normal 101-source DAG: **PASS / INDEPENDENTLY ACCEPTED**;
- maintained normal checkpoint: **order 101 / 424 DEBs**;
- KWallet package/install/PAM: **PASS**;
- KWallet automatic session unlock: **NOT CERTIFIED**;
- reproducibility 006–040: **PASS**;
- dedicated order 29: **PASS**;
- dedicated order 68: **PASS**;
- dedicated order 81: **PASS**;
- reusable orders 091–098: **FORMAL ANALYZER PENDING**;
- dedicated orders 099–101: **PENDING**;
- final consolidated reproducibility/environment gate: **PENDING**;
- `AURORA_KSQ_1_FULL_CERTIFIED`: **no**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
