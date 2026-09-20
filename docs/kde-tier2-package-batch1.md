# KDE Frameworks 6.30 — Tier 2 Batch 1 (KAuth)

Status: **KAuth PASS; canonical promotion candidate**  
Date: **2026-09-20**

Batch 1 deliberately contains only KAuth. KMime remains independently gated by ADR-0002 and does not block this runnable DAG node.

## Selected profile

- KAuth upstream: 6.30.0, SHA-256 `60b75e02abc2bfbb247c586e3ab94def7ecd7b4e1ddb8260358951d84d9ea8c9`.
- ECM predecessor: retained SupraLINUX `6.30.0-0supralinux3`.
- KCoreAddons predecessor: retained SupraLINUX `6.30.0-0supralinux4`, artifact `10457958023`.
- KWindowSystem predecessor: retained SupraLINUX `6.30.0-0supralinux4`, artifact `10428130399`.
- Linux authorization backend: `POLKITQT6-1`.
- Helper backend: `DBUS`.
- Fake backend fallback: rejected for this profile.

The runner passes the retained Framework packages to the clean Resolute sbuild as exact local package inputs, so Ubuntu cannot satisfy the KAuth build by silently substituting an older KCoreAddons/KWindowSystem.

## Debian compatibility reference

Debian `kf6-kauth 6.30.0-1` is used only as a technical package-contract reference. Its `debian.tar.xz` is pinned at SHA-256 `f304bd772cf958ca9dccab78ad33e12f8e2f7bf0b038999e629cf270bb068fc3`. The runner imports the exact `libkf6authcore6.symbols` file from that pinned tarball before source-package assembly.

SupraLINUX keeps the Ubuntu/Debian binary package names:
`libkf6auth-data`, `libkf6auth-dev`, `libkf6auth-dev-bin`, `libkf6auth-doc`, `libkf6authcore6`.

## Gates

A PASS requires:
- non-zero upstream CTest suite fully passing under Xvfb + D-Bus session;
- real Polkit backend and DBus helper plugin present;
- `KF6AuthConfig.cmake` recording the selected backend profile;
- SONAME `libKF6AuthCore.so.6` and non-empty exported ABI;
- pinned symbols contract;
- development-contract audit;
- Lintian error gate;
- exact APT runtime closure using built packages plus retained predecessor packages;
- external CMake consumer compile/run.

PASS evidence is recorded below; the retained FAIL/INFRA history remains part of the campaign evidence.

## Attempt 1 — source-package FAIL

Run `35496293561`, job `106039776267`, artifact `10600690671`, SHA-256 `8387279d8cdadd05cf73c2c16177f1d2635a331648638ca3397cef77d04c1ac3`.

The attempt failed in `dpkg-source` before sbuild. The helper-install-dir patch declared a seven-line hunk but ended after six context lines, so quilt rejected it as malformed. Retained predecessor artifacts, source SHA, backend profile and Debian symbols reference all validated before this failure.

Classification: **real package FAIL**, `package_attempted=true`, stage `source-package`, `sbuild_started=false`. Revision `6.30.0-0supralinux2` fixes only the quilt hunk structure.

## Attempt 2 — symbols contract FAIL after tests PASS

Run `35496445770`, job `106040197856`, artifact `10601410551`, ZIP SHA-256 `4ea7588f1749ce7588cc06fc6bc9dc80350d7fc270bb30688ef173ee6262cfc9`, rootfs SHA-256 `bf90d45c1b750369d482757a4521ea3578a5ef8e10835bf008b258ffad49cbcf`.

The corrected source package built through configuration/compilation and upstream CTest reported **6/6 PASS**. Both selected plugins were installed: PolkitQt6-1 authorization backend and DBus helper backend. Packaging then failed in `dh_makeshlibs`.

The pinned Debian 6.30 symbols template SHA-256 is `77ab200ea8f5e9335831ef021dd2e446598b95d886d13237e91ea69e25812259`. Two missing C++ template instantiations were already tagged `optional=templinst` and were not causal. The only mandatory missing entries were RTTI/vtable symbols for `KAuth::AuthBackend::Private`, which is defined only in `src/AuthBackend.cpp`.

Revision `6.30.0-0supralinux3` keeps the complete Debian 6.30 symbols baseline and changes exactly those two implementation-private entries to `optional=private`. No public ABI symbol is weakened.

## Attempt 3 preflight validator incident

Repository Policy run `35497248424`, job `106042393365`, failed before the queued KAuth build started. The Tier 2 discovery validator still hardcoded the original `6.30.0-0supralinux1` candidate even though the remediation revision is `6.30.0-0supralinux3`.

Classification: **INFRA**, `package_attempted=false`, `package_state_effect=none`. The validator now checks that package identity and current packaging revision agree, rather than encoding a specific remediation number.

## Superseded-run scope hardening

PR CI run `35497248610`, KAuth job `106042424661`, was cancelled while still queued when the validator remediation advanced the branch. It never downloaded predecessors or entered `Build and validate`; therefore it is not attempt 3.

The semantic scope selector now treats the current prepared/remediation revision as runnable until that exact package version appears in the real-attempt ledger with `package_attempted=true`. This prevents a superseded run from stranding a remediation merely because the subsequent commit is metadata-only. Once an attempt exists for that revision, ordinary event-delta fingerprinting resumes.

## Attempt 3 — PASS

KAuth `6.30.0-0supralinux3` completed successfully in PR CI run `35497461178`, job `106043001431`.

Artifact: `10601382235`; ZIP SHA-256 `443a47a67188a52faae6c20b03c2c53203d5a9386dbbb5765af4f69e0cd1744b`; rootfs SHA-256 `15113b108b939e2575758c6696fc34808dfa925fa2dd3cc5e6c13e65e7be4668`.

Final gates: **6/6 CTest PASS**, Lintian error gate PASS, `libKF6AuthCore.so.6` with 118 exported symbols, PolkitQt6-1 backend, DBus helper, development-contract PASS, exact APT closure PASS and external `KF6::AuthCore` consumer PASS. The adjusted symbols template SHA-256 is `b8cf2fa877c94255f015cee08b89816d538cba23f1064d0360a329189fee0b78`; only the two implementation-private RTTI/vtable entries are optional.

KAuth is therefore downstream-eligible and the Tier 2 canonical package state becomes **1 PASS / 1 pending / 0 current FAIL / 0 BLOCKED**. KMime is the sole pending Tier 2 node and remains decision-gated by ADR-0002.

Repository Policy run `35497460988` failed independently in the scope-test fixture because an empty `docs/` directory vanished after `git reset --hard`. The real KAuth package job still completed PASS. The promotion candidate fixes that fixture without rebuilding KAuth.
