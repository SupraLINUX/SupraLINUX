# ADR-0003: KDE integration frontier and Ubuntu application compatibility

Status: **accepted**  
Date: **2026-09-27**

## Context

SupraLINUX exists to provide a complete, well-integrated KDE desktop on an Ubuntu 26.04 LTS platform without inheriting Ubuntu's KDE package cadence. The original architecture correctly separated authority from provider, but the rule "always adopt the newest KDE stable and provide Qt ourselves if Ubuntu is behind" can create a conflict with the Ubuntu application-compatibility goal when a newer KDE release requires a broad platform transition.

The concrete upstream boundary is visible in KDE's current Plasma schedule: Plasma 6.7 uses Qt 6.10, while Plasma 6.8 is assigned Qt 6.11. As of this decision date Plasma 6.8 is still beta, so it is not eligible for canonical selection anyway. Qt's compatibility policy aims to preserve backward binary compatibility within Qt 6 under matching toolchain, system and build-configuration conditions, but that is not a substitute for distribution-level validation of plugins, private APIs, package metadata and third-party consumers.

Authoritative references:

- KDE Plasma release/dependency schedule: <https://community.kde.org/Schedules/Plasma_6>
- KDE Plasma announcements: <https://kde.org/announcements/>
- Qt compatibility commitments: <https://doc.qt.io/qt-6/qt-releases.html>

## Decision

SupraLINUX defines a **KDE integration frontier**.

The selection rule is:

> **Select the newest official stable KDE stack that SupraLINUX can package completely while preserving the Ubuntu application-compatibility contract.**

This means:

- **KDE upstream remains the desktop authority.** KDE determines component relationships, supported behavior and the Qt/dependency requirements of each release.
- **SupraLINUX is the selection and packaging authority.** Ubuntu does not select Plasma, Frameworks, Gear, KWin, Breeze or the KDE application set.
- **Ubuntu KDE package versions are not an upper bound.** SupraLINUX continues to package its own KDE stack and may remain substantially newer than Ubuntu's desktop packages.
- **Ubuntu application compatibility is a hard integration gate.** A newer KDE release is not adopted merely because it exists if its required Qt or other platform transition cannot yet be compatibility-certified.
- **Providing Qt ourselves is conditional, not automatic.** SupraLINUX may replace Ubuntu Qt only with build/runtime/package/application evidence sufficient for the compatibility contract. If that gate cannot pass, the KDE frontier remains at the newest compatible stable release.
- **No beta/RC becomes canonical by default.** Pre-releases are test inputs only unless explicitly approved.
- **The selected KDE profile should be feature-complete by default.** Upstream-advertised desktop features selected for the product should not require users to discover missing integration packages after installation. Dependencies needed for those features are packaged/installed by default unless a documented exception is justified by security, legal restrictions, hardware-specific scope, an external service, or disproportionate footprint.

## Internal development heuristic

"**Stay ahead of Ubuntu where compatible**" is an internal engineering heuristic, not a public marketing claim and not a numeric version rule.

SupraLINUX should describe itself by its architecture and capabilities. It does not need to advertise itself as better, newer or superior to Ubuntu, Kubuntu, KDE neon or any other distribution.

## Selection procedure

For each candidate KDE stable transition:

1. verify the release and dependency profile from official KDE upstream sources;
2. construct the KDE/Qt/dependency DAG for the candidate;
3. determine whether Ubuntu can provide each broad platform dependency without changing authority;
4. where SupraLINUX must substitute Qt or another broadly consumed library, validate package metadata, ABI/private-API consumers, representative Ubuntu applications and relevant third-party applications;
5. require the normal SupraLINUX build/runtime/authoritative gates;
6. select the candidate only after the compatibility contract passes;
7. otherwise retain the current newest compatible stable KDE release and continue investigating the next frontier.

A compatibility hold is therefore a SupraLINUX engineering decision, not Ubuntu choosing the desktop version.

## Current implication

As of 2026-09-27 the canonical stack remains Plasma 6.7.5 / Frameworks 6.30.0 / Gear 26.08.1 with Qt 6.10 as the selected Qt line. Plasma 6.8 remains beta and is not canonical. After Plasma 6.8 becomes stable, its Qt 6.11 requirement becomes an integration-frontier candidate that must pass this policy before selection.

This ADR changes the **future selection rule**. It does not invalidate existing build evidence, change the current Tier 3/KIO lifecycle, authorize Attempt 9, or promote any package.

## Consequences

Positive:

- Ubuntu does not regain authority over the desktop;
- SupraLINUX can keep KDE materially newer and more complete than Ubuntu's KDE packaging when compatible;
- Ubuntu application compatibility becomes a clear architectural contract instead of a best-effort afterthought;
- Qt replacement risk is bounded by evidence rather than ideology;
- future KDE upgrades become explicit integration decisions rather than automatic version chasing.

Costs:

- a newly released KDE stable may be held temporarily at the compatibility frontier;
- compatibility testing must include representative Ubuntu and third-party applications when broad libraries change;
- SupraLINUX must maintain its own KDE packaging and feature-completeness decisions even when Ubuntu ships different versions or splits optional functionality differently.

## Rejected alternatives

- Let Ubuntu/Kubuntu package versions select the KDE desktop.
- Always adopt the newest KDE stable even when doing so requires an uncertified broad Qt/platform replacement.
- Remove or disable upstream KDE features solely to force a newer version through the compatibility gate.
- Use "newer than Ubuntu" as product positioning rather than as an internal engineering heuristic.
