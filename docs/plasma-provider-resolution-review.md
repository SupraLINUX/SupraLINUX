# Plasma 6.7.5 provider-resolution review

Status at definition time: **review pending CI**.

This gate consumes the closed provider-resolution evidence from run `37086119189`, job `111096931279`, artifact `11260780398`. It is planning-only: no package execution starts, no package Attempt is consumed, and Level 0 remains locked.

## Review decisions

- The five missing same-name Ubuntu Resolute source references are not package failures.
  - `spectacle` maps to Ubuntu source `kde-spectacle`; Resolute Updates is the base packaging reference and KDE 6.7.5 remains authoritative.
  - `plasma-bigscreen` uses Ubuntu Stonking only as a technical packaging reference for the same upstream series; binaries/providers must still resolve against Resolute/SupraLINUX.
  - `union` uses Ubuntu Stonking 6.7.4 packaging as a near-upstream technical reference; upstream 6.7.5 remains authoritative.
  - `plasma-login-manager` uses Debian sid 6.7.4 packaging as a near-upstream technical reference and KDE 6.7.5 as source authority.
  - `plasma-setup` has no matching Resolute source reference; its contract is derived from KDE 6.7.5 upstream and already-certified SupraLINUX/Resolute provider decisions.
- The seven missing `debhelper-compat` / `dh-sequence-*` names are compatibility relations or virtual dh sequences. They are resolved through `debhelper`, `pkg-kde-tools`, or `dh-python`; they are not missing package providers.
- Ten pending KDE QML modules are supplied by already-PASS SupraLINUX Frameworks 6.30 artifacts.
- `org.kde.kirigamiaddons.formcard` is provided by Ubuntu Resolute `qml6-module-org-kde-kirigamiaddons-formcard` 1.11.0-2ubuntu2.
- `org.kde.kquickimageeditor` is provided by Ubuntu Resolute `qml6-module-org-kde-kquickimageeditor` 0.6.0-2build1.
- The 117 CMake `source-build-dep-reference` entries are reviewed by per-node source Build-Depends context. Every referring node must have either a Resolute source reference or one of the five explicit source-reference decisions above.
- The 11 Qt5/KF5 CMake references are intentional compatibility paths limited to Breeze, KWayland Integration, Oxygen, and Plasma Integration. They use Ubuntu Resolute compatibility providers and must not replace or downgrade the primary Qt6/KF6 stack.
- `${GENMODULE}` is an ECM-generated QML finder probe, not an external build provider.
- `KF${QT_MAJOR_VERSION}KirigamiAddons` resolves to the Qt6 Kirigami Addons provider from Ubuntu Resolute.

## External technical references

- https://packages.ubuntu.com/source/resolute-updates/kde-spectacle
- https://packages.ubuntu.com/source/stonking/plasma-bigscreen
- https://packages.ubuntu.com/source/stonking/union
- https://packages.debian.org/sid/plasma-login-manager
- https://packages.ubuntu.com/resolute/kirigami-addons-dev
- https://packages.ubuntu.com/resolute/kquickimageeditor-dev

Passing this review only authorizes promotion of the candidate dependency graph to an executable DAG definition. It does **not** authorize Plasma Level 0 package execution.
