# KDE Frameworks Tier 2 dependency map

Status: **discovery complete**  
Series: **6.30.0**

## Retained local predecessors

- ECM `6.30.0-0supralinux3`: PASS.
- KCoreAddons `6.30.0-0supralinux4`: PASS, artifact `10457958023`.
- KWindowSystem `6.30.0-0supralinux4`: PASS, artifact `10428130399`.
- KCodecs `6.30.0-0supralinux4`: PASS, artifact `10305050385`.

## KAuth

Build profile:
`ECM -> KCoreAddons + KWindowSystem + Qt Gui/DBus + PolkitQt6-1 -> KAuth`.

KCoreAddons is always required. KWindowSystem is required by the selected Linux Polkit backend. Resolute's `libpolkit-qt6-1-dev 0.200.0-4ubuntu1` satisfies upstream's minimum 0.112.0. Falling back to Fake merely because a provider was omitted would violate the upstream-selected behavior and SupraLINUX policy.

## KMime

Build profile:
`ECM -> KCodecs + Qt Core -> KMime`.

KCodecs is a required build dependency. In the Frameworks 6.30 shared target it is private, while Qt Core is public. The build dependency itself is not the blocker; ADR-0002 tracks the package/runtime compatibility transition.

## KAuth Batch 1 materialized edge

The KAuth runner downloads retained artifacts directly from their PASS runs:

- ECM artifact `10298635300`;
- KCoreAddons artifact `10457958023`;
- KWindowSystem artifact `10428130399`.

Their recorded package hashes are verified before they are passed to `sbuild --extra-package`. The KAuth `.buildinfo` must then prove that `extra-cmake-modules 6.30.0-0supralinux3`, `libkf6coreaddons-dev 6.30.0-0supralinux4` and `libkf6windowsystem-dev 6.30.0-0supralinux4` actually participated in the build.

## KAuth retained PASS edge

KAuth `6.30.0-0supralinux3` is retained PASS/downstream-eligible from run `35497461178`, job `106043001431`, artifact `10601382235`. The buildinfo proves the selected SupraLINUX ECM, KCoreAddons and KWindowSystem revisions participated in the clean build. Later nodes may consume this artifact; KMime does not depend on KAuth.
