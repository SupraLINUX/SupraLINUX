#!/usr/bin/env python3
from pathlib import Path


def replace_required(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    if old in text:
        text = text.replace(old, new, count)
        path.write_text(text, encoding="utf-8")
        return
    if new not in text:
        raise SystemExit(f"{path}: replacement anchor missing: {old}")


def ensure_insert_before(path: Path, anchor: str, block: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if anchor not in text:
        raise SystemExit(f"{path}: insertion anchor missing: {anchor}")
    text = text.replace(anchor, block.rstrip() + "\n\n" + anchor, 1)
    path.write_text(text, encoding="utf-8")


# 1. Canonical DAG document: only current-state surfaces advance; history stays untouched.
p = Path("docs/kde-dag.md")
replace_required(
    p,
    "Status: **ECM root PASS; 13 Frameworks Tier 1 PASS; 16 Tier 1 pending; 0 current FAIL; 0 BLOCKED**",
    "Status: **ECM root PASS; 18 Frameworks Tier 1 PASS; 11 Tier 1 pending; 0 current FAIL; 0 BLOCKED**",
)
replace_required(p, "Last reviewed: **2026-09-15**", "Last reviewed: **2026-09-16**")
replace_required(
    p,
    "Tier 1 queda en **16 PASS, 13 pending, 0 current FAIL, 0 BLOCKED**.",
    "Tier 1 queda en **18 PASS, 11 pending, 0 current FAIL, 0 BLOCKED** tras el cierre canónico de Batch 6.",
)

# 2. Dependency resolution document: move all current summaries to Batch 6 closure truth.
p = Path("docs/kde-tier1-dependencies.md")
replace_required(
    p,
    "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping resolved; hosted provider preflight PASS; 16 package nodes PASS; 13 package nodes pending**",
    "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping resolved; hosted provider preflight PASS; 18 package nodes PASS; 11 package nodes pending**",
)
replace_required(p, "Last reviewed: **2026-09-15**", "Last reviewed: **2026-09-16**")
replace_required(
    p,
    "- Tier 1 package/build states: **16 PASS / 13 pending**;",
    "- Tier 1 package/build states: **18 PASS / 11 pending**;",
)
replace_required(
    p,
    "Provider evidence alone never promotes a Framework. Each of the sixteen canonical PASS nodes has real package-attempt evidence. Batch 5 is closed 3/3 PASS; the two earlier ModemManagerQt FAIL attempts remain retained as historical evidence while its `-3` PASS is the current downstream-eligible state.",
    "Provider evidence alone never promotes a Framework. Each of the eighteen canonical PASS nodes has real package-attempt evidence. Batch 5 remains historically closed 3/3 PASS, and Batch 6 is closed 2/2 PASS. Earlier ModemManagerQt, KWindowSystem and Solid FAIL attempts remain retained as historical evidence while their later PASS revisions are the current downstream-eligible state.",
)
replace_required(p, "## Batch 6 selection", "## Batch 6 selection (historical pre-closure)")
replace_required(
    p,
    "KWindowSystem and Solid are the next package candidates. This does not change authority: KDE upstream 6.30.0 defines requirements; Ubuntu Resolute is only a provider. KWindowSystem retains QML, X11 and Wayland with Wayland Protocols >= 1.46 and Plasma Wayland Protocols. Solid retains DBus, udev and libmount; IMobileDevice/PList remain upstream-optional and their Ubuntu providers are supplied rather than disabled. Canonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until real package evidence is promoted.",
    "At Batch 6 selection time, KWindowSystem and Solid were the next package candidates. This did not change authority: KDE upstream 6.30.0 defined requirements; Ubuntu Resolute remained only a provider. KWindowSystem retained QML, X11 and Wayland with Wayland Protocols >= 1.46 and Plasma Wayland Protocols. Solid retained DBus, udev and libmount; IMobileDevice/PList remained upstream-optional and their Ubuntu providers were supplied rather than disabled. The canonical Tier 1 state at that historical point was **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** pending real package promotion.",
)
replace_required(
    p,
    "Because this changes a shared Batch 6 build input, both KWindowSystem and the retained-PASS Solid node must revalidate. No package revision is bumped for this runner-only correction. Canonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until the corrected lane passes and closure promotes the nodes.",
    "Because this changed a shared Batch 6 build input, both KWindowSystem and the retained-PASS Solid node had to revalidate. No package revision was bumped for this runner-only correction. At that remediation point, canonical Tier 1 remained **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until the corrected lane passed and closure promoted the nodes.",
)

# 3. General dated status: make the explicit 'Current canonical state' current, preserve attempt chronology as historical.
p = Path("docs/status/2026-09-15.md")
replace_required(
    p,
    "Batches 4 and 5 are closed **3/3 PASS** each.\n\nCanonical Tier 1:\n\n**16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED**.\n\nThe promoted Batch 5 nodes are KIdleTime, ModemManagerQt and NetworkManagerQt. Only retained PASS artifacts may feed dependents.",
    "Batches 4 and 5 are closed **3/3 PASS** each, and Batch 6 is closed **2/2 PASS**.\n\nCanonical Tier 1:\n\n**18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**.\n\nThe Batch 6 closure promotes KWindowSystem `6.30.0-0supralinux4` and Solid `6.30.0-0supralinux2` from final run `35047623320`. Only retained PASS artifacts may feed dependents; historical FAIL attempts remain evidence rather than current state.",
)
for old, new in (
    ("## Tier 1 Batch 6 prepared", "## Tier 1 Batch 6 preparation (historical pre-closure)"),
    ("## Tier 1 Batch 6 initial attempts and remediation", "## Tier 1 Batch 6 initial attempts and remediation (historical pre-closure)"),
    ("## Tier 1 Batch 6 second attempt", "## Tier 1 Batch 6 second attempt (historical pre-closure)"),
    ("## Tier 1 Batch 6 third attempt", "## Tier 1 Batch 6 third attempt (historical pre-closure)"),
    ("## Tier 1 Batch 6 fourth attempt and consumer-runtime remediation", "## Tier 1 Batch 6 fourth attempt and consumer-runtime remediation (historical pre-closure)"),
):
    replace_required(p, old, new)

# 4. Batch 6 design/execution document: current header first, historical execution preserved below.
p = Path("docs/kde-tier1-package-batch6.md")
replace_required(
    p,
    "Status: **Solid retained PASS — KWindowSystem package/tests PASS but shared consumer-runtime runner remediation pending**\nLast reviewed: **2026-09-15**",
    "Status: **CLOSED PASS — KWindowSystem `6.30.0-0supralinux4` and Solid `6.30.0-0supralinux2` canonical/downstream-eligible**\nLast reviewed: **2026-09-16**\n\nCurrent canonical Tier 1: **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. Final Batch 6 evidence is workflow run `35047623320`; the execution sections below preserve the pre-closure history that led to that result.",
)
replace_required(p, "## Selection", "## Selection (historical pre-closure)")
replace_required(
    p,
    "Canonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** until real package attempts pass and a separate closure commit promotes them.",
    "At selection time, canonical Tier 1 was **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED** pending real package attempts and a separate closure promotion.",
)
replace_required(p, "## Promotion rule", "## Promotion rule (historical pre-closure)")
replace_required(
    p,
    "The open batch is not canonically closed. Solid has retained real PASS evidence but will be revalidated because the shared consumer-runtime runner changed. KWindowSystem remains remediation-pending-build even though its `-4` package build and all upstream tests passed, because the complete package gate includes consumer runtime validation. Canonical Tier1/DAG remains unchanged until a subsequent run passes the complete corrected lane for the affected nodes and a separate closure commit promotes them.",
    "Before closure, the batch was not yet canonically closed. Solid retained real PASS evidence but required revalidation because the shared consumer-runtime runner changed. KWindowSystem remained remediation-pending-build even though its `-4` package build and all upstream tests passed, because the complete package gate also included consumer runtime validation. Canonical Tier1/DAG therefore remained unchanged until the corrected lane passed and the separate closure commit promoted both nodes.",
)

# 5. Batch 6 status: put final truth at the top and explicitly mark the old running narrative historical.
p = Path("docs/status/2026-09-15-batch6.md")
replace_required(
    p,
    "Status: **Solid retained PASS — KWindowSystem `-4` package/tests PASS; shared consumer-runtime runner remediation pending**\n\nCanonical Tier 1 remains **16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED**.\n\nBatch 6 selects KWindowSystem and Solid because both preserve KDE upstream Linux defaults while fitting the current single-primary-library ABI package lane.",
    "Status: **CLOSED PASS — KWindowSystem `6.30.0-0supralinux4` + Solid `6.30.0-0supralinux2` canonical/downstream-eligible**\n\nCurrent canonical Tier 1: **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. Final package/revalidation evidence is workflow run `35047623320`.\n\n## Historical execution record\n\nThe narrative below records Batch 6 point-in-time preparation, FAIL/remediation and revalidation states. Any `16 PASS / 13 pending` statement in this historical section describes the canonical state at that earlier point, not the current state.\n\nBatch 6 selected KWindowSystem and Solid because both preserve KDE upstream Linux defaults while fitting the current single-primary-library ABI package lane.",
)

# 6. Tier 1 overview: update the canonical snapshot and add the missing Batch 4-6 PASS evidence.
p = Path("docs/kde-tier1.md")
replace_required(
    p,
    "Status: **29-node source set fixed; 10 hosted package PASS; 19 package nodes pending; 0 current FAIL; 0 BLOCKED**",
    "Status: **29-node source set fixed; 18 hosted package PASS; 11 package nodes pending; 0 current FAIL; 0 BLOCKED**",
)
replace_required(p, "Last reviewed: **2026-09-15**", "Last reviewed: **2026-09-16**")
insert = """### Batch 4

- KItemViews `6.30.0-0supralinux1`: run `34999449194`, job `104483912528`, artifact `10409267184`, 2/2 tests PASS.
- KGlobalAccel `6.30.0-0supralinux2`: run `35006477086`, job `104507372240`, artifact `10412320520`, 1/1 tests PASS; its `-1` missing-`LinguistTools` attempt remains historical FAIL evidence.
- KSyntaxHighlighting `6.30.0-0supralinux2`: run `35006477086`, job `104507371855`, artifact `10411888269`, 8/8 tests PASS; its `-1` missing-`LinguistTools` attempt remains historical FAIL evidence.

### Batch 5

- KIdleTime `6.30.0-0supralinux1`: run `35014875475`, job `104535671033`, artifact `10414598079`, 1/1 tests PASS.
- ModemManagerQt `6.30.0-0supralinux3`: run `35021323444`, job `104557423664`, artifact `10417683848`, 11/11 tests PASS; two earlier real FAIL attempts remain historical evidence.
- NetworkManagerQt `6.30.0-0supralinux1`: run `35014875475`, job `104535671250`, artifact `10414714325`, 38/38 tests PASS.

### Batch 6

Final shared-runner revalidation workflow `35047623320`:

- KWindowSystem `6.30.0-0supralinux4`: job `104640833059`, artifact `10428130399`, ZIP SHA-256 `9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272`, 14/14 tests PASS, Lintian/SONAME/consumer runtime closure PASS.
- Solid `6.30.0-0supralinux2`: job `104640833295`, artifact `10427653865`, ZIP SHA-256 `cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389`, 5/5 tests PASS, Lintian/SONAME/consumer runtime closure PASS.

Both are downstream-eligible. KWindowSystem's four prior FAIL attempts and Solid's earlier FAIL plus historical PASS remain retained as evidence; current node state is PASS.
"""
ensure_insert_before(p, "## ABI and packaging policy", insert, "### Batch 6\n\nFinal shared-runner revalidation workflow `35047623320`")
replace_required(
    p,
    "- PASS: **10**;\n- pending: **19**;\n- current FAIL: **0**;\n- BLOCKED: **0**.",
    "- PASS: **18**;\n- pending: **11**;\n- current FAIL: **0**;\n- BLOCKED: **0**.",
)
replace_required(
    p,
    "Revalidate the current KDE stable release metadata before starting the next package batch, then select another independent group among the 19 pending nodes. Keep ABI contracts, optional features and tests explicit; extend the package runner when a Framework requires multiple ABI libraries instead of weakening the model.",
    "The eleven pending nodes are `kcalendarcore`, `kconfig`, `kcoreaddons`, `kguiaddons`, `ki18n`, `kirigami`, `kquickcharts`, `kuserfeedback`, `kwidgetsaddons`, `prison` and `sonnet`. Revalidate the current KDE stable release metadata before Batch 7 selection, then choose the next independent group whose packaging contracts fit the available runner. Keep ABI contracts, upstream-default features and tests explicit; extend the runner for multi-library or binding-heavy Frameworks instead of weakening the model.",
)

# Final guard: current-state docs must expose 18/11 at their primary status surfaces.
checks = {
    Path("docs/kde-dag.md"): ["18 Frameworks Tier 1 PASS", "11 Tier 1 pending", "Tier 1 queda en **18 PASS, 11 pending"],
    Path("docs/kde-tier1-dependencies.md"): ["18 package nodes PASS", "11 package nodes pending", "Tier 1 package/build states: **18 PASS / 11 pending**"],
    Path("docs/status/2026-09-15.md"): ["## Current canonical state", "**18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**"],
    Path("docs/kde-tier1-package-batch6.md"): ["Status: **CLOSED PASS", "Current canonical Tier 1: **18 PASS / 11 pending"],
    Path("docs/status/2026-09-15-batch6.md"): ["Status: **CLOSED PASS", "Current canonical Tier 1: **18 PASS / 11 pending"],
    Path("docs/kde-tier1.md"): ["18 hosted package PASS", "11 package nodes pending", "- PASS: **18**", "- pending: **11**"],
}
for path, tokens in checks.items():
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        if token not in text:
            raise SystemExit(f"{path}: final canonical token missing: {token}")
