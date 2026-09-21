# KDE Frameworks Tier 2 — package Batch 3

Status: **partial PASS; KColorScheme retry + KContacts/KPackage rematerialization queued**  
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


## First real campaign — run 35620923130 attempt 2

The shared retained-input bundle and shared Resolute rootfs both passed. Rootfs artifact `10649790827` has artifact SHA-256 `83d2e99fa9dfcc9a6ccca73a86a9c99f3c574bcb209b07a47ed209b155a677e9`; rootfs content SHA-256 is `2ec1afc0318c4a3cf33a77b88f48f92e4a4ddafb8434382bf9c488987bb4aa9b`.

**KCompletion PASS:** job `106404917964`, artifact `10649102710`, artifact SHA-256 `02e2dd47d4be5d0898130abd111048ac85ed1a2b45e8b895c0b611c9c1e628f0`; 6/6 tests, Lintian PASS-errors, SONAME `libKF6Completion.so.6`, 297 exports, APT closure, consumer smoke and exact KCodecs/KConfig/KWidgetsAddons buildinfo proof all PASS.

**KPty PASS:** job `106404918040`, artifact `10649911201`, artifact SHA-256 `b2ab1931be5d21f0395f6666f9da119856d3a31cbf0889a444d82f09c735caeb`; 2/2 tests, Lintian PASS-errors, SONAME `libKF6Pty.so.6`, 70 exports, APT closure, consumer smoke and exact KCoreAddons/KI18n buildinfo proof all PASS.

KColorScheme failed before `sbuild` because the promoted materialization manifest contained one mistyped `.debian.tar.xz` hash. Artifact evidence proves the tree itself is valid; this is recorded as INFRA with `package_attempted=false` and corrected to `fa5d7f65b2b0d1281cfc762dbd083d5776eabeb0dfa14e8c51a3d681a58195b2`.

KContacts was attempted but given back at `sbuild install-deps`: Debian's reference tree adds `libkf6coreaddons-dev`, while authoritative KDE 6.30.0 KContacts CMake requires only I18n, Config and Codecs. The reference overconstraint is removed from source and binary-development dependency fields. Its disabled test override is restored.

KPackage compiled, then `dh_install` failed because `kpackagetool6.install` still requested KDocTools-generated manpages after SupraLINUX had correctly disabled optional KDocTools. Those stale install entries are removed and the disabled test override is restored.

KContacts and KPackage are integration/rematerialization cases with package-state effect `none`, not canonical FAIL. KColorScheme remains build-ready. No stable promotion is authorized.
