# KMime legacy compatibility-provider audit

Status: **PASS**

KMime from KDE Frameworks 6.30 remains the authoritative KDE implementation in SupraLINUX. Ubuntu Resolute's `kmime 25.12.3-0ubuntu1` is considered only as an on-demand compatibility provider for software that still requires the legacy `libKPim6Mime.so.6` ABI.

The second real KF6Mime build already established that the Frameworks package itself is healthy: clean `sbuild`, **17/17 upstream tests**, Lintian without errors, `libKF6Mime.so.6` ABI validation, APT runtime closure, external `KF6::Mime` consumer smoke and the no-fake-legacy-metadata gate all passed.

The remaining blocker was observed only when Ubuntu's stock `libkpim6mime6 + libkmime-data` were requested: APT removed `libkf6mime6`, `libkf6mime-dev` and `libkf6mime-data`. This audit determines why.

The audit is diagnostic and changes **no package state**. It consumes the real KF6Mime build artifact from run `35687831684`, artifact `10677716050`, and downloads the exact Resolute legacy binaries `25.12.3-0ubuntu1`. It records:

- exact binary package versions and SHA-256;
- `Depends`, `Pre-Depends`, `Provides`, `Conflicts`, `Breaks` and `Replaces`;
- pairwise payload overlap between Frameworks and legacy packages;
- SHA-256 comparison for every overlapping file;
- proof that `libKF6Mime.so.6` and `libKPim6Mime.so.6` remain distinct runtime namespaces;
- a non-destructive APT solver simulation.

A successful audit means the evidence was captured and classified. It does **not** mean stock Ubuntu packages are compatible, does not make KMime PASS, and does not authorize publication. The next implementation must be the smallest compatibility-provider adaptation supported by this evidence; KDE Frameworks remains authoritative.


## Audit PASS — 2026-09-22

Run `35690284355`, job `106625630885`, artifact `10678073973` completed the compatibility-provider audit. Artifact SHA-256: `7b0c9175b1e0f48eb1d18e9ceb1af03381c4de8d0b322bc619dd7be224307c5b`.

The failure is **not** a runtime ABI collision:

- `libkpim6mime6` has no `Breaks`, `Conflicts` or `Replaces` against KF6Mime.
- Its dependency is exactly `libkmime-data (= 25.12.3-0ubuntu1)` plus normal runtime libraries.
- `libKF6Mime.so.6` and `libKPim6Mime.so.6` remain distinct and non-overlapping runtime payloads.
- The package relation that forces the transition is on `libkf6mime-data`: `Breaks: libkmime-data` and `Replaces: libkmime-data`.

The only payload overlap is data-to-data: `libkf6mime-data` vs `libkmime-data`, 72 shared paths. 68 are byte-identical. The four differing paths are three translations (`lt`, `sk`, `ug`) and `/usr/share/qlogging-categories6/kmime.categories`.

### Selected remediation

Do not install or republish a second legacy data owner beside `libkf6mime-data`. Keep the authoritative Frameworks data package unchanged.

SupraLINUX will instead provide the real legacy runtime ABI as a separate compatibility package derived from the `kmime 25.12.3` compatibility source. Its runtime dependency will accept the authoritative Frameworks data package as an alternative:

`libkmime-data (= Ubuntu compatibility version) | libkf6mime-data`

This preserves `libKPim6Mime.so.6` for Ubuntu applications without pretending that KF6Mime implements that ABI and without duplicating the 72 shared data files.

At the time of this audit KMime remained canonical **pending** until that compatibility provider was built and the full co-installation/application gates passed.


## Compatibility-provider closure

The selected remediation was subsequently implemented and validated. Provider workflow `35691309612` built the real legacy ABI package `kmime 25.12.3-0ubuntu1+supralinux1` without emitting `libkmime-data`.

Final provider build job `106628834481`, artifact `10679420779`, SHA-256 `f77517f13eab6a282d6050cb738f78b233a9392c076a23d54131073468d2ad4b` passed clean sbuild, Lintian, co-installation, APT closure and both `KPim6::Mime` and `KF6::Mime` consumers.

The audit therefore remains PASS as diagnostic evidence, while the provider implementation closes the compatibility gate. No stock Ubuntu package is reclassified as compatible as packaged; the SupraLINUX compatibility provider is the tested bridge.
