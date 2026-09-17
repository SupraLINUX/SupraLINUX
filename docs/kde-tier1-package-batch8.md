# KDE Frameworks Tier 1 Batch 8 — KGuiAddons

Status: **remediation pending after successful compile / symbols-Lintian FAIL**  
Date: **2026-09-17**  
Frameworks: **6.30.0**

## Scope and authority

Batch 8 contains one pending Tier 1 node: `kguiaddons`. KDE upstream 6.30.0 is authoritative.

- source: `https://download.kde.org/stable/frameworks/6.30/kguiaddons-6.30.0.tar.xz`
- source SHA-256: `e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d`
- current remediation revision: `6.30.0-0supralinux2`

The retained Debian 6.28.0 packaging tree from run `34708030450`, artifact `10301938362`, is a technical package-layout/symbols/copyright reference only. It does not define KDE version, Qt selection or enabled upstream features.

## Upstream defaults

SupraLINUX preserves the KGuiAddons Linux feature profile: Wayland, X11, DBus, the `geo:` handler, Python bindings and tests are enabled. QCH remains disabled by the common Frameworks packaging profile.

## KCoreAddons relationship

KGuiAddons remains a Tier 1 Framework. Its root build does not make KCoreAddons a Framework build dependency, so `libkf6coreaddons-dev` is deliberately absent from KGuiAddons `Build-Depends`.

The public `KImageCache` header does include KCoreAddons' `kshareddatacache.h`. Therefore `libkf6guiaddons-dev` depends on `libkf6coreaddons-dev (>= 6.30.0~)` and the consumer smoke validates this public development surface against the retained SupraLINUX KCoreAddons PASS.

Retained KCoreAddons evidence:

- version `6.30.0-0supralinux4`;
- workflow run `35122522242`;
- artifact `10457958023`;
- artifact digest `sha256:c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`.

The exact retained package hashes are pinned in the Batch 8 campaign and Repository Policy validator.

## Binary contract

Batch 8 expects seven packages:

- `libkf6guiaddons-bin`;
- `libkf6guiaddons-data`;
- `libkf6guiaddons-dev`;
- `libkf6guiaddons-doc`;
- `libkf6guiaddons6`;
- `qml6-module-org-kde-guiaddons`;
- `python3-kguiaddons`.

Runtime SONAME gate: `libKF6GuiAddons.so.6`.

## Attempt 1 — retained preparation FAIL

Head `64585a32ce481350df188237b71b5354d9aec4a7`, router run `35182478592`, job `105077454579`, artifact `10480782714`, digest `sha256:690e29e1c44835c1568eaca7f950393fbd3487f03be050d1f4f47880bb107b9e`.

Result: FAIL at `campaign-validation`, before source-package creation. The materialized signing key was the KCoreAddons reference key instead of the KGuiAddons key. The manifest pin was already correct. Repository Policy was hardened to hash the materialized key before build execution.

Because no source package was produced, revision remained `6.30.0-0supralinux1`.

## Attempt 2 — retained predecessor-hash FAIL

Head `6df438c345a10e679bc4f52d3bcfd427cb4fa603`, Repository Policy run `35183197615` PASS, router run `35183198027`, job `105079635248`, artifact `10481500636`, digest `sha256:0011def5c3111d67266edc95bbd91b178057d3e65f8ff571e09e112d1658bf61`.

Result: FAIL at `retained-input-validation`, before source-package creation. The correct retained KCoreAddons artifact had been selected, but two inner package SHA-256 values were copied incorrectly. They were replaced with the hashes recorded by the retained PASS artifact itself and the validator was hardened to pin workflow run, artifact ID, artifact digest and all three package hashes.

Revision again remained `6.30.0-0supralinux1`.

## Attempt 3 — successful build, symbols-Lintian FAIL

Head `a5d3d047b9c54a91f1c31dfe7bfcfb437e0f6963` passed Repository Policy run `35183595001`. The real package attempt ran in router run `35183595245`, job `105080827688`.

Retained evidence:

- artifact `10480549680`;
- artifact digest `sha256:eee95d50f04a8517eca828cff25cd52e0306684cfc61137569b15fb89d402fcd`;
- result: FAIL;
- stage: `sbuild`;
- package revision: `6.30.0-0supralinux1`;
- `sbuild` final status: **successful**;
- CTest: **9/9 PASS**;
- Lintian: **FAIL**.

The only blocking Lintian error was `symbols-file-contains-current-version-with-debian-revision`. `dpkg-gensymbols` discovered two symbols absent from the retained Debian 6.28 symbols reference and assigned the current package revision automatically:

```text
_ZNK16KSystemClipboard13ownsClipboardEv@Base 6.30.0-0supralinux1
_ZNK16KSystemClipboard13ownsSelectionEv@Base 6.30.0-0supralinux1
```

This is a packaging/ABI-metadata FAIL after a successful compile, not an upstream compile failure or a missing KCoreAddons build edge.

## Symbols remediation and upstream evidence

The minimum ABI version is not guessed from the current 6.30 build. KDE upstream tag `v6.29.0` exposes both `KSystemClipboard::ownsSelection()` and `ownsClipboard()` and documents each as `since 6.29`; tag `v6.28.0` contains neither method. Therefore their correct minimum stable Frameworks version is **6.29.0**.

SupraLINUX adds `debian/libkf6guiaddons6.symbols.supralinux-overlay` containing exactly:

```text
 _ZNK16KSystemClipboard13ownsClipboardEv@Base 6.29.0
 _ZNK16KSystemClipboard13ownsSelectionEv@Base 6.29.0
```

`debian/rules` appends the overlay before `dh_makeshlibs`. This records upstream ABI history while retaining the Debian 6.28 symbols file as the technical baseline.

Because attempt 3 created the source package and completed a binary build, this packaging remediation advances the Debian revision to **`6.30.0-0supralinux2`**. Attempt 3 remains in the append-only attempt ledger.

## Build/test gate

A PASS still requires source hash verification, exact retained ECM/KCoreAddons inputs, clean Resolute `sbuild`, non-zero 100% CTest PASS, Lintian source+binary error gate, seven-package contract, SONAME, Python import, APT closure, KImageCache consumer CMake smoke and proof that KCoreAddons did not enter KGuiAddons Build-Depends.

## Promotion rule

Until a later Batch 8 run is a real PASS:

- canonical `manifests/kde-frameworks-tier1.json` remains `kguiaddons: pending`;
- KGuiAddons is not downstream-eligible;
- canonical Tier 1 remains `21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED`;
- Batch 8 remains `remediation-pending-build`.

Only a real PASS may promote KGuiAddons into the canonical Tier 1 manifest.
