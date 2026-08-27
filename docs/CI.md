# SupraLINUX CI — Aurora validation

SupraLINUX CI validates packaging, clean-system composition and real VM boot behavior against Ubuntu 26.04 LTS, the base generation used by Aurora.

## Runner

The workflows use GitHub's `ubuntu-26.04` x64 runner. As of August 2026 this runner image is still in public preview, so each workflow explicitly verifies `VERSION_CODENAME=resolute` and amd64 before doing project work.

The source repository is public pre-alpha development. Public repository visibility does not imply release readiness and there is no supported ISO/release yet.

## Gate 1 — package build and APT resolution

Workflow: `.github/workflows/package-validation.yml`

It proves:

1. the development package sources build into DEB packages on Ubuntu 26.04;
2. the runner is actually amd64 Resolute;
3. `supralinux-snap-policy`, `supralinux-base`, `supralinux-settings` and `supralinux-desktop` resolve together through APT;
4. the SupraLINUX Snap policy removes installable APT candidates for `snapd` and `plasma-discover-backend-snap` in a fresh APT state;
5. the default package composition does not pull `plasma-session-x11`;
6. Plasma Discover resolves under the policy without pulling the Snap backend.

## Gate 2 — clean rootfs installation

Workflow: `.github/workflows/rootfs-validation.yml`

This gate builds a disposable Ubuntu 26.04 `debootstrap --variant=minbase` rootfs, enables the official Ubuntu main/restricted/universe/multiverse repositories, then installs the SupraLINUX DEBs for real inside that isolated filesystem.

The Snap policy is installed first. The base, settings and desktop packages are then installed using normal APT behavior. The gate runs `apt-get check` and verifies representative required integrations including Plasma Wayland, XWayland compatibility, SDDM, KWin Wayland, Polkit, PipeWire, NetworkManager, Bluetooth, KDE portals, Flatpak integration, KRDP, printing, Samba sharing, KWallet, power management and display management.

The rootfs gate also verifies Aurora's SDDM Wayland configuration from `supralinux-settings`: `DisplayServer=wayland` and a KWin Wayland compositor command must be present. It rejects `plasma-session-x11` and its standard launcher files from the default baseline.

It additionally fails if it finds Snap components, Ubuntu Desktop, Kubuntu Desktop or GNOME Shell, and verifies the SupraLINUX APT preference that keeps Snap non-installable by default.

## Gate 3 — C1 kernel + systemd boot

Workflow: `.github/workflows/boot-c1-validation.yml`

C1 converts the clean Aurora composition into a disposable ext4 VM disk, boots the actual Ubuntu kernel/initramfs in QEMU and requires the guest to reach a healthy `multi-user.target` state.

The guest must emit exactly one `AURORA_C1_SUCCESS` marker and no `AURORA_C1_FAILURE` marker. C1 checks PID 1/systemd, writable root, package consistency, SupraLINUX package presence, Snap policy and the configured SDDM display-manager link.

## Gate 4 — C2 graphical target + SDDM Wayland greeter

Workflow: `.github/workflows/boot-c2-validation.yml`

C2 boots the same package-defined Aurora system to `graphical.target` with a virtual DRM device. It does not accept a merely installed or enabled SDDM service.

The guest requires:

- `graphical.target` and `multi-user.target` active;
- SDDM and systemd-logind healthy;
- a graphical `seat0` and `/dev/dri/card0`;
- Aurora's `DisplayServer=wayland` SDDM configuration;
- `kwin_wayland` running for the SDDM user;
- `sddm-greeter` running for the SDDM user;
- `xwayland` installed for application compatibility;
- no default Plasma X11 desktop session;
- package and Snap-policy sanity after graphical boot.

The guest must emit exactly one `AURORA_C2_SUCCESS` and no `AURORA_C2_FAILURE` marker. Serial logs and installation diagnostics are uploaded as evidence.

C2 validates the display-manager greeter only. It does **not** prove that a normal user can log into a Plasma Wayland desktop; that is C3.

## Next gate — C3 Plasma Wayland user session

C3 must create a disposable CI-only user and prove a real Plasma session, including `XDG_SESSION_TYPE=wayland`, KWin Wayland, Plasma shell, user D-Bus, portals, PipeWire, Polkit/KWallet integration and lack of an immediate crash loop.

Because Aurora prioritizes a complete desktop rather than protocol purity, C3 must also perform an XWayland compatibility smoke test by launching a small disposable X11 client inside the Wayland session. XWayland support is part of the intended user experience; it is not an alternative Plasma X11 desktop session.

## Storage policy

Large VM/rootfs images remain ephemeral and out of Git. Boot-validation workflows preserve compact serial and targeted diagnostic artifacts so accepted runtime milestones can be audited.

Persistent release packages belong in the future SupraLINUX APT repository rather than GitHub Actions artifact storage.
