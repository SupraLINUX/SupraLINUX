# KDE Frameworks 6.30 Tier 1 — package batch 4

Status: **ACTIVE — 1 real PASS retained; 2 real FAIL attempts remediated and pending rebuild**

Last reviewed: **2026-09-15**

## Authority and canonical boundary

KDE Frameworks `6.30.0` remains the selected stable upstream release. KDE upstream is the source/build authority. Ubuntu Resolute is provider/compatibility target; Ubuntu and Debian packaging remain technical references only.

Batch 4 contains:

- `kitemviews` (KItemViews);
- `kglobalaccel` (KGlobalAccel);
- `syntax-highlighting` (KSyntaxHighlighting).

All three depend only on retained ECM `6.30.0-0supralinux3` inside the Tier 1 DAG. They are independent and are attempted with `fail-fast: false`.

The current canonical Tier 1 snapshot remains deliberately unchanged until Batch 4 is closed:

**10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED**.

This is not a denial of the real attempt results. In-flight attempt truth is recorded in `manifests/kde-tier1-package-campaign-batch4.json`; the canonical Tier 1 manifest and package DAG are promoted only in the closure commit. That prevents a partial batch from being confused with a completed downstream-eligible state.

PR #1 remains Draft. No merge is authorized.

## Attempt 1 — workflow `34999449194`

The first real hosted package campaign ran from commit `209f6234cbd94d0b4e02df509b25ae5a6e0922fd`.

### KItemViews — PASS retained

KItemViews `6.30.0-0supralinux1` completed the real package lane:

- job `104483912528`;
- artifact `10409267184`;
- artifact SHA-256 `7e34fa7ede21510cf6829448e7b45a5c2832aaf9ac2719b9cb4125d23b593e55`;
- upstream tests `2/2 PASS`;
- Lintian error gate PASS;
- SONAME `libKF6ItemViews.so.6` PASS;
- consumer CMake configure/build and runtime `dlopen()` smoke PASS;
- ECM predecessor `6.30.0-0supralinux3` consumed.

This is a real hosted-preflight PASS and is retained. It is **not** rebuilt merely because the other two nodes require packaging remediation.

### KGlobalAccel `-1` — historical real FAIL

KGlobalAccel `6.30.0-0supralinux1` was really attempted and failed in clean `sbuild`:

- job `104483912661`;
- artifact `10408264332`;
- artifact SHA-256 `1b7564f211967d1be8b61a96bc2a67389c6164f566e54dad79682d37a33bf6e5`;
- failure stage: `sbuild` / `dh_auto_configure` / CMake;
- tests: not reached.

The configure failure came from ECM `ECMPoQmTools`: it requires the Qt 6 `LinguistTools` CMake component for the translation install path. The package did not declare the provider package containing that component.

This is a package-attempt **FAIL**, not BLOCKED and not an infrastructure failure. It remains historical evidence after remediation.

### KSyntaxHighlighting `-1` — historical real FAIL

KSyntaxHighlighting `6.30.0-0supralinux1` failed at the same real package stage and for the same root cause:

- job `104483912313`;
- artifact `10408154532`;
- artifact SHA-256 `8601077898fcba1ea5708fbd4e5a1c0d877825f969b8b39999d7d6bf131fbfe4`;
- failure stage: `sbuild` / `dh_auto_configure` / CMake;
- tests: not reached.

`ECMPoQmTools` could not resolve required Qt 6 `LinguistTools` because the corresponding Build-Depends provider was absent.

This is also a real package-attempt **FAIL**. It is independent from KGlobalAccel and is not BLOCKED.

## Root cause and remediation

Ubuntu Resolute provides `qt6-tools-dev` `6.10.2-1`, including the `Qt6LinguistTools` CMake package. This matches the KDE-selected Qt 6.10 provider line and resolves the component actually requested by ECM.

No KDE source change, KDE version downgrade, Qt replacement or dependency-policy relaxation is justified.

The remediation is therefore packaging-only:

- KGlobalAccel becomes candidate `6.30.0-0supralinux2` and adds `qt6-tools-dev (>= 6.9.0~)` to Build-Depends;
- KSyntaxHighlighting becomes candidate `6.30.0-0supralinux2` and adds the same requirement;
- both `-1` FAIL attempts remain in the campaign evidence ledger;
- the source SHA-256, KDE upstream source, ABI baseline and consumer contracts remain unchanged.

KItemViews already declared `qt6-tools-dev` for its upstream-default Designer plugin and therefore did not suffer this omission.

## Batch 4 state model

The campaign ledger now distinguishes three facts:

- KItemViews: `PASS`, retained attempt, hosted downstream evidence available but canonical promotion deferred until batch closure;
- KGlobalAccel: last attempt `FAIL`, candidate `-2` is `remediation-pending-build`;
- KSyntaxHighlighting: last attempt `FAIL`, candidate `-2` is `remediation-pending-build`.

The canonical Tier 1 manifest continues to report all three as `pending` until the closure gate. The package DAG is likewise not rewritten to claim a pre-closure promotion. This avoids fabricating PASS state from preparation alone.

## Packaging and CI contracts retained

The remediation does not relax any existing gate. The runner still requires:

- exact KDE upstream source SHA-256;
- ECM PASS predecessor artifact;
- exact retained symbols/copyright references;
- `dpkg-source -b` followed by clean Ubuntu 26.04 `sbuild` with unshare;
- upstream tests enabled;
- expected binary Architecture/Multi-Arch/Depends/Recommends contracts;
- SONAME verification;
- retention of `.deb`, `.ddeb`, `.changes`, `.buildinfo`, `.dsc`, source tarballs and hashes;
- `sbuild` Lintian summary verification;
- standalone `lintian --fail-on error` against source and binary evidence;
- consumer CMake configure/build plus runtime SONAME load.

QCH remains disabled in the common Frameworks profile. `-doc` package names remain compatibility stubs and must not claim QCH payload that is not built.

## Scope expectation for the remediation commit

The semantic scope selector consumes package inputs rather than descriptive state/evidence metadata.

Expected behavior on the remediation commit:

- KItemViews: scope-skip; no source download, no `sbuild`, no new artifact;
- KGlobalAccel: real rebuild of `6.30.0-0supralinux2`;
- KSyntaxHighlighting: real rebuild of `6.30.0-0supralinux2`.

Repository Policy must validate the remediation state before any result is promoted.

## Deferred nodes

`KConfig` remains deferred because it exports multiple ABI libraries/symbol files and requires an explicit multi-library runner extension.

`KWidgetsAddons` remains deferred from this batch because its Linux/shared default enables Python bindings and adds Shiboken6/PySide6 surface while simpler independent nodes remain.

## Next gate

Batch 4 is not closed yet. The next valid transition requires real `-2` builds for KGlobalAccel and KSyntaxHighlighting. If both pass all gates, the closure commit can promote the three Batch 4 nodes and change the canonical count to `13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED`. If either `-2` fails, that new FAIL must be retained and remediated instead of being hidden or reclassified.
