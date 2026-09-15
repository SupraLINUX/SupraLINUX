# KDE Frameworks 6.30 Tier 1 — package batch 4

Status: **PREPARED — build attempts pending**

Last reviewed: **2026-09-15**

## Selection

Batch 4 contains three independent Tier 1 nodes:

- `kitemviews` (KItemViews);
- `kglobalaccel` (KGlobalAccel);
- `syntax-highlighting` (KSyntaxHighlighting).

All three depend only on the retained ECM `6.30.0-0supralinux3` root inside the KDE Frameworks Tier 1 DAG. None depends on another KDE Framework, so they can be attempted in parallel with `fail-fast: false`.

KDE Frameworks `6.30.0` remains the selected stable upstream release. KDE upstream is the source/build authority. Ubuntu Resolute remains provider/compatibility target, while Ubuntu/Debian packaging is reference material only.

## Why these nodes

The current hosted package runner models one primary ABI library, one SONAME and one symbols baseline per node. These three nodes fit that model:

- **KItemViews** builds the single `libKF6ItemViews.so.6` ABI library. KDE enables its Qt Designer plugin by default when not cross-compiling, so SupraLINUX explicitly retains that path and provides Qt `UiPlugin` through `qt6-tools-dev`.
- **KGlobalAccel** builds the single `libKF6GlobalAccel.so.6` ABI library. KDE 6.30 requires Qt DBus/Gui/Widgets and, with Qt >= 6.10, `Qt6GuiPrivate`; its enabled tests additionally require QtQml. SupraLINUX therefore includes `qt6-base-private-dev` and `qt6-declarative-dev` for reasons traceable to upstream build files.
- **KSyntaxHighlighting** builds the single `libKF6SyntaxHighlighting.so.6` ABI library plus tools and a QML module. Perl is an upstream-required generator dependency. XercesC remains an optional upstream compile-time syntax-definition validator and is deliberately enabled in the selected provider profile because Resolute provides it. Python remains optional and is not promoted to a hard package requirement.

`KConfig` remains deferred because it exports multiple ABI libraries/symbol files and needs an explicit multi-library runner extension. `KWidgetsAddons` is not selected in this batch because its Linux/shared build enables Python bindings by default, bringing Shiboken6/PySide6 into the build surface while cleaner independent nodes remain.

## Packaging references and ABI baselines

The retained generic packaging-tree artifact is still:

- workflow run `34708030450`;
- artifact `10301938362`;
- artifact SHA-256 `6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6`;
- snapshot JSON SHA-256 `f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345`.

Debian sid is used only for the closer ABI symbols baseline:

- KItemViews Debian 6.28.0 symbols SHA-256 `c95ecbc24ccee885f1aa50df1c2aab41f54eb561baf66b1b219a562a5ce372cf`;
- KGlobalAccel Debian 6.28.0 symbols SHA-256 `967876c92b88b1a0654b06084c70604191464ecaded59df4bbf4dea71c0c6bb7`;
- KSyntaxHighlighting Debian 6.28.1 symbols SHA-256 `3dd1d9e56a8fa8b802ffb6708ec65984cef422bcbe7660583c907a827aec47dd`.

Any KDE 6.30 ABI delta must come from a real build and be reviewed. No symbols change is pre-declared as PASS.

## Source authority pins

The KDE 6.30 source inputs remain pinned to upstream release artifacts:

- KItemViews source SHA-256 `9452f2b0cc5dd0214b88c4ce33297866be89af4177af14f5390cfb616e49c153`, root CMake blob `d4abc8277881fff0ad85d06167b0f1e5c8e0977d`;
- KGlobalAccel source SHA-256 `e532ebd4cbfc8d6d79c6c38c556f1871315fedae8db2b69b574b9c496f171473`, root CMake blob `274623176b4c0f9b72edea3bd770530f76c8f607`;
- KSyntaxHighlighting source SHA-256 `fc429b093058bec4878306cbbfb3aa0560ff4a3f166c69504036c507fe72afcc`, root CMake blob `cbd31a8f3c8b981931fc0d39ee5991f5c7f6903a`.

Each package begins at revision `6.30.0-0supralinux1`.

## Binary compatibility contracts

The retained Ubuntu/Debian binary-contract snapshot is used as a compatibility input, not as the KDE authority.

Expected binary packages:

- KItemViews: `libkf6itemviews-data`, `libkf6itemviews-dev`, `libkf6itemviews-doc`, `libkf6itemviews6`;
- KGlobalAccel: `libkf6globalaccel-data`, `libkf6globalaccel-dev`, `libkf6globalaccel-doc`, `libkf6globalaccel6`;
- KSyntaxHighlighting: `libkf6syntaxhighlighting-data`, `libkf6syntaxhighlighting-dev`, `libkf6syntaxhighlighting-doc`, `libkf6syntaxhighlighting-tools`, `libkf6syntaxhighlighting6`, `qml6-module-org-kde-syntaxhighlighting`.

The Batch 4 runner verifies package count, Architecture, Multi-Arch, selected Depends/Recommends contracts, absence of unexpected Provides/Breaks/Replaces/Conflicts, SONAME and a CMake + runtime `dlopen()` consumer smoke.

## Documentation package policy

QCH remains disabled in the common Frameworks profile. The Debian-family `-doc` package names are retained as compatibility stubs with descriptions that explicitly state that QCH is not shipped. No package description may claim QCH payload that the build does not produce.

## CI gates

A node becomes PASS only after a real clean hosted attempt completes all current non-authoritative gates:

- exact upstream source SHA-256;
- retained ECM PASS artifact consumed as predecessor;
- exact retained symbols/copyright references verified before source-package creation;
- `dpkg-source -b` followed by clean Ubuntu 26.04 `sbuild`/unshare;
- upstream tests enabled;
- expected binary contracts checked;
- SONAME checked;
- `.ddeb`, `.changes`, `.buildinfo`, `.dsc`, source tarballs and hashes retained;
- `sbuild` Lintian summary checked;
- `lintian --fail-on error` run against `.dsc` and `.changes`;
- consumer CMake configure/build plus runtime SONAME load.

Independent FAIL nodes do not stop their peers. BLOCKED is reserved for a node that cannot be attempted because a predecessor FAILed; these three nodes share only an already-PASS ECM predecessor.

## Canonical state before attempts

Preparing Batch 4 **does not promote any Framework**.

Canonical Tier 1 remains:

**10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED**.

KItemViews, KGlobalAccel and KSyntaxHighlighting remain `pending` until real build evidence exists. PR #1 remains Draft and no merge is authorized.
