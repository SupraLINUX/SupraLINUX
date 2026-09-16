# KDE Tier 1 global source diagnostic lane

Date: **2026-09-16**

Status: **THIRD CAMPAIGN COMPLETE — 7 DIAG_PASS / 0 DIAG_FAIL**

## Purpose and semantics

The package DAG remains the only path that may promote a KDE node to package `PASS`. The source-diagnostic lane discovers provider/configure/build/test failures across independent nodes before every specialized Debian packaging lane exists.

It reports only `DIAG_PASS` and `DIAG_FAIL`. Neither value changes the canonical package DAG. A `DIAG_PASS` does not prove Debian package splits, symbols/ABI policy, Lintian, Multi-Arch, `.deb` runtime closure, `.changes`, `.buildinfo` or downstream eligibility.

## Campaign 1 — run `35131119792`

Commit `1f5fcdc68e1bbb2a7cc3f93dc20687aadc15cec0` attempted all seven nodes independently with `fail-fast: false`.

- KConfig: `DIAG_FAIL` because `Qt6::CorePrivate` referenced a missing versioned private-header surface; the provider profile lacked `qt6-base-private-dev`.
- KI18n: `DIAG_FAIL`, 14/17 tests, initially exposing missing effective French locale data.
- Sonnet, Kirigami, KQuickCharts, KUserFeedback and Prison: `DIAG_PASS`.

## Campaign 2 — run `35134670463`

Commit `e0228ddb21fb57a639245b2fb93494854bccd928` validated the KConfig provider correction and refined the KI18n diagnosis.

KConfig became `DIAG_PASS`. KI18n remained `DIAG_FAIL` even though real French `iso_3166-1.mo` and `iso_3166-2.mo` catalogs were installed. The common runner forced `LC_ALL=C.UTF-8`, which has higher locale precedence than the `LANG` and `LANGUAGE` values intentionally manipulated by KI18n's upstream tests. That fixture prevented the tests from exercising the intended gettext locale path.

The result established a CI-fixture defect, not a KDE source defect.

## Campaign 3 — run `35138333645`

Commit `6b3a8b9f408c5fff4bceec81ac9ffb3e47a4dbd3` validated the final locale fixture and revalidated all seven nodes because the common diagnostic runner changed.

| Node | Result | Job | Artifact | Artifact SHA-256 |
| --- | --- | ---: | ---: | --- |
| KConfig | `DIAG_PASS` | `104936243505` | `10464074545` | `9f05b0e368c4d1a7eb3dbec441680b423fd3f8b4a7fc2a0cdcbf9edbb3ca6e68` |
| KI18n | `DIAG_PASS` | `104936243967` | `10463404553` | `86b5f05313d164358ac36e1cc4982b72fad90bad3175114d2b2b493691a6bec3` |
| Sonnet | `DIAG_PASS` | `104936243844` | `10464073832` | `6b17c7f02213282a520f4127feb010e9a37dbbafce9c8ab17d7f76164b22d7b6` |
| Kirigami | `DIAG_PASS` | `104936243949` | `10464419377` | `f83a7e508fa2031dcf5401a7590e9598ab3d5888230af60b153c4b77d4b53185` |
| KQuickCharts | `DIAG_PASS` | `104936243779` | `10463808939` | `5d1023d260fe167d846a8b3f16310c6771bb08f79688095bd27ba5ea79798a28` |
| KUserFeedback | `DIAG_PASS` | `104936243847` | `10463474227` | `490be26e6790ac56114948be44e0b068061479e448c1ba1b3ee227c231902d39` |
| Prison | `DIAG_PASS` | `104936243826` | `10464172535` | `cee0b26d3c3dbad53b0924d8c15cde6b11813863a4e800634a8b9ae2cfdb90b5` |

Result: **7/7 DIAG_PASS**.

## KConfig validated provider contract

The selected Linux build path requires the Qt private Core surface. Ubuntu Resolute provides it through `qt6-base-private-dev`. The runner additionally asserts that the versioned `QtCore/.../QtCore/private` directory actually exists before CMake configure. Campaigns 2 and 3 both validate that provider mapping.

## KI18n validated locale contract

The final diagnostic profile declares the test fixture rather than overriding upstream locale behavior:

- `locales-all` provides the required compiled locales;
- `language-pack-fr-base` provides the French iso-codes catalogs;
- `en_US.UTF-8` and `fr_CH.UTF-8` must both be visible through `locale -a`;
- the KI18n test wrapper sets `LANG=en_US.UTF-8` and leaves `LC_ALL` unset;
- upstream tests remain unchanged.

Campaign 3 `DIAG_PASS` validates this correction. No KDE source patch and no test exclusion is required.

## Upstream defaults

The diagnostic runner does not disable features to obtain green results. It preserves and validates the selected KDE 6.30 defaults, including GUI/QML/DBus for KConfig, QML for KI18n, spell backends and Designer plugin for Sonnet, Desktop style and DBus for Kirigami, and enabled multimedia/barcode paths for Prison.

## Scope policy

The selector is per-node after common infrastructure stabilizes:

- node-specific provider/profile changes rerun only that node;
- evidence-only `last_campaign` changes do not rerun diagnostics;
- common runner/workflow/provider-contract changes conservatively rerun the matrix;
- documentation-only changes do not run source diagnostics.

## Relationship to package lanes

1. source diagnostics discover provider/configure/build/test failures broadly;
2. specialized package lanes produce `.deb` evidence;
3. only package `PASS` artifacts may feed downstream package nodes;
4. diagnostic corrections must still pass package gates;
5. `DIAG_PASS` never implies downstream eligibility.

KGuiAddons remains outside this source matrix because its development/consumer contract must consume the retained local KCoreAddons PASS rather than substitute an Ubuntu KDE package.
