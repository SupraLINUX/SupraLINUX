# KDE Tier 3 support package contracts

Status: **contracts ready — materialization pending**

Reviewed: **2026-09-22**

## Scope

This lane prepares packaging contracts for the three KDE Frameworks 6.30 support components selected to be provided by SupraLINUX:

- Breeze Icons;
- KDocTools;
- KDED.

The provider decision is already PASS and does not need to be repeated. This gate captures packaging references only.

## Authority versus reference

KDE upstream 6.30.0 remains authoritative for source, feature defaults and dependencies.

Ubuntu Resolute and Debian sid are used only as **technical packaging references**. Their package names, dependency metadata and Debian packaging can inform compatibility/materialization, but cannot lower or replace the selected KDE source.

The hosted reference job uses signed `deb-src` metadata for both distributions and records:

- source package/version;
- binary package set;
- Build-Depends / Build-Depends-Indep;
- VCS metadata;
- source-file SHA-256 records.

For Debian, the selector requires an exact 6.30.0 source reference when available and fails rather than silently materializing from a different KDE series.

## Lifecycle

Reference capture has `package_state_effect=none`. No source package is built and no Tier 3/support node becomes PASS.

After capture PASS, the resulting records must be reviewed into explicit SupraLINUX contracts before materialization is authorized. Promotion to `stable` remains impossible without explicit user approval.


## Reference capture PASS — 2026-09-22

Run `35696911023`, job `106645687497`, artifact `10680304903`, SHA-256 `677f5a0065d3fab2983471a0ccc54ba640b980d25740773e35eea1c5ef9ee95d`: **PASS**.

Normalized snapshot SHA-256: `27012f04c7686e94061055a6aeb33d12f2d17521a151c5742b5e2b2863d5c4d8`.

Captured source references:
- Breeze Icons: Ubuntu `6.24.0-0ubuntu1`; Debian `4:6.30.0-1`.
- KDocTools: Ubuntu `6.24.0-0ubuntu1`; Debian `6.30.0-1`.
- KDED: Ubuntu `6.24.0-0ubuntu1`; Debian `6.30.0-1`.

Debian's 6.30 Breeze source exposes both the newer `breeze-icon-theme*` packages and the `kf6-breeze-icon-theme*` compatibility names, while Ubuntu 6.24 exposes only the latter. Because that distinction affects Ubuntu compatibility and future KDE consumers, the package contract is not finalized from source-record metadata alone.

The active next gate downloads and verifies the exact pinned Ubuntu/Debian source files, extracts both `debian/` trees, records deterministic tree hashes, and retains parsed control relations. It remains a technical-reference operation with `package_state_effect=none`.


## Packaging-tree capture PASS

Run `35697315731`, job `106646990521`, artifact `10681410828`, SHA-256 `819917d75fc00de52a7d3bb851a4e1a9d467138bad6e7218c10c95a62babf61f`: **PASS**.

The deterministic packaging-tree index SHA-256 is `dc5e72000afc3843f804177a383ad81fe3cd3cfb346c955a809389243cf382fa`.

Selected Debian 6.30 tree hashes:
- Breeze Icons: `c0127864df0444373e3256559cd1b7d0f3e326d71630c2a4c1eab334ee81d416`.
- KDocTools: `208eebbad9c402e0b6803cfa0b20b2c9e3b843415f0a44c843a1c7c64c4ed3b5`.
- KDED: `035f17f065f2d31e9650d979b51b0d79989ea142503436de30e93cc717c5fbdc`.

## Final support contracts

### Breeze Icons

SupraLINUX will materialize source package `kf6-breeze-icons` as `4:6.30.0-0supralinux1`.

The target binary family follows the current 6.30 packaging model:
- real primary packages: `breeze-icon-theme`, `breeze-icon-theme-rcc`;
- Ubuntu-name transitional packages: `kf6-breeze-icon-theme`, `kf6-breeze-icon-theme-rcc`;
- development/runtime library packages: `libkf6breezeicons-dev`, `libkf6breezeicons6`.

The epoch `4:` is intentionally retained. The historical primary `breeze-icon-theme` line already uses epoch 4; dropping it would make a nominal 6.30 build compare older than installed `4:5.x` packages and could prevent the intended upgrade.

The 6.30 transition relations are retained: the new primary packages Break/Replace old `kf6-breeze-icon-theme*` payload packages below the transition threshold, while the `kf6-*` packages become dependency-only compatibility bridges. This preserves Ubuntu package names while moving the payload to the current primary names.

`BINARY_ICONS_RESOURCE=ON` is selected only to retain the RCC compatibility output. This is an integration/package-output adaptation, not a KDE desktop feature change.

### KDocTools

Source package `kf6-kdoctools` becomes `6.30.0-0supralinux1` and preserves:
`kdoctools6`, `libkf6doctools-dev`, `libkf6doctools-doc`, and `libkf6doctools6`.

The selected profile keeps KArchive enabled, includes KI18n translations, and builds QCH documentation. Retained KDE 6.30 predecessors are ECM, KArchive and KI18n.

### KDED

Source package `kf6-kded` becomes `6.30.0-0supralinux1` and preserves `kded6` plus `kded6-dev`.

Its normal Framework dependencies come from retained PASS artifacts. KDocTools is an explicit selected CI/documentation predecessor, so KDED is placed one support build level after KDocTools.

## Build order

Support build level 0: Breeze Icons + KDocTools.

Support build level 1: KDED, only after KDocTools PASS.

All three remain canonical pending. Contract readiness authorizes materialization only; no package build or PASS has occurred yet.
