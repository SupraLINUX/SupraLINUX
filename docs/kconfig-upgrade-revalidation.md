# KConfig Ubuntu upgrade repair

Plasma Activities Attempt 1 exposed an installation failure in the retained
KConfig `6.30.0-0supralinux4` packages. Ubuntu `6.24.0-0ubuntu1` owns
`libexec/kf6/kconf_update` in `libkf6config-bin`; the retained SupraLINUX build
moved it to `libkf6configcore6` without a Breaks/Replaces boundary covering that
Ubuntu version. dpkg correctly refused the file collision. Activities compiled,
but its candidate clients never ran; its original FAIL remains retained.

The packaging-only `6.30.0-0supralinux5` revision restores Ubuntu's binary package
ownership and declares versioned Breaks/Replaces against the old SupraLINUX core
owner. The official KDE source, Qt provider, ABI symbol floors and feature
defaults are unchanged. The original Frameworks campaign and its milestone
remain historical evidence for their original inputs.

The repair passed the authoritative KVM lane: a bare sbuild environment, all 90
required upstream tests, source/binary lintian, the unchanged Ubuntu SDK client
after upgrade, a client rebuilt with the candidate SDK, and an upgrade from the
retained SupraLINUX packages. The client exercises persisted/default values,
GUI shortcuts, the QML property map and actual installed QML plugin. The real
configuration updater must migrate a value, preserve an unrelated value and
execute a completed migration exactly once. Candidate upgrades use normal APT
resolution; no forced overwrite is permitted.

`manifests/package-revalidation.json` is the live repair authority. Its evidence
links bind the original Actions archive, job and source commit to the sealed
host run, verified source/binary closure and offline restoration. Full archives
are retained under `.artifacts/package-revalidation` independently of Actions
expiry. Small infrastructure preflights and their incidents consumed no package
Attempts; the repair's first package Attempt passed.

New Plasma consumers resolve the repaired version through
`scripts/frameworks-revalidation-inputs.py`. Cache admission still verifies every
binary and metadata file in the historical milestone; it then adds only the
exact binaries from the repair's verified PASS archive. The old package pool is
preserved, and the superseded version cannot feed a new build. Closed Plasma
results continue to validate their original frozen predecessor versions.

Before rebuilding Activities, a separate infrastructure preflight must restore
the repaired inputs and install every selected predecessor at its reviewed
version in clean sbuild. This certifies the new transport route without using
Activities as its first test. Product-wide Ubuntu compatibility, the final clean
rebuild and actual Plasma session acceptance remain release gates.
