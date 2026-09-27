# ADR-0001: Separate component authority from package provider

Status: **accepted**  
Date: **2026-09-11**  
Amended by: **ADR-0003 (2026-09-27)**

## Context

SupraLINUX needs Ubuntu compatibility and platform stability without allowing Ubuntu's desktop package cadence to determine the KDE desktop release. The same tension applies to Qt: Ubuntu may have a suitable Qt build, but package availability must not become the rule that selects KDE.

## Decision

SupraLINUX separates **authority** from **provider**.

- Ubuntu is authoritative for the platform areas assigned to Ubuntu.
- KDE upstream is authoritative for the KDE desktop stack and its dependency requirements.
- The Qt Project is authoritative for Qt itself, while KDE's release dependency profile determines the Qt version line required by the selected KDE stable stack.
- Ubuntu may be the package provider for Qt when its packages satisfy the selected profile and certification gates.
- If Ubuntu cannot satisfy that profile, SupraLINUX may become the provider only when the substitution passes the Ubuntu application-compatibility contract. Otherwise the selected KDE integration frontier remains at the newest compatible stable release.

For KDE components owned by SupraLINUX, Ubuntu's package version is never used as the selection authority or upper bound. SupraLINUX selects the newest official stable KDE stack that can be integrated completely while satisfying the Ubuntu application-compatibility contract. See ADR-0003.

## Consequences

Positive consequences:

- KDE can advance independently of Ubuntu's desktop cadence;
- Ubuntu compatibility remains an explicit engineering target;
- reusing Ubuntu packages remains possible when technically correct;
- provider substitutions become reviewable decisions rather than implicit inheritance.

Costs and risks:

- SupraLINUX may need to maintain a large Qt/KDE package set;
- ABI and Debian-package compatibility testing becomes mandatory when replacing shared libraries;
- security maintenance responsibility expands for components provided by SupraLINUX;
- dependency metadata and promotion gates must be maintained rigorously.

## Rejected alternatives

- Pin KDE to the versions shipped by Ubuntu 26.04.
- Start from Ubuntu Desktop or Kubuntu and upgrade the desktop opportunistically.
- Follow the newest Qt release independently of KDE requirements.
- Adopt an immutable image architecture to avoid package compatibility work.
