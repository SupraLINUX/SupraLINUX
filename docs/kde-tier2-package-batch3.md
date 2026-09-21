# KDE Frameworks Tier 2 — package Batch 3

Status: **prepared; clean-build campaign queued**  
Date: **2026-09-21**

Batch 3 covers KColorScheme, KCompletion, KContacts, KPackage and KPty. All five are package-state `pending` and `build-ready` from materialization run `35608790364`; this lane is the first real package attempt for this group.

## Multi-predecessor execution

Every node consumes its complete retained Tier 1 Framework predecessor set:

- KColorScheme ← KConfig + KGuiAddons + KI18n
- KCompletion ← KCodecs + KConfig + KWidgetsAddons
- KContacts ← KI18n + KConfig + KCodecs
- KPackage ← KArchive + KI18n + KCoreAddons
- KPty ← KCoreAddons + KI18n

ECM `6.30.0-0supralinux3` remains a shared retained PASS input.

The workflow prepares one **shared retained input** bundle for the campaign instead of downloading the same historical artifacts independently in every matrix job. Before the package matrix begins, that bundle is validated fail-closed against exact Debian package names, versions and SHA-256 values. Each node then revalidates only its declared predecessors and supplies every retained `.deb` to the same clean `sbuild` invocation via `--extra-package`.

The generated `.buildinfo` must prove that every predecessor development package was actually consumed at the exact retained SupraLINUX revision. This prevents a successful-looking build from silently falling back to an older Ubuntu KDE development package.

## State semantics and gates

A real attempt begins immediately before `sbuild`, recorded as `package_attempted=true`. Failures while preparing the rootfs, retained input bundle or materialized source remain **INFRA** with no package-state effect. A post-`sbuild` failure requires root-cause classification before it can become canonical FAIL; FAIL still requires a node-owned root cause. BLOCKED is never FAIL.

The matrix remains **fail-fast: false**. PASS requires clean sbuild, a non-zero upstream CTest PASS summary, exact binary set, Lintian error-free result, expected SONAME with non-empty exports, APT runtime closure, external CMake consumer smoke and proof for every retained predecessor. KContacts additionally requires its QML payload smoke.

No package is rebuilt from an older materialization. The retained materialization for all five is run `35608790364`, and provider audit/reference capture/materialization must remain skipped unless a semantic input changes.

No Batch 3 result publishes automatically. PASS only makes a package eligible for later `testing` handling; promotion to `stable` remains manually tested and requires explicit user approval.
