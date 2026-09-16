# KDE Frameworks 6.30 Tier 1 — package Batch 7

Status: **3/3 PASS; canonical promotion complete**

Canonical Tier 1 after promotion: **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**. Historical FAIL attempts remain immutable in `manifests/kde-tier1-package-batch7-attempts.json`; they are not BLOCKED and are not erased by later PASS results.

## Final retained PASS

- **KCalendarCore `6.30.0-0supralinux5`** — run `35130213945`, job `104909057699`, artifact `10461386548`, artifact SHA-256 `6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6`, rootfs `eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6`, 507/507 tests PASS.
- **KCoreAddons `6.30.0-0supralinux4`** — run `35122522242`, job `104883541991`, artifact `10457958023`, artifact SHA-256 `c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`, rootfs `dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794`, 34/34 tests PASS.
- **KWidgetsAddons `6.30.0-0supralinux7`** — run `35145607543`, job `104960718770`, artifact `10467164025`, artifact SHA-256 `f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e`, rootfs `d381a2d238103d21dbce47af60377b48ca77b385ab8598d135d30386ac17cf12`, 27/27 tests PASS.

Every final PASS completed strict Lintian error gating, exact local-package APT closure, Python import for enabled bindings and C++ consumer smoke. KWidgetsAddons retained all upstream tests and its Designer plugin; its deterministic test fixture runs 25 suites under bare Xvfb and only the two activation-dependent gesture suites under verified Openbox.

## Shared causes resolved

The campaign discovered and validated the clean-build providers required by ECM/Shiboken: Clang/LLVM built-ins plus `python3-build` and `python3-setuptools`. Package-specific remediations then handled KCalendarCore translation ownership/ABI minima, KCoreAddons ABI minima, and KWidgetsAddons deterministic GUI-test fixture, Designer-plugin `${shlibs:Depends}` and reviewed ABI minima. KDE source and selected upstream defaults remain unchanged.

## Next frontier

KGuiAddons is no longer blocked by KCoreAddons: the predecessor has a retained SupraLINUX PASS. It remains `lane-pending` until the local-predecessor runner is implemented; that runner must consume the SupraLINUX KCoreAddons artifacts rather than Ubuntu KDE packages.

PR #1 remains **OPEN + DRAFT**. No merge is authorized.
