# KDE Frameworks Tier 3 — build Level 2

Status: **Attempt 2 closed FAIL; Attempt 3 support-closure remediation pending validation** as of 2026-09-28.

Level 2 contains Baloo, KCMUtils, KNotifyConfig and KParts. Its precondition is closed Level 1 Attempt 10: KIO `6.30.0-0supralinux10` and KXMLGui `6.30.0-0supralinux5` are canonical PASS, with Tier 3 at **13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED**.

The Level 2 manifest freezes each source-only materialization, all direct Frameworks 6.30 Build-Depends, the recursive SupraLINUX provider closure, exact predecessor versions/artifact IDs/SHA-256 values, selected build profiles and QML payload checks. Every Level 2 sbuild remains network-disabled.

```text
state = planned-pending-activation
execution_authorized = false
current_attempt = 2
next_attempt = 3
next_gate = tier3-build-level2-attempt3-planning-validation
```

Planning was validated by Repository Policy `36443524514` and Level 2 workflow `36443524497` at commit `b07c6c0a0b3072a76e57cf52d679001de2985d3c`. That run executed the planner and intentional skip only; rootfs and package jobs were skipped as required.

Attempt 1 was invalidated before package execution. Recovery planning then passed under Repository Policy `36447346563` and Level 2 workflow `36447346441` at commit `d420cd8b60e48a837ab90acf5ce144f0bfc9be54`; the executable-runner preflight passed while rootfs and package jobs remained skipped. Attempt 2 is now separately authorized for Baloo, KCMUtils, KNotifyConfig and KParts. Canonical package state remains unchanged until real build evidence is consumed.

KNewStuff remains `pending/runtime-validation-required`. A KCMUtils PASS only enables its separate runtime-validation gate; it never auto-promotes KNewStuff.

PASS, FAIL, BLOCKED and INFRA retain their existing semantics. Independent Level 2 nodes use fail-fast=false. Stable promotion still requires explicit user approval.


## Attempt 1 infrastructure invalidation

Workflow `36446660866` successfully planned the four nodes and built a shared Resolute rootfs, but every package job stopped before the Level 2 runner entered:

```text
scripts/run-kde-tier3-build-level2.sh: Permission denied
exit code 126
```

No node reached `sbuild`; no package evidence directory was created. Attempt 1 is therefore `INFRA_INVALID`, not package FAIL. Canonical state remains **13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED**.

The shared rootfs itself passed and was retained as artifact `10980029224`, SHA-256 `eae0f8b164ee002ad56b96f76e3a882254b60ca639d8ce7663c63447b961e000`.

Remediation is limited to restoring executable mode `100755` on the Level 2 runner and adding a planner preflight that fails if the runner is not executable. Attempt 2 remains unauthorized until that planning gate passes.


## Attempt 2 activation

Attempt 2 is authorized only after the recovery planning gate proved the Level 2 runner executable. It starts from the same frozen package/materialization/predecessor contracts; Attempt 1 contributes no package evidence and no canonical package-state transition.


## Attempt 2 result and root cause

Workflow `36448160410` entered the Level 2 runner correctly and all four nodes reached `sbuild`. Each package attempt failed in `install-deps` before compilation (build time 0), so these are package-attempt FAIL results rather than infrastructure invalidations.

The common solver root cause is:

```text
libkf6kio-dev
  -> libkf6kiofilewidgets6
  -> libkf6iconthemes6 6.30.0-0supralinux3
  -> libkf6breezeicons6 (>= 4:6.30.0~)
  -> no installable choice
```

Level 0 already models Breeze Icons as a packaging support provider of KIconThemes. Level 2 derived only the logical DAG provider closure and therefore omitted inherited support-provider edges. The same audit also found KDocTools inherited through KWallet.

Canonical result after Attempt 2: **13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED**. Baloo, KCMUtils, KNotifyConfig and KParts are FAIL. KTextEditor is BLOCKED by KParts; Purpose and KNewStuff are BLOCKED by KCMUtils.

Attempt 3 remediation does not change source code or package versions. It adds the inherited support closure `breeze-icons` + `kdoctools` to all four Level 2 nodes and remains unauthorized until Repository Policy and planning validation pass.
