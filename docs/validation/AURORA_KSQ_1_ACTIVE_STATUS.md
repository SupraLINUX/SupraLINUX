# Aurora KSQ-1 active qualification status

Status: **ACTIVE — NOT CERTIFIED**

This file is the canonical current engineering status of KSQ-1. It is not a final KSQ-1 acceptance record and does not authorize entry into KSQ-2.

- KSQ-0: **CERTIFIED / CLOSED**.
- KSQ-1: **ACTIVE / NOT CERTIFIED**.
- KSQ-2: **BLOCKED**.
- C4.1: **PAUSED**.

## Fixed contract

- Platform: Ubuntu 26.04 LTS Resolute, amd64.
- Candidate KDE: Plasma 6.7.4 / KDE Frameworks 6.29.0.
- Certified source DAG: 101 sources.
- Immutable snapshot slice: `20260829T022000Z-r3`.
- Build architecture: `mmdebstrap --mode=unshare --variant=buildd` + `sbuild --chroot-mode=unshare --no-enable-network` using the immutable local slice.
- Docker/custom AppArmor/uidmap-filecap workaround in certified builds: forbidden.
- Canonical build-order SHA-256: `9c53547df78a9f7c740228aba09490dfdb68e6307d2200e12ebf907dfa3fcb88`.
- APT Recommends: normal/default semantics.

## Immutable r3 input

r3 is an immutable strict extension of historical r2 containing the three additional payload objects proven necessary by the complete real-build witness. Signed Ubuntu metadata, versions and pre-existing payload identities remain unchanged.

Independent r3 validation:

- run `33964782073`;
- artifact `9969086882`;
- archive SHA-256 `cb904b478afe186b96823b1b2872d5937517e3de10c6d2dd3170ec29fea09bc6`;
- strict extension / signed metadata / pre-existing payload identity / exact witness-gap inclusion: PASS.

Accepted-order-65 regression under r3: PASS in run `33965237362`.

## Normal build — accepted through order 101

The complete 101-source normal-build DAG is accepted.

Orders 66–80:

- source run `33973287438`;
- 15/15 sources PASS;
- 50 new DEBs;
- accumulated `345` DEBs;
- independent acceptance run `33978315934`, artifact `9972976872`, digest `sha256:ebd60471d9834efbb4fad9f5680c6a153000aa8b9393f4821a70ff148edc2511`.

Orders 81–90:

- source run `33978550975`;
- 10/10 sources PASS;
- 31 new DEBs;
- accumulated `376` DEBs;
- independent acceptance run `33994817042`, artifact `9977725295`, digest `sha256:aa4d0499623073108161750881eee06804d1a1d20e5cd45e4a83ab4de3ad7d04`.

Orders 91–101:

- source run `33994908104`;
- source HEAD `7f680a9eb18096bf5908abe131bc943c3564a6f4`;
- artifact `9979632407`;
- digest `sha256:0595106d646d61dcd0d65066b69f109823b00802b78ebc2e6547d3fa1eab9e42`;
- size `248721436` bytes;
- 11/11 sources PASS;
- 48 new DEBs;
- accumulated `424` DEBs;
- packaging adaptations in the range `0`;
- external build APT HTTP(S) `0`;
- relevant AppArmor denials `0`.

Independent acceptance:

- run `34002503177`;
- acceptance HEAD `8de6b08456975e391624813776866a138a8ea40e`;
- artifact `9979901723`;
- digest `sha256:62b5014923d487e13e9a2377ef91dec4cc1a11a33b75acd6f58f4642b0403e83`;
- size `8932` bytes;
- extracted `evidence.sha256`: PASS;
- accepted checkpoint: **order 101 / 424 DEBs**.

Normal build PASS for orders 99–101 does not satisfy their dedicated reproducibility obligations.

## Reproducibility contract

KSQ-1 retains the fixed `95 + 6` contract:

- 95 source nodes may reuse independent earlier build evidence only after exact prepared-source identity, exact binary shape and byte-identical DEBs are proven;
- six dependency-affected nodes require dedicated independent rebuild evidence against final candidate inputs.

Dedicated nodes:

1. order 29 `kf6-syntax-highlighting`;
2. order 68 `drkonqi`;
3. order 81 `kf6-ktexteditor`;
4. order 99 `plasma-workspace`;
5. order 100 `plasma-desktop`;
6. order 101 `powerdevil`.

## Reproducibility accepted so far

### Orders 006–040 reusable range — PASS

Preserved rebuild run `33995573548` completed 35 source rebuilds and produced 180 repeated DEBs. The original post-build validator lacked an authoritative order-to-candidate-root relation; that tooling defect was corrected fail-closed and the immutable preserved evidence was independently reanalyzed.

Independent analyzer:

- run `34002943660`;
- artifact `9980034262`;
- digest `sha256:82344f3647e583d9cf01e7973d39d0e1295b4deea538d061422b52b6fcdd6b30`;
- 35 source identities PASS;
- 180 binary identities PASS;
- source-preparation umask `0002`;
- relevant AppArmor denials `0`;
- Docker/custom AppArmor/uidmap-filecap workaround `0/0/0`.

Order 29 `kf6-syntax-highlighting` dedicated reproducibility is therefore **PASS**, including exact source identity, exact binary identity and the declared adaptation `kf6-syntax-highlighting-deterministic-jinja-order`.

Legacy multiple candidate roots are again executable through fail-closed range inference from one unique PASS `range-status.env` per root. Overlap or missing ownership is rejected. Tooling commit: `aca9cd3998fbddccdc0f18f06eca9a1e772dec2a`.

### Dedicated orders 068 and 081 — PASS

Accepted run:

- run `34003504416`;
- run HEAD `ac282338079e635b2c2d05243bc967df00eaa7dc`;
- artifact `9980459788`;
- digest `sha256:a76eac5620e6768dc525f8dce64e50f561b035359690ebebee941e8db133bbbd`;
- size `285568` bytes;
- Ubuntu 26.04.1 runner;
- `sbuild 0.91.2ubuntu3`;
- `mmdebstrap 1.5.7-3`;
- immutable r3 validation PASS;
- local-only environment and native network isolation PASS;
- source-preparation umask `0022`;
- relevant AppArmor denials `0`;
- Docker/custom AppArmor/uidmap-filecap workaround `0/0/0`.

Order 68 `drkonqi`: source identity PASS, rebuild PASS, byte-identical output, dedicated reproducibility **PASS**.

Order 81 `kf6-ktexteditor`: source identity PASS, rebuild PASS, all six DEBs byte-identical, dedicated reproducibility **PASS**.

### Reusable orders 091–098 — PASS

Historical reference run `33281736655` is globally cancelled and is not accepted by that fact alone. The reusable analyzer permits only preserved per-order evidence after proving exact artifact provenance, per-source PASS evidence, exact prepared-source identity, exact binary package shape and byte-identical candidate/reference DEBs. Orders 99–101 are explicitly excluded.

Authoritative historical inputs:

- reference HEAD `90fd5d3119ebfaab42f721d3bdd977a3472da498`;
- reference job `99217598358`;
- evidence artifact `9729820568`, digest `sha256:5a2c05498f5346a1c72a25c59d9a7d3bd55788d0cce6896d9fde14726f20a6c5`, size `2826876`;
- binary artifact `9729819980`, digest `sha256:ced4f26dd7c00c45967d3458e3f18dabab0049edcb8b03f9e8bd3fcd56c9866a`, size `70080482`.

The first analyzer revisions failed closed on tooling assumptions only: stale artifact metadata and then the wrong build-evidence key (`AURORA_KSQ_1_BUILD_STATUS` instead of the actual `AURORA_KSQ_1_BUILD_RESULT`). Neither failure demonstrated source or binary divergence.

Corrected analyzer v2:

- run `34005216292`;
- run HEAD `bbef709c638d3d95278292623272112360798962`;
- artifact `9980712108`;
- digest `sha256:43135e95250d90ccf2368d1cebd907a283e334185d166c07bb27d3fa1fe4a98c`;
- size `12685` bytes;
- external artifact SHA-256 verification: PASS;
- internal `evidence.sha256`: PASS for all provenance and proof files;
- 8/8 reusable source identities PASS;
- 27/27 binary identities PASS;
- build evidence contract `AURORA_KSQ_1_BUILD_RESULT=PASS` plus exact order/source/version validation: PASS;
- orders 99–101 included: **no**.

Reusable orders 91–98 are therefore formally **PASS**.

## Remaining KSQ-1 work

The next reproducibility gate is a fresh dedicated rebuild of:

- order 99 `plasma-workspace`;
- order 100 `plasma-desktop`;
- order 101 `powerdevil`.

Those rebuilds must use immutable r3, exact accepted candidate inputs, local-only sbuild network isolation, explicit source-preparation umask, zero relevant AppArmor denials and no Docker/custom-AppArmor/uidmap-filecap workaround. Their output must match the accepted candidate byte-for-byte.

After 99–101 pass, KSQ-1 still requires the consolidated final 95+6 reproducibility/environment evidence gate and every other KSQ-1 exit criterion before certification.

KWallet package installation/PAM registration remains PASS. Runtime login/session automatic KWallet unlock remains **NOT CERTIFIED** and is not promoted by package-level reproducibility evidence.

## Current gate state

- KSQ-0: **CERTIFIED / CLOSED**;
- immutable r3 snapshot: **PASS / FIXED**;
- complete normal 101-source DAG: **PASS / INDEPENDENTLY ACCEPTED**;
- maintained normal checkpoint: **order 101 / 424 DEBs**;
- reproducibility 006–040: **PASS**;
- dedicated order 29: **PASS**;
- dedicated order 68: **PASS**;
- dedicated order 81: **PASS**;
- reusable orders 091–098: **PASS**;
- dedicated orders 099–101: **PENDING**;
- final consolidated 95+6 reproducibility/environment gate: **PENDING**;
- KWallet automatic session unlock: **NOT CERTIFIED**;
- `AURORA_KSQ_1_FULL_CERTIFIED`: **no**;
- KSQ-1: **ACTIVE / NOT CERTIFIED**;
- KSQ-2: **BLOCKED**;
- C4.1: **PAUSED**.
