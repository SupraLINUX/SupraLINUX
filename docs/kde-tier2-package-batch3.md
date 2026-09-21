# KDE Frameworks Tier 2 — package Batch 3

Status: **4/5 PASS; KPackage offline AppStream rematerialization pending**  
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


## Package dependency closure and remediation build set

Run `35623204812` isolated KColorScheme after the corrected materialization hash. Its artifact validation passed, but `sbuild` stopped at `install-deps`: `libkf6guiaddons-dev 6.30.0-0supralinux2` requires `libkf6coreaddons-dev (>= 6.30.0~)`. KCoreAddons is not an upstream KColorScheme Framework dependency, so adding it to `predecessors` or to the KDE DAG would be incorrect.

Batch 3 therefore adds a separate `package_dependency_closure` contract. KColorScheme keeps KDE predecessors `kconfig + kguiaddons + ki18n` and adds only package closure `kcoreaddons`. The runner validates and injects the full retained KCoreAddons package set, verifies its development package at the retained SupraLINUX revision in the generated `.buildinfo`, and verifies the same revision in the consumer environment.

The KColorScheme run is retained as a real package attempt with result INFRA and package-state effect none:
- run `35623204812`
- job `106411496226`
- artifact `10649414890`
- artifact SHA-256 `2787ce2e14de33afae8c0c711554c9db8afabb552f6a41889e7185f073e6dc84`
- rootfs content SHA-256 `a7ba0a25cb68895c0cd0e7ddd2c3165d0133de1c77199a41c6e44e94a2850908`

Selective materialization run `35623204805` completed PASS:
- KContacts: job `106411141167`, artifact `10649784091`, artifact SHA-256 `bf0ea0c660da42ab84ff2e92d6196c90e65a274c40fafed1cc16a5c05f1dd432`.
- KPackage: job `106411141243`, artifact `10649014863`, artifact SHA-256 `7d805f24f4bba2b9e9f4d383252b04ef6efe7dbdba64c72aa10e50382a148188`.

The next clean-build matrix is exactly **KColorScheme + KContacts + KPackage**. KCompletion and KPty remain retained PASS and are not rebuilt. No stable promotion is authorized.


## Remediation run 35627389046 — four retained PASS

The closure-aware clean-build run `35627389046` used shared rootfs artifact `10651834404` (artifact SHA-256 `56f55edf755b2a599280f85675fe209a41062cf2463a1ee501f056a5e85378d1`, rootfs content SHA-256 `4d53ff1b4b933010a4aeef39131983a698a787c4f49f32f65a3169f376b48d12`).

KColorScheme is now PASS:
- job `106425601911`
- artifact `10651864741`
- artifact SHA-256 `d52b7bbc99d1e211600f648152781b6dc1b958c51972fdb206099c1e860e88f3`
- 2/2 tests PASS
- Lintian PASS-errors
- `libKF6ColorScheme.so.6`, 69 exports
- APT closure + external consumer PASS
- exact KConfig/KGuiAddons/KI18n buildinfo proof PASS
- exact package closure KCoreAddons `6.30.0-0supralinux4` buildinfo proof PASS.

KContacts is now PASS:
- job `106425601953`
- artifact `10653450027`
- artifact SHA-256 `369ccd7e71ee00120b78d711c5782363996d401703dacd43d57839861a3710e0`
- 33/33 tests PASS
- Lintian PASS-errors
- `libKF6Contacts.so.6`, 973 exports
- QML payload, APT closure and external consumer PASS
- exact KI18n/KConfig/KCodecs buildinfo proof PASS.

Together with retained KCompletion and KPty, Batch 3 is **4/5 PASS** and canonical Tier 2 is **10 PASS / 5 pending / 0 current FAIL / 0 BLOCKED**.

### KPackage AppStream test-environment incident

KPackage job `106425602113`, artifact `10651894789` (SHA-256 `41830724340037e0f8b16526c9ea887adc162fff00572c7e1d6b49242b44230c`) compiled and entered the restored upstream test suite. Nine of ten tests passed. `testpackage-appstream` failed because Ubuntu Resolute's AppStream `1.1.2-1` performed remote URL reachability checks against `kde.org` from the isolated build environment, where DNS/network access was unavailable.

This is classified INFRA/integration with package-state effect `none`, not a KPackage code FAIL. AppStream v1.1.2 documents `--no-net` and the equivalent `AS_VALIDATE_NONET` environment variable specifically for metadata validation without network access:
`https://github.com/ximion/appstream/blob/v1.1.2/docs/xml/man/appstreamcli.1.xml`.

SupraLINUX does not patch out or skip the KDE test. The reviewed KPackage test command becomes:

`AS_VALIDATE_NONET=1 xvfb-run -a --server-args="-screen 0 1024x768x24+32" dh_auto_test --buildsystem=kf6 -O--buildsystem=kf6 --no-parallel`

The setting is scoped to `dh_auto_test`. It disables remote URL reachability only; AppStream metadata validation and the complete KDE CTest suite remain enabled. KPackage alone returns to deterministic materialization before its next clean-build attempt. No stable APT promotion is authorized.
