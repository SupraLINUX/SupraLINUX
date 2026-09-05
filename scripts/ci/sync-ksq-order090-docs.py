#!/usr/bin/env python3
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new)


active = Path("docs/validation/AURORA_KSQ_1_ACTIVE_STATUS.md")
t = active.read_text(encoding="utf-8")
start = "## Orders 081–090 — current local-only gate\n"
end = "## Reproducibility contract\n"
if t.count(start) != 1 or t.count(end) != 1:
    raise SystemExit("active range markers are not unique")
replacement = """## Orders 081–090 — ACCEPTED on r3

The complete local-only range and its separate fail-closed acceptance are PASS.

Source-build evidence:

- run `33978550975`;
- source HEAD `8b54e2aa98e7df0d82a09b0d840cd2163913c409`;
- artifact `9974023708`;
- digest `sha256:dfa78a851139b279f08d58bef9a0d95fc9261a26c18b6c1dc85a65afe29401ed`;
- 10/10 sources PASS;
- 31 new DEBs;
- accumulated DEBs: `376`;
- packaging adaptations: `0`;
- external APT HTTP(S) during source builds: `0`;
- relevant AppArmor denials: `0`.

The first independent-acceptance attempt (`33994677077`) failed closed only because its validator assumed a `build/ksq-1/...` extraction root while this raw artifact is rooted at `ksq-1/...`. The source and predecessor identities had already passed; no checkpoint was promoted. Downstream source-artifact consumers now resolve exactly one supported root and reject missing/ambiguous layouts.

Successful independent acceptance:

- run `33994817042`;
- acceptance HEAD `ddffb2dfb6aa6c48e56cc07b11a11696d6cb5c9b`;
- artifact `9977725295`;
- digest `sha256:aa4d0499623073108161750881eee06804d1a1d20e5cd45e4a83ab4de3ad7d04`;
- `evidence.sha256`: PASS after independent download/extraction;
- accepted checkpoint: **order 90 / 376 DEBs**.

Order 81 `kf6-ktexteditor` has normal-build PASS only; its dedicated reproducibility obligation remains **NOT CERTIFIED**.

Detailed record: `docs/validation/AURORA_KSQ_1_RANGE_081_090_R3.md`.

## Orders 091–101 — current local-only gate

Range 91–101 is active from the exact independently accepted order-90 checkpoint. Its maintained workflow reconstructs the complete accepted dependency chain, validates immutable r3 again and builds orders 91–101 under the same local-only unshare/sbuild network-isolation contract.

Current run: `33994908104` on source HEAD `7f680a9eb18096bf5908abe131bc943c3564a6f4`.

Orders 99 `plasma-workspace`, 100 `plasma-desktop` and 101 `powerdevil` may pass their normal builds without satisfying their later dedicated reproducibility requirements.

"""
i = t.index(start)
j = t.index(end)
t = t[:i] + replacement + t[j:]
t = replace_once(t, "- maintained accepted checkpoint: **order 80 / 345 DEBs**;", "- maintained accepted checkpoint: **order 90 / 376 DEBs**;", "active checkpoint")
t = replace_once(t, "- orders 081–090: **LOCAL-ONLY BUILD ACTIVE / NOT ACCEPTED**;\n- orders 091–101: **NOT ACCEPTED**;", "- orders 081–090: **PASS / INDEPENDENTLY ACCEPTED**;\n- orders 091–101: **LOCAL-ONLY BUILD ACTIVE / NOT ACCEPTED**;", "active ranges")
active.write_text(t, encoding="utf-8")

qual = Path("docs/KDE_STACK_QUALIFICATION.md")
q = qual.read_text(encoding="utf-8")
old = "Order 68 `drkonqi` has a normal-build PASS only; its dedicated reproducibility rebuild remains mandatory under the 95+6 contract. Orders 81–90 are now the active local-only range from the exact independently accepted order-80 checkpoint."
new = """Order 68 `drkonqi` has a normal-build PASS only; its dedicated reproducibility rebuild remains mandatory under the 95+6 contract.

Orders 81–90 are now **independently accepted on immutable r3**. Source-build run `33978550975` produced 10/10 PASS, 31 new DEBs and 376 accumulated DEBs with zero range adaptations, zero external build APT HTTP(S) and zero relevant AppArmor denials. The first acceptance attempt `33994677077` failed closed only on an artifact extraction-root assumption and promoted nothing. After fail-closed heterogeneous-root detection was applied to all downstream consumers, acceptance run `33994817042`, artifact `9977725295`, digest `sha256:aa4d0499623073108161750881eee06804d1a1d20e5cd45e4a83ab4de3ad7d04`, promoted the maintained checkpoint to **order 90 / 376 DEBs**. Detailed evidence is `docs/validation/AURORA_KSQ_1_RANGE_081_090_R3.md`.

Order 81 `kf6-ktexteditor` has normal-build PASS only and still requires its dedicated reproducibility rebuild. Orders 91–101 are now the active local-only range from the exact independently accepted order-90 checkpoint."""
q = replace_once(q, old, new, "qualification order90 paragraph")
qual.write_text(q, encoding="utf-8")

r3 = Path("docs/validation/AURORA_KSQ_1_R3_SLICE_AND_REGRESSION.md")
r = r3.read_text(encoding="utf-8")
old = """The maintained checkpoint is therefore **order 80 / 345 DEBs**. The next authorized range is 81–90, and it must consume the exact accepted-080 plus source-artifact provenance rather than reconstruct a new implicit predecessor.

Order 68 `drkonqi` remains normal-build PASS / dedicated reproducibility **NOT CERTIFIED**."""
new = """Range 81–90 has since separately completed both required stages:

- local-only source-build run `33978550975`: 10/10 PASS, 31 new DEBs, 376 accumulated DEBs;
- independent acceptance run `33994817042`: PASS, artifact `9977725295`, digest `sha256:aa4d0499623073108161750881eee06804d1a1d20e5cd45e4a83ab4de3ad7d04`.

The maintained checkpoint is therefore **order 90 / 376 DEBs**. The next authorized range is 91–101 and must consume the exact accepted-090 provenance.

Orders 68 `drkonqi` and 81 `kf6-ktexteditor` remain normal-build PASS / dedicated reproducibility **NOT CERTIFIED**."""
r = replace_once(r, old, new, "r3 downstream checkpoint")
r = replace_once(r, "- accepted KSQ-1 checkpoint: **order 80 / 345 DEBs**;", "- accepted KSQ-1 checkpoint: **order 90 / 376 DEBs**;", "r3 checkpoint")
r = replace_once(r, "- orders 81–90: **ACTIVE local-only range / not accepted**;\n- orders 91–101: **NOT ACCEPTED**;", "- orders 81–90: **PASS / independently accepted**;\n- orders 91–101: **ACTIVE local-only range / not accepted**;", "r3 ranges")
r3.write_text(r, encoding="utf-8")

print("AURORA_KSQ_R3_ORDER090_DOC_SYNC=PASS")
