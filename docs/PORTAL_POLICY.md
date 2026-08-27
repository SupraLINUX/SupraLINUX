# Aurora XDG Portal Policy

Status: **candidate routing policy selected; C4.6/C4.7 runtime certification pending**.

Aurora currently installs both:

- `xdg-desktop-portal-kde`
- `xdg-desktop-portal-gtk`

This does **not** mean SupraLINUX mixes KDE and GNOME desktop shells. XDG Desktop Portal is a broker and multiple backend implementations may coexist. Runtime routing determines which backend serves each interface.

## Intended routing

For Plasma, the KDE backend is primary. It should own Plasma-native user-facing paths such as file selection and Wayland screen/screencast integration wherever KDE implements them.

The GTK backend is currently installed as a compatibility/fallback candidate for interfaces/settings where the effective Plasma portal configuration deliberately falls back to GTK.

Aurora must never rely on package installation order to select a portal backend.

## Why the GTK backend is currently in the candidate baseline

The package was promoted into the broad development candidate because Plasma portal routing may use a fallback backend for selected interfaces/settings and because GTK/Flatpak applications must behave coherently in the Plasma session.

This remains a **candidate dependency**, not a frozen requirement.

C4.6 is explicitly responsible for answering two questions with runtime evidence:

1. Does Aurora's actual Ubuntu 26.04 Plasma routing require the GTK backend for a compatibility path we intend to support?
2. If installed, does GTK remain confined to justified fallback interfaces rather than stealing Plasma/KDE-specific ones?

If the answer to the first question is no, the GTK backend should be considered for removal after C4 evidence. If yes, its exact routing becomes part of the product contract.

## C4.6 acceptance tests

Before the dependency is release-frozen:

1. confirm `XDG_CURRENT_DESKTOP` identifies Plasma correctly;
2. inventory installed portal backend descriptors/configuration;
3. record the effective portal routing used by current Ubuntu 26.04 packages;
4. activate relevant portal interfaces and record the serving backend where observable;
5. use a locally built Flatpak test application rather than relying on Flathub availability;
6. verify a sandboxed Qt/representative app receives the intended KDE file chooser path;
7. verify a representative GTK/sandbox path receives correct compatibility settings where GTK fallback is actually used;
8. verify GTK does not unexpectedly own KDE-specific screen-cast or chooser interfaces;
9. verify Flatpak permission changes actually alter sandbox behavior;
10. restore all test state and leave portal services healthy.

A portal process merely running or owning a D-Bus name is not sufficient.

## C4.7 screen-sharing acceptance

Screen capture/sharing is separated from generic portal routing because it involves KWin, PipeWire, portal session lifecycle and an external/representative client.

The test must exercise the real Wayland path and prove:

- session creation;
- source selection;
- stream start;
- real PipeWire frame flow;
- clean session close;
- recording/share indicator cleanup;
- no leaked PipeWire/portal session resources;
- stable Plasma/KWin after completion.

`docs/UPSTREAM_BLOCKERS.md` tracks an external Ubuntu 26.04 regression candidate involving repeated screen-sharing cycles. Therefore a one-shot success is insufficient. The current acceptance contract requires at least 30 consecutive start/share/stop cycles for each selected representative client path where practical.

## Failure policy

If C4 reproduces a portal/screen-sharing defect:

1. capture package versions and effective routing first;
2. identify whether the fault belongs to `xdg-desktop-portal`, KDE backend, GTK fallback, KWin, PipeWire or the client interaction;
3. check current Ubuntu/upstream fixes;
4. prefer an upstream/Ubuntu fix;
5. only then consider a scoped SupraLINUX override with documented removal condition.

Do not remove GTK, downgrade portals or pin versions merely to make C4 green before the failing component is isolated.
