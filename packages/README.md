# SupraLINUX Packages

This directory will contain the Debian packaging owned by SupraLINUX.

Initial package plan:

```text
supralinux-base
supralinux-desktop
supralinux-settings
supralinux-release
supralinux-artwork
supralinux-default-apps
supralinux-flatpak
supralinux-installer
supralinux-welcome
supralinux-meta
```

## First implementation target

The first real package to design is `supralinux-desktop`, because it defines the complete vanilla Plasma integration baseline and its dependencies.

Before writing its final dependency list, the project must inventory Ubuntu 26.04 Plasma packages and map every shipped Plasma feature to its required backend/integration packages.

Do not create package dependencies by copying `kubuntu-desktop`. Kubuntu may be used as a reference for missing integration pieces, but SupraLINUX must justify its own desktop composition.
