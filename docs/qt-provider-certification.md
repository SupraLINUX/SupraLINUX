# Qt provider certification

Provider preflight: **PASS**  
Final certification: **pending**  
Last reviewed: **2026-09-12**

## Authority and provider

KDE upstream is the authority for the Qt version required by the desktop. Ubuntu may provide that Qt only when it satisfies the KDE-selected requirement and SupraLINUX compatibility gates.

Current KDE schedule evidence:

- Plasma 6.7 selects Qt **6.10**: <https://community.kde.org/Schedules/Plasma_6>
- Current selected Plasma: **6.7.5**.

Current Ubuntu Resolute candidate evidence includes:

- `qt6-base-dev` / private: 6.10.2+dfsg-7;
- `qt6-declarative-dev` / private: 6.10.2+dfsg-3;
- `qt6-wayland-dev` / private: 6.10.2-4;
- `qt6-svg-dev`: 6.10.2-2;
- `qt6-shadertools-dev`: 6.10.2-1;
- `qt6-tools-dev` / tools: 6.10.2-1;
- `qt6-5compat-dev`: 6.10.2-1.

Although Debian revisions differ, they all resolve to upstream **Qt 6.10.2**. Qt documents patch releases as maintenance releases and its Qt 6 compatibility commitments remain subject to the documented toolchain/configuration/private-API caveats: <https://doc.qt.io/qt-6.10/qt-releases.html>.

These facts and the successful provider preflight make Ubuntu Qt 6.10.2 a validated **reuse candidate** for the Plasma/Frameworks baseline. They do **not** constitute final KDE-stack certification.

## Provider preflight evidence

First real PASS:

- commit: `bffcc3ce42f65bc73b784dbf94b90429be2262b0`;
- workflow: `Qt provider preflight`;
- run: **34665704108**;
- artifact: **10288816586**;
- artifact SHA-256: `90a25a24b60dcc02691c7043eb3a985f21013c73e3ea4489a7427fa74e618e33`;
- hosted image: Ubuntu 26.04.1, image `ubuntu-26.04` version `20260907.131.1`;
- effective Qt runtime: **6.10.2**;
- compiler observed: GCC **15.2.0**;
- CMake configure/build: **PASS**;
- runtime probe: **PASS**.

The same commit also had Repository Policy run `34665704104` PASS and package preflight `34665704091` PASS with its expensive `sbuild` path intentionally skipped.

Second hardened PASS:

- branch commit: `8cf0b4c9b156937c7ae322970d57bc5fd5561a9c`;
- workflow run: **34666082893**;
- artifact: **10289775722**;
- artifact SHA-256: `67e8254f7c54a72e5c99000e9f00fb180a9b78b6ac39c05ad56ba0a4a2fa979b`;
- result: **PASS** after adding the stricter `installed Debian version == current APT candidate` requirement for every baseline package.

On that same head, Repository Policy run **34666082909** is retained as a transition **FAIL**. All pre-existing architecture/KVM checks and the general repository validator passed; only `Validate Qt provider invariants` failed because `validate_qt_provider.py` compared the documented status phrases case-sensitively (`provider`/`final`) while this document correctly used title-case headings (`Provider`/`Final`). This was a policy-validator defect, not a Qt-provider failure. Commit `284807f04a45a75a87e8cc65bdaf6a2bb4287a1a` corrected the validator by normalizing documentation text before status checks.

Correction verification:

- head: `89e12d0d1d6f92811d7d3da4e6ed4d4d1c2bcbcb`;
- Repository Policy **34688817960**: **PASS**, including `Validate Qt provider invariants` and the live Ubuntu Qt candidate check;
- Qt provider preflight **34688817853**: **PASS**;
- Qt evidence artifact: **10296212097**;
- Qt artifact SHA-256: `8b0faa9c375641a535d6e8790e0330ec0a27b5f9638dc3ca642df4c75932e271`;
- package preflight **34688817841**: **PASS** with `sbuild` and artifact upload intentionally skipped because the event delta did not affect package-proof inputs.

This closes the documentation-validator defect without changing the Qt technical conclusion: provider preflight is PASS; final Qt provider certification is still pending KDE DAG/runtime/compatibility evidence.

## Baseline closure proven

The initial provider preflight targets the Qt closure needed as a baseline for Plasma/Frameworks packaging, not every optional module that may later be required by individual KDE Gear applications.

Packages under the baseline gate:

- `qt6-base-dev`, `qt6-base-private-dev`;
- `qt6-declarative-dev`, `qt6-declarative-private-dev`;
- `qt6-svg-dev`;
- `qt6-wayland-dev`, `qt6-wayland-private-dev`;
- `qt6-shadertools-dev`;
- `qt6-tools-dev`, `qt6-tools-dev-tools`;
- `qt6-5compat-dev`.

The first PASS proved all baseline packages install from Resolute and normalize to upstream `6.10.2`. The hardened preflight additionally requires each installed Debian package version to equal the current APT candidate, preventing stale locally installed Qt packages from satisfying the gate. Run `34666082893` proved that stricter condition in CI.

## CMake and runtime surface proven

The PASS resolved public targets for:

- Core, Gui, Widgets, DBus, Network, Concurrent;
- Qml, Quick, QuickControls2;
- Svg, ShaderTools, Core5Compat;
- WaylandClient.

It also resolved the private targets:

- `Qt6::GuiPrivate`;
- `Qt6::QmlPrivate`;
- `Qt6::QuickPrivate`;
- `Qt6::WaylandClientPrivate`.

CMake emitted the expected Qt warning for private modules: consumers of private headers are tied to the specific Qt module build version. This is material evidence, not noise. SupraLINUX therefore treats the exact upstream patch level as part of the private-API build contract and rejects a mixed baseline such as Base 6.10.2 plus Declarative 6.10.3.

The compiled probe linked the public/private closure and executed with:

```text
qt_runtime_version=6.10.2
qml_engine=PASS
svg_module=PASS
core5compat=PASS
```

## Claim boundary

The hosted result is explicitly `ubuntu-qt-provider-preflight-only` and is non-authoritative for final KDE compatibility.

Provider preflight PASS establishes:

1. KDE-selected Qt series 6.10 is available from Ubuntu 26.04;
2. the declared baseline packages are coherent at upstream 6.10.2;
3. public and selected private CMake targets required for early Plasma/Frameworks packaging are discoverable;
4. a representative C++/QML/SVG/Core5Compat program builds and runs against that provider.

It does not establish that every Framework, Plasma component, KWin consumer or Gear application builds and runs correctly.

## Why Gear is not predeclared here

KDE Gear is a collection of applications with a wider and package-specific Qt dependency surface. SupraLINUX will extend the Qt module closure from the actual upstream dependency DAG for each selected application. Optional modules such as Multimedia, WebSockets, WebEngine, Positioning or Speech are added only when upstream KDE packages require them.

This preserves the project rule: **KDE decides what KDE needs**; Ubuntu does not define the desktop dependency set.

## Final certification requirements

Ubuntu Qt may move from `reuse-candidate` with final certification `pending` to certified only after evidence establishes at minimum:

1. provider preflight PASS on current Ubuntu 26.04 — **PASS**;
2. selected KDE Frameworks sources configure and build against that provider — **pending**;
3. selected Plasma/KWin sources configure and build against that provider — **pending**;
4. private-API consumers required by the selected KDE stack build successfully — **pending beyond the synthetic baseline probe**;
5. Debian package metadata/ABI contracts remain compatible with the SupraLINUX/Ubuntu package model — **pending**;
6. KDE runtime/session smoke tests pass — **pending**;
7. compatibility tests for relevant Ubuntu and third-party Qt applications pass — **pending**;
8. real evidence is recorded in manifests/status documentation — **ongoing**.

Until those stronger gates pass, `qt.certification.status` remains `pending` and Ubuntu remains a `reuse-candidate`, not a certified Qt provider.
