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

## Version-scoped certification

A PASS belongs to the exact software/runtime scope that produced its evidence. Replacing KDE Frameworks, Plasma, KWin, Qt or another component that can materially affect the tested path requires the applicable regression gates before the PASS can describe the new release candidate.

Historical evidence is preserved for comparison; it is never silently relabelled as evidence for a different stack.

A newer KDE release is not promoted because it builds or because its version number is newer. It must satisfy `docs/KDE_STACK_QUALIFICATION.md`, including reproducible source packaging, dependency closure, clean install, upgrade, rollback/recovery, boot/session regressions and fresh runtime-surface reconciliation before feature certification continues.

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

A distribution-owned compatibility launcher, override or patch is acceptable only when its underlying integration defect and maintenance/removal condition are documented and the resulting user path is tested. It must not be used to hide an unexplained failure.

## Release gates

A release candidate must not be promoted to stable solely because it builds. Stable requires explicit review of the current test matrix, package/source provenance, known issues, upgrade/rollback evidence and security-maintenance ownership for any SupraLINUX override.
