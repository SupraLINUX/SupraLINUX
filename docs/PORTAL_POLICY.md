# Aurora XDG Portal Policy

Status: **candidate integration policy; clean Plasma Wayland validation pending**.

Aurora currently installs both:

- `xdg-desktop-portal-kde`
- `xdg-desktop-portal-gtk`

This does **not** mean SupraLINUX is mixing KDE and GNOME desktop shells. XDG Desktop Portal is a broker: multiple backend implementations can coexist and the desktop selects which implementation handles each portal interface.

## Intended routing

For Plasma, the KDE backend is the primary implementation. It should own the Plasma-native user-facing paths such as file selection and screen/screencast integration wherever KDE implements them.

The GTK backend is installed as a compatibility/fallback implementation, particularly for portal interfaces/settings where the Plasma portal configuration may deliberately fall back to GTK.

Aurora must not rely on package installation order to choose a backend.

## Why the GTK backend is in the candidate baseline

Ubuntu 26.04's Kubuntu desktop installs both the KDE and GTK portal backends as hard dependencies. More importantly, Plasma's portal-routing design has used the GTK backend as a fallback for selected interfaces such as desktop Settings. This can matter for GTK applications running inside a Plasma session (theme/font/settings coherence).

SupraLINUX therefore treats `xdg-desktop-portal-gtk` as an integration candidate with a concrete reason, not as something copied blindly from Kubuntu.

## Acceptance tests

Before the dependency is release-frozen:

1. confirm `XDG_CURRENT_DESKTOP` identifies Plasma correctly;
2. inspect the effective Plasma portal routing configuration installed by current Ubuntu 26.04 KDE packages;
3. verify a Flatpak/Qt app opens the KDE file chooser;
4. verify a representative GTK/Flatpak app gets correct fonts/theme/settings;
5. verify screen sharing routes through the KDE/KWin/PipeWire path;
6. verify installing the GTK backend does not steal KDE-specific interfaces unexpectedly;
7. repeat screen-sharing start/stop cycles according to `docs/UPSTREAM_BLOCKERS.md` because Ubuntu 26.04 currently has an external regression report in this area.

If the GTK backend provides no required compatibility in the tested Aurora environment, it can be removed. If it is required, the routing behavior becomes part of the release contract.
