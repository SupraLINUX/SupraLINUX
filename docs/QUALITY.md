# SupraLINUX Quality Contract

## Core rule

**If SupraLINUX exposes a feature in the shipped desktop, SupraLINUX is responsible for making it work end-to-end.**

A feature is not complete merely because its GUI package is installed.

## Integration checklist for each feature

- [ ] Frontend present
- [ ] Backend/service present
- [ ] Required runtime dependencies installed
- [ ] Required permissions/policy configured
- [ ] Correct Wayland/session integration
- [ ] Correct portals where applicable
- [ ] Correct systemd service/socket activation where applicable
- [ ] Correct locale/translations
- [ ] Correct default configuration
- [ ] Happy path tested
- [ ] Common failure path tested
- [ ] Upgrade path tested when state/configuration is persistent

## Baseline integration areas

The Phase 1 baseline must explicitly validate at least:

- Plasma session startup
- KWin Wayland
- SDDM
- Polkit
- NetworkManager
- Wi-Fi
- VPN UI/backend integration
- PipeWire audio
- Bluetooth
- printing
- removable devices
- KWallet
- XDG portals
- Flatpak permissions/configuration
- screen capture
- screen sharing
- remote desktop where shipped
- network shares/Samba
- archives and common formats
- language/locale support
- XDG user-directory localization
- power management
- suspend/resume
- multi-monitor behavior
- common file associations

## Localization quality

A clean installation is defective if the installer selects one language but the first session is left partially in another because SupraLINUX failed to initialize locale, translations, formats, or XDG user directories in the correct order.

For every officially supported installation language, test:

- installer language
- generated locale
- first-login `$LANG`
- Plasma translations
- Qt translations
- regional formats
- XDG user-directory names
- common application translations where part of the shipped baseline

## No repair-script dependency

The supported installation must not require users to run a post-install script to finish features SupraLINUX claims to include.

If the known fix is “install package X”, the normal solution is to make the responsible SupraLINUX package declare the correct dependency/recommendation and test it.

## Release gates

A release candidate must not be promoted to stable solely because it builds. Stable requires explicit review of the current test matrix and known issues.
