# SupraLINUX status — 2026-09-16 — Batch 7 Python backend

Status: **provider PASS; Batch 7 revision -3 prepared for real build**

Canonical promoted KDE Frameworks Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**.

## Attempt 2

Run `35103681715` attempted KCalendarCore, KCoreAddons and KWidgetsAddons as `6.30.0-0supralinux2`. All three are real `FAIL`, not `BLOCKED`.

The `-2` Clang/LLVM remediation succeeded in moving every node past Shiboken wrapper generation and through final Python extension linking. Each node then failed when ECM invoked `python3 -m build --wheel --no-isolation` because `setuptools.build_meta` was unavailable in the clean sbuild environment.

Evidence:

- KCalendarCore: job `104819252283`, artifact `10449348134`, SHA-256 `5e24d94981c060541e008c81ef6e76e3f785b5e52fe249206aa117920c9d7040`;
- KCoreAddons: job `104819252182`, artifact `10449846512`, SHA-256 `17df43995650455389ee2f0d565ed966dd536abaeaf6f56bb44877c762c478af`;
- KWidgetsAddons: job `104819252378`, artifact `10449886366`, SHA-256 `0ded038e3a2b7cac8bc94dc5eb61e8183cc1cdcc45284d0040ddbc4ee9670760`.

## Provider gate

Provider-only commit `78760b565dd49e981fa0891535da289120b40470` passed Repository Policy in run `35106561229`.

Dependency-provider run `35106561251`, job `104829186807`, passed and retained artifact `10450572112`, SHA-256 `488592048a0514b8f6234e8820c959817a151782fef41c138b71f7a8b7fe8fc4`.

It proves Ubuntu Resolute provides `python3-setuptools 78.1.1-0.1build1` and that `setuptools.build_meta` imports successfully alongside `python3-build 1.4.0-1`.

Batch 7 run `35106561165` skipped all package builds intentionally, so this provider validation did not create a hidden package attempt.

## Revision -3

The next package revision adds only `python3-setuptools` to the three Build-Depends. It retains KDE 6.30.0 source, Python bindings, tests, KWidgetsAddons Designer support, the Clang/LLVM toolchain and `DEB_PYTHON_INSTALL_LAYOUT=deb`.

No PASS is claimed until the real package matrix completes every gate.

PR #1 remains **OPEN + DRAFT** and must not be merged.
