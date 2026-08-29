# Plasma System Settings KCM Audit — Historical Ubuntu KDE 6.6.6 baseline

Status: **HISTORICAL / VERSION-SCOPED INPUT; C4.0 accepted on the Ubuntu KDE 6.6.6 baseline; regenerate if a new KDE stack is adopted**.

Purpose: preserve the package-derived System Settings/KWin surface that was used to build the first executable Aurora C4 inventory, so SupraLINUX can compare a future stack against a known baseline without rewriting history.

This document describes the Ubuntu 26.04 KDE 6.6.6-era package surface. The historical executable capability IDs/statuses live in `docs/PLASMA_INTEGRATION_MATRIX.md`; the execution contract and current pause live in `docs/C4_CERTIFICATION.md`; the active architecture gate is `docs/KDE_STACK_QUALIFICATION.md`.

If the KDE Stack Qualification adopts a newer stack, do not edit the tables below until the new packages/runtime have actually been inventoried. Generate the new runtime surface first, classify deltas, then update this audit from evidence.

## 1. KCMs shipped directly by `plasma-desktop` in the historical Ubuntu 26.04 baseline

The audited Ubuntu 26.04 / Plasma 6.6.6 package surface included these System Settings modules/plugins:

| KCM/plugin | Functional area | C4 acceptance focus |
|---|---|---|
| `kcm_access` | Accessibility | AT-SPI/screen-reader/visual accessibility paths, with hardware split where needed |
| `kcm_activities` | Plasma Activities | Create/switch/remove and persistence |
| `kcm_baloofile` | File Search / Baloo | Backend state, indexing controls and status |
| `kcm_desktoppaths` | User paths | XDG directories and localization consistency |
| `kcm_gamecontroller` | Game controllers | Surface ownership in C4; representative physical controller later |
| `kcm_kded` | Background services | Listed services correspond to installed/actionable backends |
| `kcm_keyboard` | Keyboard | Layouts/options and Wayland behavior |
| `kcm_keys` | Shortcuts | Global shortcut persistence and actual trigger path |
| `kcm_landingpage` | System Settings landing page | Module discovery/navigation and no broken entries |
| `kcm_mouse` | Mouse | Supported settings reach KWin/libinput path |
| `kcm_plasmasearch` | Plasma Search | KRunner/search plugin enable/disable behavior |
| `kcm_smserver` | Session | Representative login/logout/session-setting behavior |
| `kcm_splashscreen` | Plasma splash | Upstream baseline configuration lifecycle |
| `kcm_tablet` | Drawing tablet | Runtime surface inventory; representative hardware later |
| `kcm_touchpad` | Touchpad | Runtime surface inventory; representative hardware later |
| `kcm_touchscreen` | Touchscreen | Runtime surface inventory; representative hardware later |
| `kcm_workspace` | Workspace behavior | Settings actually consumed by Plasma/KWin |
| `kcm_clock` | Date/time | Timezone/time backend and privileged helper/Polkit path |
| `kcm_device_automounter` | Removable-media automount | UDisks/Solid behavior with hot-plug fixture |
| `kcm_qtquicksettings` | Qt Quick settings | Expected runtime effect |
| `kcm_recentFiles` | Recent files | Privacy/history behavior and cleanup |
| `kcm_solid_actions` | Device actions | Solid integration/action dispatch |
| `kcmspellchecking` | Spell checking | Dictionaries/providers for supported C4 locales |
| `kcm_krunnersettings` | KRunner settings | Plugin list/configuration lifecycle |

The same package exposed accessibility schemas for bell, color-blindness correction, invert, keyboard, mouse, screen reader, shake cursor and zoom/magnifier behavior. The accepted historical C4.0 runtime inventory, rather than this static table alone, is the evidence for what was actually exposed by that baseline.

## 2. KWin KCM surface from historical `kwin-common`

The audited Ubuntu 26.04 / KWin 6.6.6 surface included:

| KCM/plugin | Functional area | C4 acceptance focus |
|---|---|---|
| `kcm_animations` | Global animation speed | Change/persistence and KWin health |
| `kcm_kwin_effects` | Desktop Effects | Representative effect lifecycle |
| `kcm_kwin_scripts` | KWin scripts | Discovery/enable/disable/configuration lifecycle |
| `kcm_kwin_virtualdesktops` | Virtual desktops | Add/remove/switch/persistence |
| `kcm_kwindecoration` | Window decorations | Supported setting applies live/persists |
| `kcm_kwinrules` | Window rules | Wayland application matching |
| `kcm_kwinxwayland` | XWayland controls | Policy changes without breaking intended compatibility |
| `kcm_virtualkeyboard` | Virtual keyboard | KWin input-method path with `plasma-keyboard` |
| `kcm_kwinoptions` | Window management behavior | Representative focus/placement/action settings |
| `kcm_kwinscreenedges` | Screen edges | Trigger and persistence |
| `kcm_kwintabbox` | Task/window switcher | Layout/behavior and Alt-Tab operation |
| `kcm_kwintouchscreen` | Touchscreen edges | Surface inventory plus later hardware validation |

KWin also shipped screenshot/screencast plugins. C4 therefore treats Wayland capture/sharing as a KWin + PipeWire + portal/client path, not merely a portal-package check.

## 3. External KCM/integration surfaces in the historical candidate

| Package(s) | Visible/related surface | C4 treatment |
|---|---|---|
| `kscreen` | Displays / HDR/display OSD | C4.1 virtual-output test; physical multi-monitor/HDR later |
| `powerdevil` | Power/battery/brightness | C4.12; hardware capability split |
| `kde-config-screenlocker` | Screen locking | inventory plus applicable software/session behavior |
| `kde-config-sddm` + `sddm` | Login screen configuration | privileged write path in C4.2; preserve C2 greeter baseline |
| `kde-config-flatpak` + `flatpak` | Flatpak permissions | C4.6 real sandbox behavior |
| `krdp` | Remote Desktop settings/server | C4.8 end-to-end external-client tests |
| `plasma-nm` + NetworkManager | Network connections | C4.3 |
| `bluedevil` + BlueZ | Bluetooth | C4.5 virtual HCI software path + physical follow-up |
| `print-manager` + CUPS | Printers | C4.9 virtual IPP job lifecycle |
| `kdenetwork-filesharing` + Samba | Dolphin folder sharing | C4.11 external SMB client |
| `kde-config-gtk-style` + Breeze GTK | GTK appearance | C4.15 |
| `plasma-disks` | SMART disk health | C4.10/C4.15 justification + hardware follow-up |
| `polkit-kde-agent-1` | Authentication dialogs | C4.2 real privileged action |
| `xdg-desktop-portal-kde` | Portals | C4.6/C4.7 |
| `xdg-desktop-portal-gtk` | Portal compatibility fallback | C4.6 routing evidence; keep/remove decision after test |
| `libpam-kwallet5` | Wallet unlock at login | C4.2 password-login flow |
| `at-spi2-core`, `orca`, `speech-dispatcher` | Accessibility / screen reader | C4.14 |

## 4. Network/VPN integration

The historical candidate included:

- `network-manager-openvpn`
- `network-manager-openconnect`

These were selected because Plasma-NM exposes corresponding workflows. When C4 resumes on the adopted stack, C4.3 must prove real controlled tunnels and traffic; plugin presence alone remains insufficient.

Additional VPN protocols are not automatically claimed. The rule remains: do not present a workflow as supported unless its backend is present and tested.

## 5. Printing and network-sharing completeness

### Printing

Historical product candidates:

- `print-manager`
- `cups`
- `cups-client`
- `cups-filters`

C4.9 must exercise a real virtual IPP job path, queue state, cancellation and failure behavior on the adopted stack.

### Samba sharing

Historical product candidates:

- `kdenetwork-filesharing`
- `samba`
- `kio-extras`
- `kio-fuse`

C4.11 tests both remote SMB consumption and creation of a local share through the shipped KDE integration, with an external client verifying access.

## 6. C4 test classes

Each surface receives one or more classes:

- **Software-only** — fully automatable in a real Plasma VM session.
- **Virtualizable** — requires a VM device/service fixture but can be automated credibly.
- **Hardware-assisted** — requires representative physical hardware for the hardware claim.
- **Privileged/system** — explicitly tests Polkit/PAM/system service behavior.
- **External-client** — requires another process/guest/client role outside the tested server/session.

Hardware status is separate from C4 execution status. A virtualized software stack may be `PASS-C4` while physical validation remains `PENDING-HW`.

## 7. Deliberately unresolved / not currently claimed

These remained outside the hard baseline until policy and complete backend paths are chosen:

- `plasma-firewall` — no supported firewall backend policy selected;
- `plasma-thunderbolt` — physical authorization testing required;
- `plasma-vault` — crypto backend and lifecycle/recovery design required;
- fingerprint/PAM — auth-stack and hardware testing required;
- KDE Connect — product/default-app decision;
- browser integration — waits for browser/default-app policy;
- scanner workflow — no scanner UI/app is currently exposed by the baseline;
- archive/RAR workflow — Phase 5 application capability unless runtime discovery exposes a current surface.

Discover is resolver-safe under the implemented Snap policy, but its hard-baseline role remains a deliberate product decision and must be re-evaluated against the adopted KDE stack.

## 8. Next work

The historical package/KCM audit and historical C4.0 are complete. Do not repeat their old checklist as if it were unfinished work.

The active sequence is now:

1. complete `docs/KDE_STACK_QUALIFICATION.md`;
2. if the candidate KDE stack is rejected, resume C4.1 on the last known-good baseline and retain this audit as current reference;
3. if the candidate KDE stack is adopted, install the qualified package set in a clean runtime;
4. regenerate the package-derived KCM/KWin inventory from that stack;
5. rerun C4.0 and compare the new live surface against this historical baseline;
6. classify every added, removed or renamed surface before updating capability mappings;
7. only then resume C4.1 and later functional gates.

Do not add or remove product packages merely to make this static historical audit look tidy. Runtime/dependency evidence drives the new audit.
