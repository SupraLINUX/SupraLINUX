# Plasma Package Audit — Ubuntu 26.04 LTS

Status: **broad development candidate installed and boot/session validated; exact dependency set remains unfrozen pending C4 evidence**.

Purpose: determine the smallest complete package composition that gives SupraLINUX an upstream-like KDE Plasma desktop in which every shipped/exposed feature has its backend and integration present.

This is not a copy of `kubuntu-desktop`. Kubuntu remains a comparative reference for integrations that minimal Plasma packaging may omit, never an automatic dependency source.

The canonical runtime/executable feature status now lives in:

- `docs/PLASMA_INTEGRATION_MATRIX.md`
- `docs/C4_CERTIFICATION.md`

## 1. Current validation context

The historical “first clean Ubuntu 26.04 installation” is complete. The current broad candidate has already:

- built successfully as DEB packages;
- resolved through APT under the SupraLINUX Snap policy;
- installed in an isolated clean Resolute rootfs;
- booted through C1;
- reached a real SDDM/KWin Wayland greeter through C2;
- reached a stable real Plasma Wayland user session with XWayland compatibility through C3.

Those results prove composition/session viability. They do not prove feature completeness and therefore do not freeze the dependency set.

## 2. Current REQUIRED-candidate areas

The development `supralinux-desktop` intentionally remains broader than a minimal KDE installation so C4 can test the complete intended surface.

| Area | Current candidate package(s) | C4 owner / reason |
|---|---|---|
| Plasma shell/workspace | `plasma-desktop`, `plasma-workspace` | C3 prerequisite + C4.0/C4.1 surface inventory |
| Wayland session | `plasma-session-wayland` | C3 prerequisite |
| System Settings | `systemsettings` | C4.0/C4.1 |
| Qt/Plasma visual integration | `breeze`, `frameworkintegration6`, `plasma-integration` | baseline integration |
| GTK visual integration | `breeze-gtk-theme`, `kde-config-gtk-style` | C4.15 |
| Authentication UI | `polkit-kde-agent-1` | C4.2 real privileged action |
| Display manager/config | `sddm`, `sddm-theme-breeze`, `kde-config-sddm` | C2 prerequisite + C4.2 privileged config path |
| Storage/removable media | `udisks2` | C4.10 |
| Power | `upower`, `powerdevil`, `power-profiles-daemon` | C4.12 |
| Displays | `kscreen` | C4.1 virtual output + later HW |
| Screen locking | `kde-config-screenlocker` | C4.0/C4.1/session coverage |
| System information | `kinfocenter` | C4.15 |
| System monitoring | `ksystemstats` | C4.15 |
| Audio UI | `plasma-pa` | C4.4 |
| Audio stack | `pipewire-audio` | C4.4 |
| Bluetooth | `bluedevil`, `bluez` | C4.5 + later HW |
| Networking | `plasma-nm`, `network-manager` | C4.3 |
| Common VPN backends | `network-manager-openvpn`, `network-manager-openconnect` | C4.3 controlled tunnels |
| Mobile/radio integration | `modemmanager`, `rfkill` | C4.3/C4.15 justification |
| Platform sensors/GPU | `iio-sensor-proxy`, `switcheroo-control` | C4.12/C4.15 justification + HW |
| Portals | `xdg-desktop-portal`, `xdg-desktop-portal-kde`, `xdg-desktop-portal-gtk` | C4.6/C4.7 routing evidence |
| XDG user dirs | `xdg-user-dirs` | C4.13 |
| Keyboard data | `xkb-data` | C4.1 |
| Qt translations | `qt6-translations-l10n` | C4.13 |
| File/network abstraction | `kio6`, `kio-fuse`, `kio-extras` | C4.11 |
| KWallet login integration | `libpam-kwallet5` | C4.2 |
| Flatpak | `flatpak`, `kde-config-flatpak` | C4.6 |
| Remote Desktop server | `krdp` | C4.8 |
| Printing | `print-manager`, `cups`, `cups-client`, `cups-filters` | C4.9 |
| Network sharing | `kdenetwork-filesharing`, `samba` | C4.11 |
| Accessibility | `at-spi2-core`, `orca`, `speech-dispatcher` | C4.14 |
| SMART surface | `plasma-disks` | C4.10/C4.15 + HW |
| Virtual keyboard | `plasma-keyboard` | C4.1/C4.15 |
| Crash/credential UI helpers | `drkonqi`, `ksshaskpass`, `pinentry-qt` | C4.15 |

The table is a candidate audit, not proof that every entry must remain a hard dependency after C4.

## 3. KWin and Plasma KCM surface

The detailed package-derived KCM inventory remains in `docs/KCM_AUDIT.md`.

C4.0 now adds a stronger rule: the live guest must discover its actual installed KCM/KWin/integration surface and compare that result with a versioned coverage manifest. This protects Aurora from silently gaining an untested user-visible feature after an Ubuntu/KDE update.

Static package research is therefore an input, not the final source of truth for coverage.

## 4. Feature-completeness decisions currently promoted into the candidate

### Flatpak

Current candidate:

- `flatpak`
- `kde-config-flatpak`

Reason: Flatpak is a first-class SupraLINUX application layer. C4.6 must prove actual sandbox/permission behavior before the hard dependency classification is frozen.

### Remote Desktop

Current hard candidate:

- `krdp`

`krdc` remains `Recommends` and must not be automatically treated as a certified baseline application. C4.8 decides whether the client remains optional or is promoted later.

### Printing

Current candidate:

- `print-manager`
- `cups`
- `cups-client`
- `cups-filters`

C4.9 must exercise a real controlled IPP job lifecycle, not only package/service presence.

### Network sharing

Current candidate:

- `kdenetwork-filesharing`
- `samba`
- `kio-extras`
- `kio-fuse`

C4.11 verifies both remote SMB consumption and local share creation/access. `samba` remains explicit until evidence proves a better split.

### VPN

Current candidate:

- `network-manager-openvpn`
- `network-manager-openconnect`

C4.3 must establish real controlled tunnels and traffic. Other protocols remain unclaimed unless deliberately selected.

### Accessibility

Current candidate:

- `at-spi2-core`
- `orca`
- `speech-dispatcher`

C4.14 determines whether the current composition provides a genuinely usable assistive path or whether an additional provider/runtime is needed.

### SMART disk health

Current candidate:

- `plasma-disks`

C4 can validate package/surface integration, but a meaningful physical SMART claim remains hardware-scoped. C4.15 may demote it if the dependency is inappropriate for the base image.

### GTK application coherence

Current candidate:

- `breeze-gtk-theme`
- `kde-config-gtk-style`

C4.15 must prove the supported configuration path rather than assuming installation equals coherence.

## 5. Discover / PackageKit / Snap interaction — resolver issue CLOSED, product decision OPEN

The previous package-audit blocker was that Ubuntu's `plasma-discover` recommends `plasma-discover-backend-snap` and APT normally installs recommendations.

That resolver risk is no longer an implementation blocker: the shipped `supralinux-snap-policy` has been implemented and CI verifies that Discover resolves under the policy without pulling either the Snap backend or `snapd`.

This does **not** promote Discover into the hard `supralinux-desktop` dependency set.

Current decision:

- Snap resolver policy: implemented/validated;
- Discover baseline role: still a later product/software-management decision;
- no Snap backend in Aurora's default policy state.

## 6. Portal backend question — CANDIDATE ROUTING TO BE CERTIFIED IN C4.6

The current `supralinux-desktop` installs both:

- `xdg-desktop-portal-kde`;
- `xdg-desktop-portal-gtk`.

This is now an explicit candidate policy, not an unresolved package-presence question. `docs/PORTAL_POLICY.md` defines KDE as primary and GTK as compatibility fallback candidate.

C4.6 must record effective routing and determine from runtime evidence whether the GTK backend is required and whether it stays out of KDE-specific interfaces.

Only after C4.6 may the GTK backend be kept or removed from the final candidate.

## 7. Deliberately unresolved capabilities

These remain outside the hard candidate until policy/testing is adequate:

| Capability | Package(s) | Reason not yet hard baseline |
|---|---|---|
| Firewall KCM | `plasma-firewall` + backend | No selected/supported firewall policy |
| Thunderbolt | `plasma-thunderbolt` + backend | Physical authorization testing required |
| Plasma Vaults | `plasma-vault` + crypto backends | Complete lifecycle/recovery design required |
| Fingerprint | `libpam-fprintd` / `fprintd` | Auth-stack + hardware validation required |
| KDE Connect | `kdeconnect` | Deliberate app/product decision |
| Browser integration | `plasma-browser-integration` | Wait for browser/default-app policy |
| Scanner workflow | scanner app/backend stack | No scanner UI/app currently exposed by baseline |
| Archive/RAR workflow | Ark/backend choices | Phase 5 capability unless C4.0 discovers a current exposed surface |
| Firmware UI | `fwupd` + UI | Coupled to store/updater product decision |

## 8. Explicit non-inheritance from Kubuntu

The following remain NOT automatically inherited:

- `kubuntu-settings-desktop`;
- Kubuntu wallpapers/branding/Plymouth themes;
- `plasma-distro-release-notifier`;
- `plasma-discover-backend-snap`;
- `snapd`;
- Firefox Ubuntu Snap transition package;
- games and discretionary applications;
- Ubuntu/Kubuntu-specific helpers without a SupraLINUX architectural reason;
- duplicate applications merely because Kubuntu recommends them.

Every inherited-looking package needs a SupraLINUX reason and, by C4 closure, a matrix/evidence owner where it is a direct desktop dependency.

## 9. Dependency-chain observations retained from research

- `plasma-session-wayland` expresses the intended Wayland session relationship and pulls the appropriate KWin Wayland/session chain.
- KWin Wayland pulls XWayland compatibility; SupraLINUX intentionally retains that compatibility path.
- `pipewire-audio` is Ubuntu's desktop PipeWire abstraction and brings the normal compatibility/WirePlumber/Bluetooth-audio pieces through its dependency chain.
- Ubuntu retains the package name `libpam-kwallet5` for current KWallet PAM integration.
- `kio-extras` materially expands KIO protocol/device support and remains a candidate because SupraLINUX intends common network/file protocols to work out of the box.

Recheck current Ubuntu 26.04 metadata before release freeze; package relationships may change in updates.

## 10. Current metapackage state

`supralinux-desktop` remains an explicitly development/unreleased candidate. Its dependency list is intentionally broad enough to create a complete test surface.

Do not reduce or expand it merely to optimize package count before C4.0.

After C4.0 coverage is green, later C4 defects may justify isolated dependency/configuration changes. After C4 closes, every direct dependency must be one of:

- tested and justified;
- hardware-dependent but product-justified;
- demoted/removed.

Only then should the exact dependency set be considered for freeze.

## 11. Immediate next steps

The previous clean-rootfs/C1-C3 work is complete. The package-audit sequence is now:

1. implement C4.0 runtime surface/dependency inventory;
2. compare it to the versioned capability manifest;
3. close any coverage gaps without changing product packages merely for convenience;
4. implement C4.1 and later feature subgates;
5. when a feature fails, isolate frontend/backend/service/API before modifying dependencies;
6. record package/configuration changes as evidence-driven fixes;
7. complete C4.15 direct-dependency closure;
8. only then freeze/refine the final `supralinux-desktop` set.
