# KDE Frameworks 6.30 Tier 1 — package batch 4

Status: **CLOSED — 3/3 PASS**

Last reviewed: **2026-09-15**

## Authority

KDE Frameworks `6.30.0` is the selected stable upstream release and remains the source/build authority. Ubuntu Resolute is the provider and compatibility target. Debian/Ubuntu packaging is technical reference only.

Batch 4 contains:

- KItemViews (`kitemviews`);
- KGlobalAccel (`kglobalaccel`);
- KSyntaxHighlighting (`syntax-highlighting`).

All three depend only on retained ECM `6.30.0-0supralinux3` in the Tier 1 DAG.

## Attempt 1 — run `34999449194`

### KItemViews — PASS retained

KItemViews `6.30.0-0supralinux1` completed the hosted package lane:

- job `104483912528`;
- artifact `10409267184`;
- artifact SHA-256 `7e34fa7ede21510cf6829448e7b45a5c2832aaf9ac2719b9cb4125d23b593e55`;
- tests `2/2 PASS`;
- Lintian error gate PASS;
- SONAME `libKF6ItemViews.so.6` PASS;
- consumer smoke PASS.

Its PASS was retained and not rebuilt during remediation.

### KGlobalAccel `-1` — historical real FAIL

KGlobalAccel `6.30.0-0supralinux1` was really attempted and failed in clean `sbuild`:

- job `104483912661`;
- artifact `10408264332`;
- artifact SHA-256 `1b7564f211967d1be8b61a96bc2a67389c6164f566e54dad79682d37a33bf6e5`;
- failure: `dh_auto_configure` / CMake;
- tests not reached.

ECM `ECMPoQmTools` required the Qt 6 `LinguistTools` CMake component, but the packaging lacked `qt6-tools-dev` in Build-Depends. This is a package-attempt FAIL, not BLOCKED and not infrastructure.

### KSyntaxHighlighting `-1` — historical real FAIL

KSyntaxHighlighting `6.30.0-0supralinux1` failed independently for the same packaging omission:

- job `104483912313`;
- artifact `10408154532`;
- artifact SHA-256 `8601077898fcba1ea5708fbd4e5a1c0d877825f969b8b39999d7d6bf131fbfe4`;
- failure: `dh_auto_configure` / CMake;
- tests not reached.

## Remediation

Ubuntu Resolute provides the selected Qt 6.10 provider line and `qt6-tools-dev` supplies `Qt6LinguistTools`. No KDE source change, KDE downgrade, Qt replacement or ABI relaxation was required.

The packaging-only remediation was:

- KGlobalAccel `6.30.0-0supralinux2`: add `qt6-tools-dev (>= 6.9.0~)`;
- KSyntaxHighlighting `6.30.0-0supralinux2`: add `qt6-tools-dev (>= 6.9.0~)`.

The `-1` FAIL attempts remain retained evidence.

## Remediation validation — run `35006477086`

Repository Policy run `35006476864` passed before canonical promotion.

KItemViews performed a complete scope-skip on the remediation commit: ECM download, package build and evidence upload were all intentionally skipped. Its prior PASS remains the accepted evidence.

### KGlobalAccel `6.30.0-0supralinux2` — PASS

- job `104507372240`;
- artifact `10412320520`;
- artifact SHA-256 `cb8143633cf15745a235937ea55ee096cb094cc96da3bd1fc39dc914f3acb3b1`;
- tests `1/1 PASS`;
- Lintian `PASS-errors`;
- SONAME `libKF6GlobalAccel.so.6` PASS;
- consumer smoke PASS;
- ECM predecessor `6.30.0-0supralinux3`.

### KSyntaxHighlighting `6.30.0-0supralinux2` — PASS

- job `104507371855`;
- artifact `10411888269`;
- artifact SHA-256 `1ec0d1e7d046b1393fbb299c9a6fec7e85ee4ac59ed5deafa0c777ead67c0b5f`;
- tests `8/8 PASS`;
- Lintian `PASS-errors`;
- SONAME `libKF6SyntaxHighlighting.so.6` PASS;
- consumer smoke PASS;
- ECM predecessor `6.30.0-0supralinux3`.

Non-fatal Lintian warnings remain documented rather than hidden: compatibility `-doc` packages are intentionally empty while QCH is disabled; upstream signatures are not claimed as packaged payload; `ksyntaxhighlighter6` currently has no manpage. None is an error-level gate failure.

## Canonical closure

Batch 4 is now **3/3 PASS** and all three nodes are downstream eligible in the hosted lane.

Canonical Tier 1 state after closure:

**13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED**.

The campaign ledger preserves every real FAIL and PASS attempt. The Tier 1 manifest and package DAG now promote KItemViews, KGlobalAccel and KSyntaxHighlighting only because real PASS evidence exists.

This remains hosted package-preflight evidence, not authoritative KVM/JIT certification.

## Preserved gates

The closure does not relax any build or policy gate. The lane still requires exact KDE source SHA-256, retained ECM PASS, clean Ubuntu 26.04 `sbuild`, upstream tests, binary contracts, SONAME validation, Lintian error gates, `.deb`/`.ddeb`/`.changes`/`.buildinfo`/`.dsc` evidence and a consumer CMake/runtime smoke.

KConfig remains deferred until the runner explicitly supports its multi-library ABI contract. KWidgetsAddons remains outside Batch 4 because its selected upstream-default profile adds Python/Shiboken/PySide surface.

PR #1 remains Draft. No merge is authorized by this closure.
