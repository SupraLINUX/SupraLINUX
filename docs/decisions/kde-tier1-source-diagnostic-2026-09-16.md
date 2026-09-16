# KDE Tier 1 global source diagnostic lane

Date: **2026-09-16**

Status: **SECOND CAMPAIGN COMPLETE — 6 DIAG_PASS / 1 DIAG_FAIL; KI18n locale-fixture remediation prepared**

## Purpose and semantics

The package DAG remains the only path that may promote a KDE node to package `PASS`. The source-diagnostic lane discovers provider/configure/build/test failures across independent nodes before every specialized Debian packaging lane exists.

It reports only `DIAG_PASS` and `DIAG_FAIL`. Neither value changes the canonical package DAG. A `DIAG_PASS` does not prove Debian package splits, symbols/ABI policy, Lintian, Multi-Arch, `.deb` runtime closure, `.changes`, `.buildinfo` or downstream eligibility.

## First campaign — run 35131119792

Commit `1f5fcdc68e1bbb2a7cc3f93dc20687aadc15cec0` attempted all seven nodes independently with `fail-fast: false`.

- KConfig: `DIAG_FAIL` at configure because `Qt6::CorePrivate` referenced the missing versioned Qt private-header surface; `qt6-base-private-dev` was absent.
- KI18n: `DIAG_FAIL`, 14/17 tests; the three failures expected French `iso-codes` translations.
- Sonnet, Kirigami, KQuickCharts, KUserFeedback and Prison: `DIAG_PASS`.

This campaign established two independent provider/fixture hypotheses without changing package state.

## Second campaign — run 35134670463

Commit `e0228ddb21fb57a639245b2fb93494854bccd928` reran the seven nodes once because the common runner and selector contract changed.

| Node | Result | Job | Artifact | Artifact SHA-256 |
| --- | --- | ---: | ---: | --- |
| KConfig | `DIAG_PASS` | `104923940842` | `10463162930` | `8af6e430985ac9d46886032c7e4073eaacd6a599eb66f005b15abba723b10c0c` |
| KI18n | `DIAG_FAIL` | `104923940865` | `10462837843` | `96801e17f96956a616a06be32e11facdde6dfdef0809ce966865a8d95718e537` |
| Sonnet | `DIAG_PASS` | `104923941024` | `10462543371` | `c832539c4fa053d125f62764886bbad6158814e33a0a39afcdd914f2b62b3bf6` |
| Kirigami | `DIAG_PASS` | `104923940883` | `10462063740` | `1014cb8cce1b43f9a3912b4e45acf752a2bf9520bc8dad2c7a6b8f2e1f9077b6` |
| KQuickCharts | `DIAG_PASS` | `104923940752` | `10462337704` | `ee33a55f58ea0e56c7d8af5cfa571790531e92f5897b1f88c25520ceae0c042b` |
| KUserFeedback | `DIAG_PASS` | `104923940498` | `10462087859` | `baf1b41d7b74b4001b165ef5426ec78cd5ffdec7acc15e43234a7a0d5035727e` |
| Prison | `DIAG_PASS` | `104923940882` | `10462272649` | `3f7dfd401f1906845b8465a7059ed4cda55b6e7fd520108a90bc8a1a5d7713b0` |

KConfig therefore validates the provider correction: `qt6-base-private-dev` plus a real versioned private-header assertion is sufficient for the source diagnostic.

## KI18n v2 classification

The second attempt disproved the narrower hypothesis that French catalogs were simply absent. `language-pack-fr-base` installed real `iso_3166-1.mo` and `iso_3166-2.mo` catalogs and the pre-build assertion passed, but the same three upstream tests still failed.

The common test wrapper forced `LANG=C.UTF-8 LC_ALL=C.UTF-8`. KI18n's upstream tests intentionally manipulate `LANG` and `LANGUAGE`; for example, `kcountrytest` sets `LANG=fr_CH.UTF-8`, while `kcatalogtest` constructs a long `LANGUAGE=fr_CH:...` value to exercise KCatalog/gettext behavior. `LC_ALL` has higher locale precedence and therefore neutralized the test's `LANG` selection. With the effective C locale, gettext does not exercise the intended `LANGUAGE` translation path.

This is a diagnostic-fixture failure, not justification to patch KDE source or disable tests.

## KI18n v3 remediation

The node profile now declares its locale requirements and test environment explicitly:

- provider `locales-all` supplies precompiled locales;
- `language-pack-fr-base` continues to supply the required French catalogs;
- `en_US.UTF-8` and `fr_CH.UTF-8` must both be discoverable through `locale -a` before configure;
- the test wrapper sets `LANG=en_US.UTF-8` and unsets `LC_ALL` only for KI18n;
- the unchanged upstream test suite remains the proof gate.

The runner reads this fixture from node metadata. Other nodes retain the existing `C.UTF-8` default. Once this common runner change has passed, later provider/profile changes can use the existing per-node semantic selector instead of rerunning unrelated green nodes.

## Upstream defaults

The runner does not disable KDE features to obtain a green result. It preserves and checks the selected KDE 6.30 defaults, including GUI/QML/DBus for KConfig, QML for KI18n, backends and Designer plugin for Sonnet, Desktop style and DBus for Kirigami, and enabled multimedia/barcode paths for Prison.

## Relationship to package lanes

1. source diagnostics discover failures broadly and early;
2. specialized package lanes produce real Debian package evidence;
3. only package `PASS` artifacts may feed downstream package nodes;
4. diagnostic fixes must still pass the full package gates;
5. package campaigns continue independently of diagnostic FAILs that do not form DAG predecessors.

KGuiAddons remains outside this seven-node source matrix because its package validation must consume the retained local KCoreAddons PASS rather than substitute an Ubuntu KDE package.
