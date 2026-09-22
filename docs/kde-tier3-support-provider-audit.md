# KDE Tier 3 support provider audit

Status: **PASS**

Reviewed: **2026-09-22**

## Scope

This provider audit covers the KDE Frameworks 6.30 support components needed by the selected Tier 3 profiles but not assigned to the Tier 1/2/3 API inventories:

- **Breeze Icons 6.30.0** — selected build predecessor for KIconThemes.
- **KDocTools 6.30.0** — CI/documentation predecessor for KIO and KDED.
- **KDED 6.30.0** — runtime predecessor for KIO.

The audit decides **provider ownership only**. It is **not a package PASS** and has `package_state_effect=none`.

## Provider rule

KDE upstream 6.30.0 defines the required component version. Ubuntu Resolute may be reused only when its candidate matches that selected upstream version. Otherwise the provider decision is `supralinux-required`.

The audit intentionally does not install Ubuntu's older KDE support packages. It queries their candidates and separately proves the non-KDE platform providers needed to build the selected upstream sources.

## Platform probes

The hosted Ubuntu 26.04 audit verifies:

- Qt 6.9+ Core/Gui/DBus/Widgets discovery;
- Python 3 + lxml for Breeze Icons generation;
- libxml2, libxslt, xmllint, DocBook XML 4.5 and DocBook XSL for KDocTools;
- retained SupraLINUX KDE predecessors are already PASS/downstream-eligible.

After CI evidence is promoted, each support component will advance either to `ubuntu-compatible` or `supralinux-required`. Package contracts remain a later gate.

No promotion to `stable` is authorized by this audit.


## PASS evidence — 2026-09-22

Hosted Ubuntu 26.04 run `35696178617`, job `106643431065`: **PASS**.

Evidence artifact:
- ID `10680368525`
- SHA-256 `419bc312852ff7a2a9b98f632b47037fce7960c620396dab51208fd3af78bf7a`

Observed Resolute candidates:
- Breeze Icons probe `kf6-breeze-icon-theme`: `6.24.0-0ubuntu1`
- KDocTools probe `kdoctools6`: `6.24.0-0ubuntu1`
- KDED probe `kded6`: `6.24.0-0ubuntu1`

KDE upstream selected version for all three is `6.30.0`. Therefore the provider decision is **`supralinux-required`** for all three support components.

The same audit proved the Ubuntu platform side needed for later builds: Qt 6.10.2, Python/lxml, libxml2, libxslt and DocBook providers were usable. Ubuntu remains provider for those general dependencies; it does not become authority for the KDE support components.

This audit has `package_state_effect=none`. Breeze Icons, KDocTools and KDED remain pending and now advance only to **package-contract-required**. No Tier 3 framework has become PASS.
