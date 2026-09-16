# SupraLINUX status — 2026-09-16 — Batch 7 Python backend revalidation

Status: **second Batch 7 attempt failed; provider revalidation pending before revision -3**

Canonical promoted KDE Frameworks Tier 1 remains **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**.

## Attempt 2 result

Run `35103681715` attempted KCalendarCore, KCoreAddons and KWidgetsAddons as `6.30.0-0supralinux2`. All three are real `FAIL`, not `BLOCKED`.

The `-2` Clang/LLVM remediation succeeded in moving every node past Shiboken wrapper generation. Each node linked its Python extension and then failed when ECM invoked `python3 -m build --wheel --no-isolation` because `setuptools.build_meta` was unavailable in the clean sbuild environment.

Evidence artifacts:

- KCalendarCore: `10449348134`, SHA-256 `5e24d94981c060541e008c81ef6e76e3f785b5e52fe249206aa117920c9d7040`;
- KCoreAddons: `10449846512`, SHA-256 `17df43995650455389ee2f0d565ed966dd536abaeaf6f56bb44877c762c478af`;
- KWidgetsAddons: `10449886366`, SHA-256 `0ded038e3a2b7cac8bc94dc5eb61e8183cc1cdcc45284d0040ddbc4ee9670760`.

## Next gate

Do not launch Batch 7 revision `-3` yet. First revalidate Ubuntu Resolute as provider for `python3-setuptools` and require successful `import setuptools.build_meta` in the hosted dependency-provider preflight.

If that provider gate passes, Batch 7 may add the backend package to the three clean package Build-Depends, retain KDE Python/tests/Designer defaults unchanged, and attempt revision `6.30.0-0supralinux3`.

PR #1 remains **OPEN + DRAFT** and is not authorized for merge.
