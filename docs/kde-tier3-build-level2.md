# KDE Frameworks Tier 3 — build Level 2

Status: **Attempt 4 closed MIXED; KCMUtils `6.30.0-0supralinux3` remediation materialization pending** as of 2026-09-28.

Level 2 contains Baloo, KCMUtils, KNotifyConfig and KParts. Its precondition is closed Level 1 Attempt 10: KIO `6.30.0-0supralinux10` and KXMLGui `6.30.0-0supralinux5` are canonical PASS, with Tier 3 at **13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED**.

The Level 2 manifest freezes each source-only materialization, all direct Frameworks 6.30 Build-Depends, the recursive SupraLINUX provider closure, exact predecessor versions/artifact IDs/SHA-256 values, selected build profiles and QML payload checks. Every Level 2 sbuild remains network-disabled.

```text
state = active-pending-ci
execution_authorized = true
current_attempt = 4
next_gate = tier3-build-level2-attempt4
```

Planning was validated by Repository Policy `36443524514` and Level 2 workflow `36443524497` at commit `b07c6c0a0b3072a76e57cf52d679001de2985d3c`. That run executed the planner and intentional skip only; rootfs and package jobs were skipped as required.

Attempt 1 was invalidated before package execution. Recovery planning then passed under Repository Policy `36447346563` and Level 2 workflow `36447346441` at commit `d420cd8b60e48a837ab90acf5ce144f0bfc9be54`; the executable-runner preflight passed while rootfs and package jobs remained skipped. Attempt 2 was subsequently executed and closed FAIL. Canonical package state remains unchanged by Attempt 3 activation until new build evidence is consumed.

KNewStuff is dependency-derived: it remains `pending/runtime-validation-required` while KCMUtils has not failed; if KCMUtils is `FAIL` or `BLOCKED`, KNewStuff is canonically `BLOCKED` by KCMUtils. A KCMUtils PASS only enables its separate runtime-validation gate; it never auto-promotes KNewStuff.

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

Attempt 3 remediation does not change source code or package versions. It adds the inherited support closure `breeze-icons` + `kdoctools` to all four Level 2 nodes. Repository Policy `36459675227` and Level 2 workflow `36459675009` both passed at commit `82d1e390673e261bc45a1676d002630248b46dc5`; planner/scope validation passed while rootfs and package jobs were skipped. Attempt 3 is therefore authorized for the same four nodes.


## Attempt 3 activation

Attempt 3 is active only to validate the inherited packaging support closure. The canonical pre-build snapshot remains **13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED**. No source, package version, upstream release, Qt provider or materialization changed. `breeze-icons` and `kdoctools` are the only new inherited support inputs, and stable promotion remains outside this gate.


## Attempt 3 result

Workflow `36461187872` proved that the inherited support closure fixed the Attempt 2 install-deps blocker: all four nodes advanced beyond dependency installation.

The runner then exposed a validation defect: it treated every support provider's development package as if it were a direct Build-Depends that must appear in `.buildinfo`. Exact support artifacts are now proven separately in `support-closure.json`; `.buildinfo` remains authoritative only for declared direct Build-Depends and explicit additional proof packages.

Primary classification: Baloo and KNotifyConfig are `INFRA_INVALID` at buildinfo-predecessor-proof; KParts is also `INFRA_INVALID` at that primary stage, with an independent Lintian symbol-metadata blocker observed; KCMUtils is a real `FAIL` in sbuild/dpkg-gensymbols after 6/6 tests passed.

Canonical state remains **13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED**. Attempt 4 is not authorized. Only KCMUtils and KParts are queued for rematerialization as `6.30.0-0supralinux2`; Baloo and KNotifyConfig retain their current source materializations.


## Attempt 4 materialization gate

Remediation materialization workflow `36466461781` completed successfully at commit `a0ee684e97f834e39a760eab401ba29e2c172a5d`.

- KCMUtils `6.30.0-0supralinux2`: artifact `10989229464`, SHA-256 `ec9fb73d8c03f7c972ab2e878ffaa56a3a51f7edad56e276464a09842a88fe5b`.
- KParts `6.30.0-0supralinux2`: artifact `10989828107`, SHA-256 `52183686781a2fd30a0d6b8c0b0c40fce6e5da55ac2f8680df7fcc2eae120112`.

Both source materializations are now promoted into the Level 2 build inputs. This does **not** change package state: the canonical snapshot remains **13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED**. Binary execution remains disabled until the separate Attempt 4 activation-validation gate passes.


## Attempt 4 activation

Repository Policy `36468037163` and Level 2 workflow `36468036937` both passed at commit `8b38a250b86f33dbbab60b406b2724ac6b25498d`. The Level 2 planning job `109082952071` and intentional-skip job `109083016803` passed; shared rootfs and package matrix were skipped, proving the activation state before package execution.

Attempt 4 is now authorized for all four Level 2 nodes. Baloo and KNotifyConfig retain their `-1` source materializations; KCMUtils and KParts use the remediated `-2` materializations. The canonical pre-build snapshot remains **13 PASS / 0 pending / 4 current FAIL / 3 BLOCKED** until real Attempt 4 evidence is consumed.


## Attempt 4 result

Workflow `36473379324` executed all four Level 2 package nodes from commit `35ee2761b4f6c196e9ab95e7c8eff66c6cffcce3` using shared rootfs artifact `10992682557` (SHA-256 `0dad0fc0a61d5d39bb0cc12c62d43956927657d13e67a79f9cfb6274ef690d54`).

- Baloo `6.30.0-0supralinux1`: **PASS**, 38/38 tests, artifact `10993001091`.
- KNotifyConfig `6.30.0-0supralinux1`: **PASS**, 1/1 test, artifact `10992533517`.
- KParts `6.30.0-0supralinux2`: **PASS**, 3/3 tests, artifact `10992408883`.
- KCMUtils `6.30.0-0supralinux2`: real **FAIL** in `sbuild` after 6/6 tests passed, artifact `10992718121`.

The three successful nodes are canonically promoted. KTextEditor is therefore no longer BLOCKED by KParts and returns to `pending`. Purpose and KNewStuff remain BLOCKED by KCMUtils. Canonical Tier 3 is now **16 PASS / 1 pending / 1 current FAIL / 2 BLOCKED**.

KCMUtils failed in `dpkg-gensymbols`: the existing `-2` remediation correctly made the shared_ptr vtable optional, but the matching libstdc++ shared_ptr `typeinfo` symbol remained mandatory on `!riscv64` and is not emitted by the Resolute amd64 toolchain. The already-`optional=templinst` missing symbols are not fatal.

## KCMUtils remediation after Attempt 4

The next source-only candidate is `6.30.0-0supralinux3`. It preserves `arch=!riscv64` and marks only the compiler-generated typeinfo symbol

`_ZTISt23_Sp_counted_ptr_inplaceI10QQmlEngineSaIvELN9__gnu_cxx12_Lock_policyE2EE@Base`

as `optional`. No KDE public ABI, upstream source, Qt provider, tests or support closure is relaxed.

Materialization is the only authorized next action. It does **not** consume Package Attempt 5. Binary execution remains disabled until materialization and a later activation gate pass.
