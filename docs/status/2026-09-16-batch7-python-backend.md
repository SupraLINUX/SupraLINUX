# SupraLINUX status — 2026-09-16 — Batch 7 Python backend

Status: **provider correction validated and consumed successfully; Batch 7 technical closure is 3/3 PASS**

Canonical promoted KDE Frameworks Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED** until the separate atomic promotion commit.

## Discovery and provider correction

Run `35103681715` attempted KCalendarCore, KCoreAddons and KWidgetsAddons as `6.30.0-0supralinux2`. All three were real `FAIL`, not `BLOCKED`.

The `-2` Clang/LLVM remediation succeeded in moving every node through Shiboken wrapper generation and final Python-extension linking. Each node then failed when ECM invoked `python3 -m build --wheel --no-isolation` because `setuptools.build_meta` was unavailable in the clean sbuild environment.

Evidence:

- KCalendarCore: job `104819252283`, artifact `10449348134`, SHA-256 `5e24d94981c060541e008c81ef6e76e3f785b5e52fe249206aa117920c9d7040`;
- KCoreAddons: job `104819252182`, artifact `10449846512`, SHA-256 `17df43995650455389ee2f0d565ed966dd536abaeaf6f56bb44877c762c478af`;
- KWidgetsAddons: job `104819252378`, artifact `10449886366`, SHA-256 `0ded038e3a2b7cac8bc94dc5eb61e8183cc1cdcc45284d0040ddbc4ee9670760`.

Provider-only commit `78760b565dd49e981fa0891535da289120b40470` passed Repository Policy in run `35106561229`. Dependency-provider run `35106561251`, job `104829186807`, passed with artifact `10450572112`, SHA-256 `488592048a0514b8f6234e8820c959817a151782fef41c138b71f7a8b7fe8fc4`.

That evidence proves Ubuntu Resolute provides `python3-setuptools 78.1.1-0.1build1` and that `setuptools.build_meta` imports successfully alongside `python3-build 1.4.0-1`. The package profiles therefore declare `python3-setuptools` explicitly. KDE/ECM remains authority for the wheel-building path; Ubuntu is only provider.

## Package consumption proof

The provider correction was not considered complete merely because the provider preflight passed. The real Batch 7 package lane consumed it with Python bindings left enabled:

- KCoreAddons `6.30.0-0supralinux4`: **34/34 tests PASS**, Python import PASS, final retained package PASS in run `35122522242`.
- KCalendarCore `6.30.0-0supralinux5`: **507/507 tests PASS**, Python import PASS, final retained package PASS in run `35130213945`.
- KWidgetsAddons `6.30.0-0supralinux7`: **27/27 tests PASS**, Python import PASS, final retained package PASS in run `35145607543`.

Subsequent failures between revision `-3` and those final revisions were translation ownership, ABI, test-fixture or packaging issues; none invalidated the Python backend/provider mapping.

## Final status

- `python3-build`: validated provider;
- `python3-setuptools` / `setuptools.build_meta`: validated provider;
- Clang/LLVM Shiboken toolchain: validated in real builds;
- `DEB_PYTHON_INSTALL_LAYOUT=deb`: retained;
- Python bindings: retained ON;
- real package consumption: **PASS on all three Batch 7 nodes**.

Historical FAIL attempts remain in the immutable attempt ledger. Provider evidence never replaces package evidence.

PR #1 remains **OPEN + DRAFT** and must not be merged.
