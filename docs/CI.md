# SupraLINUX CI — Aurora validation

SupraLINUX CI validates packaging and installation against the same Ubuntu generation used by Aurora.

## Runner

The workflows use GitHub's `ubuntu-26.04` x64 runner. As of August 2026 this runner image is still in public preview, so each workflow explicitly verifies `VERSION_CODENAME=resolute` and amd64 before doing project work.

The source repository is public pre-alpha development. Public repository visibility does not imply release readiness and there is no supported ISO/release yet.

## Gate 1 — package build and APT resolution

Workflow: `.github/workflows/package-validation.yml`

It runs:

- manually through `workflow_dispatch`;
- on relevant pushes to `development`; and
- on pull requests targeting `main` when packaging/CI files change.

It proves:

1. the package sources build into DEB packages on Ubuntu 26.04;
2. the runner is actually amd64 Resolute;
3. `supralinux-snap-policy`, `supralinux-base` and `supralinux-desktop` resolve through APT without unresolved dependency names;
4. the SupraLINUX Snap policy removes installable APT candidates for `snapd` and `plasma-discover-backend-snap` in a fresh APT state;
5. Plasma Discover can resolve under the policy without pulling the Snap backend.

## Gate 2 — clean rootfs installation

Workflow: `.github/workflows/rootfs-validation.yml`

This gate goes beyond resolver simulation. It builds a disposable Ubuntu 26.04 `debootstrap --variant=minbase` rootfs, enables the official Ubuntu main/restricted/universe/multiverse repositories, then installs the SupraLINUX DEBs for real inside that isolated filesystem.

The Snap policy is installed first, then `supralinux-base` and `supralinux-desktop` are installed using normal APT behavior. The gate then runs `apt-get check` and verifies a representative set of required packages including Plasma Wayland, SDDM, Polkit, PipeWire, NetworkManager, Bluetooth, KDE portal integration, Flatpak integration, KRDP, printing, Samba sharing, KWallet, power management and display management.

The rootfs gate also fails if it finds `snapd`, Plasma Discover's Snap backend, Ubuntu Desktop, Kubuntu Desktop or GNOME Shell. It checks that the SupraLINUX APT preference file exists in the installed rootfs and that Snap remains non-installable afterward.

## What these gates still do NOT prove

Neither gate is a graphical desktop test. They do not yet prove:

- the rootfs boots;
- SDDM reaches a graphical greeter;
- a Plasma Wayland session starts;
- audio/network/Bluetooth hardware actually works;
- KRDP establishes a working session;
- portals and screen sharing function end-to-end;
- locale/XDG first-login behavior is correct;
- suspend/resume works;
- hardware-specific integrations work.

Those require the next VM/boot/session validation layer.

## Storage policy

Routine validation does not upload GitHub Actions artifacts. DEBs and rootfs data exist only inside the ephemeral runner for the duration of each job.

Persistent test/release packages belong in the future SupraLINUX APT repository rather than GitHub Actions artifact storage.
