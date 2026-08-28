# Plasma Integration Matrix — Ubuntu 26.04 LTS / Aurora C4

Status: **C4 executable contract active; C4.0 reconciliation in progress**.

This is the canonical capability inventory for Aurora's first integration milestone. `docs/C4_CERTIFICATION.md` defines how these rows are executed, evidenced and certified.

A package being installed is not a pass. A KCM opening is not a pass. A capability passes only when the shipped user workflow reaches its real backend and the resulting state is observed.

Aurora's product boundary for C4 is intentionally strict: Plasma-owned or Plasma-recommended feature surfaces that are installed/exposed by the shipped desktop are in scope. They are not treated as optional accidents merely because Ubuntu pulled them through `Recommends`.

## Status vocabulary

Execution status:

- `PREREQUISITE-CERTIFIED` — already covered by accepted C1/C2/C3 evidence.
- `PENDING-C4` — in automated C4 scope and not yet executed.
- `PASS-C4` — automated C4 acceptance passed.
- `FAIL-C4` — reproducible integration defect.
- `BLOCKED-UPSTREAM` — reproduced upstream blocker with evidence.
- `NOT-EXPOSED` — intentionally not part of the current Aurora Plasma baseline.
- `FUTURE` — deliberately deferred product work.

Hardware status:

- `NOT-REQUIRED`
- `VIRTUALIZED-ONLY`
- `PENDING-HW`
- `HW-PASS`

## C1-C3 prerequisites

| ID | Capability | Evidence owner | Status |
|---|---|---|---|
| AUR-CORE-001 | Plasma desktop starts | C3 acceptance | PREREQUISITE-CERTIFIED |
| AUR-CORE-002 | Wayland primary session | C3 acceptance | PREREQUISITE-CERTIFIED |
| AUR-CORE-003 | X11 app compatibility under Wayland | C3 acceptance | PREREQUISITE-CERTIFIED |
| AUR-CORE-004 | SDDM KWin Wayland greeter | C2 acceptance | PREREQUISITE-CERTIFIED |

These rows are not reopened by C4 unless a later product change creates a documented regression scope.

## C4.0 — Surface and contract inventory

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-COVER-001 | Every shipped/discoverable Plasma KCM has an owner/test row | `kcmshell6 --list`, plugin metadata, dpkg ownership | software | zero unknown/missing KCMs and zero unresolved owners | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-002 | Every shipped KWin configurable/plugin surface is mapped | installed KWin plugin/metadata inventory + dpkg | software | zero unknown/missing KWin surfaces and zero unresolved owners | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-003 | Plasma applets/plasmoids, KDED and Dolphin/KIO integrations are mapped | installed plugin/action inventory + dpkg ownership | software | zero unknown/missing integration surfaces and zero unresolved owners | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-004 | Direct `supralinux-desktop` dependencies are justified | dpkg/DEB metadata + matrix mapping | software | every direct dependency maps to a capability/policy | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-005 | Portal backends/routing are inventoried | `.portal` descriptors, `*-portals.conf`, D-Bus | software | installed portal backends are mapped and routing config is present | PENDING-C4 | NOT-REQUIRED |
| AUR-COVER-006 | Plasma feature `Recommends` are explicitly owned by Aurora | `apt-cache depends plasma-desktop` + versioned manifest | software | zero unknown/missing recommended feature packages | PENDING-C4 | NOT-REQUIRED |

## C4.1 — System Settings / KWin / desktop software behavior

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-PLASMA-001 | Built-in Plasma shell widgets/services are usable | plasmashell/KDED/KConfig/KActivities as applicable | software | every inventoried built-in surface instantiates cleanly; representative actions/configuration work and persist | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-001 | Accessibility settings surface is mapped | Plasma/KWin accessibility config | software + HW split | every exposed control maps to C4.14 or HW follow-up | PENDING-C4 | PENDING-HW |
| AUR-KCM-002 | Activities create/switch/remove and persist | Plasma Activities service | software | real lifecycle works and returns to baseline | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-003 | File Search/Baloo controls affect indexing state | Baloo config/service | software | enable/disable/config change reflected by backend | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-004 | Desktop paths reflect XDG user dirs | `user-dirs.dirs` + KCM | software | KCM and XDG state agree | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-005 | Game controller/button-remap surface is functional where hardware exists | KWin/input/game-controller stack | virtualized + HW | virtual/software path works where possible; representative controller remains HW follow-up | PENDING-C4 | PENDING-HW |
| AUR-KCM-006 | Background-services KCM lists actionable installed services | KDED/systemd/D-Bus | software | representative toggle changes actual service state | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-007 | Global shortcuts | KGlobalAccel/KWin | software | representative shortcut persists and triggers action | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-008 | System Settings landing/navigation | System Settings plugin discovery | software | mapped modules discover without broken entries | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-009 | Plasma Search/KRunner integration | KRunner/Milou config | software | enable/disable/config lifecycle changes actual search behavior | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-010 | Session behavior | Plasma session management | software | representative setting persists and is consumed | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-011 | Splash configuration | Plasma look-and-feel/splash config | software | supported selection applies/persists without stale entry | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-012 | Qt Quick/Plasma renderer settings | Plasma/Qt config | software | representative setting produces documented runtime state | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-013 | Recent files/privacy behavior | KActivities/recent-doc state | software | state changes as configured and can be cleared | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-014 | Workspace/general behavior | Plasma/KWin config | software | representative setting is consumed and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-015 | Spell checking | Sonnet dictionaries/providers | software | supported locale has usable provider/dictionary | PENDING-C4 | NOT-REQUIRED |
| AUR-KCM-016 | KRunner settings capability | Plasma Search/KRunner in Plasma 6.6 | software | functionality is covered through current Plasma Search surface; no obsolete standalone KCM is required | PENDING-C4 | NOT-REQUIRED |
| AUR-DESKTOP-001 | Autostart management | Plasma Workspace autostart | software | add/disable/remove representative entry and verify login behavior | PENDING-C4 | NOT-REQUIRED |
| AUR-DESKTOP-002 | Default applications and file associations | KService/MIME apps | software | representative defaults/association change, launch and restore correctly | PENDING-C4 | NOT-REQUIRED |
| AUR-DESKTOP-003 | User feedback settings | KUserFeedback/Plasma config | software | exposed policy state is readable/changeable and persists without network dependency | PENDING-C4 | NOT-REQUIRED |
| AUR-DESKTOP-004 | Notifications | Plasma notification service | software | representative notification and configuration path work end-to-end | PENDING-C4 | NOT-REQUIRED |
| AUR-APPEAR-001 | Global theme, Plasma style, colors, app style, icons, cursors, fonts, wallpaper and system sounds | Plasma/KConfig/theme/font stacks | software | each inventoried appearance surface applies a valid shipped choice and restores cleanly | PENDING-C4 | NOT-REQUIRED |
| AUR-APPEAR-002 | Night Light/day-night cycle | KWin color management + geolocation/time inputs where applicable | software/virtualized | deterministic schedule/manual state reaches KWin and restores | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-APPEAR-003 | Gamma controls | KWin/display gamma path | virtualized + HW | supported virtual path works; physical-output behavior follows hardware matrix | PENDING-C4 | PENDING-HW |
| AUR-SEC-001 | Screen locking configuration | KScreenLocker + KDE KCM | software | lock, unlock, timeout/configuration and persistence work | PENDING-C4 | NOT-REQUIRED |
| AUR-INPUT-001 | Keyboard layouts/options | KWin/libxkbcommon/xkb-data | software | add/switch layout; option works and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-INPUT-002 | Mouse settings | KWin/libinput | virtualized | representative supported setting reaches backend | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-INPUT-003 | Touchpad | KWin/libinput | hardware | software surface mapped; representative physical controls deferred | PENDING-C4 | PENDING-HW |
| AUR-INPUT-004 | Touchscreen/tablet | KWin/libinput/tablet stack | hardware | software surface mapped; representative physical validation deferred | PENDING-C4 | PENDING-HW |
| AUR-KWIN-001 | Display configuration | KScreen/KWin | virtualized | virtual output resolution/scaling change applies and persists | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-KWIN-002 | Global animation speed | KWin | software | setting changes authoritative KWin config and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-003 | Desktop effects/effect configuration | KWin effects/plugins | software | every inventoried configurable effect plugin loads; representative enable/disable/config works | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-004 | Virtual desktops | KWin virtual desktop API/config | software | add/switch/remove/persist; KWin stays stable | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-005 | Window decorations | KWin decoration plugin/config | software | shipped decorations apply live and persist | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-006 | Window rules | KWin rules | software | rule matches representative Wayland window and is removable | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-007 | XWayland controls | KWin XWayland policy | software | policy change is reflected without breaking C3 compatibility | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-008 | Window behavior | KWin options | software | representative focus/placement/action option works | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-009 | Screen edges | KWin screen-edge config | virtualized | configured edge action triggers and cleans up | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-KWIN-010 | Task switcher | KWin TabBox | software | Alt-Tab works with selected layout/behavior | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-011 | KWin scripts | KWin scripting | software | discover/enable/disable representative script lifecycle | PENDING-C4 | NOT-REQUIRED |
| AUR-KWIN-012 | Virtual/on-screen keyboard | KWin input method + `plasma-keyboard` | virtualized | both exposed KCM paths register/use a functional virtual keyboard | PENDING-C4 | VIRTUALIZED-ONLY |

## C4.2 — Privilege and secrets integration

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-CORE-005 | Privileged desktop actions use Plasma Polkit agent | polkit + `polkit-kde-agent-1` | privileged | real privileged action challenges, succeeds with authorization, fails/cancels safely | PENDING-C4 | NOT-REQUIRED |
| AUR-CORE-006 | KWallet login/settings integration | PAM + KWallet + KWallet KCM | privileged/session | password login unlocks wallet; settings work; secret write/read/relogin path works | PENDING-C4 | NOT-REQUIRED |
| AUR-PRIV-001 | Date/time privileged helper path | timedate/system helper + Polkit | privileged | reversible privileged timezone/time-related action reaches backend | PENDING-C4 | NOT-REQUIRED |
| AUR-PRIV-002 | SDDM configuration privileged write path | `kde-config-sddm` helper + Polkit | privileged | reversible setting writes through supported helper without corrupting C2 baseline | PENDING-C4 | NOT-REQUIRED |
| AUR-DESKTOP-005 | User account management | AccountsService/system helpers + Polkit | privileged | create/change/delete disposable local user via supported path and verify system state | PENDING-C4 | NOT-REQUIRED |

## C4.3 — Networking and VPN

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-NET-001 | Ethernet/wired networking | Plasma-NM + NetworkManager D-Bus | virtualized | create/activate/connect/disconnect/reconnect controlled NIC profile | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-NET-002 | Wi-Fi | Plasma-NM + NetworkManager | hardware | software surface mapped; secured Wi-Fi deferred to representative hardware | PENDING-C4 | PENDING-HW |
| AUR-NET-003 | OpenVPN | Plasma-NM + `network-manager-openvpn` | external fixture | controlled local tunnel establishes and carries traffic | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-004 | OpenConnect | Plasma-NM + `network-manager-openconnect` | external fixture | controlled supported tunnel establishes and carries traffic | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-008 | Cellular/mobile broadband | Plasma-NM + ModemManager | hardware/virtualized | exposed state is mapped; real modem path deferred unless faithful fixture exists | PENDING-C4 | PENDING-HW |
| AUR-NET-009 | Radio/rfkill state integration | kernel rfkill + NM/BlueDevil | virtualized/HW | software state propagates correctly; physical radios deferred | PENDING-C4 | PENDING-HW |
| AUR-NET-010 | Hotspot | Plasma-NM + NetworkManager | hardware/virtualized | profile lifecycle and sharing path work where fixture supports AP mode | PENDING-C4 | PENDING-HW |
| AUR-NET-011 | Proxy/network preference settings | KIO proxy/network config | software | representative proxy state is consumed by KDE/KIO and restored | PENDING-C4 | NOT-REQUIRED |

## C4.4 — Audio

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-AUDIO-001 | Desktop audio | Plasma-PA + PipeWire/WirePlumber | virtualized | real playback stream; volume/mute/device state changes reach backend | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-AUDIO-002 | Audio routing | PipeWire/WirePlumber | virtualized | stream moves between available fixture endpoints | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-AUDIO-003 | Bluetooth audio | BlueZ + PipeWire Bluetooth | hardware | representative physical headset profiles/connectivity deferred | PENDING-C4 | PENDING-HW |

## C4.5 — Bluetooth

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-HW-006 | Bluetooth adapter/control/KIO path | BlueDevil + BlueZ | virtualized + HW | virtual HCI enable/disable/discovery state propagates end-to-end; KIO path loads | PENDING-C4 | PENDING-HW |
| AUR-BT-002 | Peripheral pairing/reconnect | BlueDevil + BlueZ `Device1` | hardware | representative physical pairing/reconnect later | PENDING-C4 | PENDING-HW |

## C4.6 — Flatpak and portal routing

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-FLAT-001 | Flatpak runtime | Flatpak | software | local test Flatpak install/run/remove succeeds | PENDING-C4 | NOT-REQUIRED |
| AUR-FLAT-002 | Flatpak permissions KCM | `kde-config-flatpak` + Flatpak permissions | software | permission change alters sandbox behavior and is restored | PENDING-C4 | NOT-REQUIRED |
| AUR-PORTAL-001 | KDE portal backend/file chooser | XDG portal broker + KDE backend | software | effective KDE routing and real chooser path work | PENDING-C4 | NOT-REQUIRED |
| AUR-PORTAL-004 | GTK portal compatibility fallback | portal routing config + D-Bus | software | GTK fallback serves justified interfaces without stealing KDE-native routes | PENDING-C4 | NOT-REQUIRED |
| AUR-PORTAL-005 | Secret portal uses KWallet | `kwallet.portal` + KWallet | software/session | Secret portal resolves to KWallet and stores/retrieves a controlled secret | PENDING-C4 | NOT-REQUIRED |

## C4.7 — Capture and sharing

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-PORTAL-002 | Wayland screenshot/capture | KWin screenshot + portal | software/virtualized | representative capture returns valid image without leak | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-PORTAL-003 | Wayland screen sharing | KWin screencast + PipeWire + KDE portal + client | external-client | real stream plus clean close for >=30 repeated cycles per selected path | PENDING-C4 | VIRTUALIZED-ONLY |

## C4.8 — Remote desktop

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-RDP-001 | KRDP settings | KRDP KCM/config | software | KCM state persists and maps to actionable server state | PENDING-C4 | NOT-REQUIRED |
| AUR-RDP-002 | KRDP existing/physical-session path and remote-input integration | KRDP + KWin/PipeWire/Wayland/EIS | external-client | external client obtains usable authenticated session/input and clean disconnect | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-RDP-003 | KRDP virtual-session/monitor path | KRDP virtual monitor/session | external-client | requested virtual desktop lifecycle works end-to-end | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-RDP-004 | KDE RDP client (`krdc`) | KRDC | application | certify if retained in the shipped product baseline | PENDING-C4 | NOT-REQUIRED |

## C4.9 — Printing

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-PRINT-001 | Printer configuration/Plasma applet | Print Manager + CUPS | virtualized | add/configure/remove controlled IPP target; applet state follows queue | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-PRINT-002 | Driverless discovery | CUPS/OpenPrinting + virtual IPP Everywhere target | virtualized | target discovered/usable driverlessly | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-PRINT-003 | Job lifecycle | CUPS + Print Manager | virtualized | fixture receives job; queue/status/cancel/failure path work | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-SCAN-001 | Scanning | none exposed in current baseline | product decision | no scanner UI/app is currently claimed by Aurora Plasma baseline | NOT-EXPOSED | PENDING-HW |

## C4.10 — Storage/removable media

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-HW-001 | Removable media/device actions/notifier | Solid + UDisks2 + Plasma | virtualized | hotplug/mount/read-write/unmount/eject and action/notifier lifecycle work | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-HW-002 | Device automount settings | Plasma automounter + UDisks2 | virtualized | policy change changes attach/login behavior and is restored | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-HW-005 | SMART disk health | `plasma-disks` + SMART backend | hardware | software/KDED surface works; meaningful physical SMART validation later | PENDING-C4 | PENDING-HW |

## C4.11 — Samba / KIO / KIO-FUSE

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-KIO-001 | Shipped KIO workers/actions are functional | KIO/KIO Extras + protocol dependencies | software/external fixtures | every inventoried worker/action loads and representative remote/local protocols are exercised; no exposed dead worker | PENDING-C4 | NOT-REQUIRED |
| AUR-SHARE-001 | KDE Purpose/share file action | KF6 Purpose | software | share action resolves providers safely and does not expose broken target entries | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-005 | Browse/read/write SMB share | KIO SMB + Samba client libs | external fixture | controlled remote share browsed/read/written successfully | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-006 | Create local SMB share | KDE file sharing + Samba usershare/server | external-client | share created through shipped integration and accessed externally | PENDING-C4 | NOT-REQUIRED |
| AUR-NET-007 | KIO resource in non-KIO app | KIO-FUSE | external fixture | remote resource exposed through conventional local path | PENDING-C4 | NOT-REQUIRED |

## C4.12 — Power/platform integration

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-HW-003 | Power management/battery applet path | PowerDevil + UPower/systemd | virtualized | representative policy/action works; suspend/resume where supported; Plasma remains healthy | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-HW-004 | Battery/brightness | PowerDevil hardware path | hardware | physical laptop controls later | PENDING-C4 | PENDING-HW |
| AUR-POWER-005 | Power profiles dependency is justified | `power-profiles-daemon` + PowerDevil/platform | virtualized/HW | available profile path behaves correctly or dependency is demoted later | PENDING-C4 | PENDING-HW |
| AUR-PLATFORM-001 | Ambient/orientation sensor integration | `iio-sensor-proxy` | hardware | exposed capability mapped; representative sensor later | PENDING-C4 | PENDING-HW |
| AUR-PLATFORM-002 | Hybrid-GPU integration | `switcheroo-control` | hardware | exposed capability mapped; representative hybrid GPU later | PENDING-C4 | PENDING-HW |

## C4.13 — Locale/language/XDG directories

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-L10N-001 | Locale established before first Plasma login | locale stack + test pre-login setup | software | clean user first session has requested locale | PENDING-C4 | NOT-REQUIRED |
| AUR-L10N-002 | Plasma/Qt translation | Plasma language support + Qt translations | software | representative core UI uses selected supported language | PENDING-C4 | NOT-REQUIRED |
| AUR-L10N-003 | XDG user directories | `xdg-user-dirs` | software | clean first login creates/configures localized dirs consistently | PENDING-C4 | NOT-REQUIRED |
| AUR-L10N-004 | Language-change migration | future explicit workflow | future | populated directories never silently renamed/lost | FUTURE | NOT-REQUIRED |
| AUR-L10N-005 | Installer-selected language end-to-end | installer + locale stack | Phase 4 | installer not implemented yet; no C4 claim | FUTURE | NOT-REQUIRED |
| AUR-L10N-006 | Region & Language settings | Plasma locale KCM + locale data | software | locale/format/language choices are valid, persist and are consumed on next session | PENDING-C4 | NOT-REQUIRED |

C4 initially exercises at least `en_US.UTF-8` and `es_AR.UTF-8`; the full supported-language matrix belongs to installer/release work.

## C4.14 — Accessibility

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-A11Y-001 | AT-SPI runtime/accessibility KCM | AT-SPI bus/runtime | software | accessibility bus usable in Plasma session and settings apply | PENDING-C4 | NOT-REQUIRED |
| AUR-A11Y-002 | Screen reader | Orca + Speech Dispatcher + AT-SPI | software | representative Plasma/Qt UI can be observed/navigated and speech path is usable | PENDING-C4 | NOT-REQUIRED |
| AUR-A11Y-003 | KWin accessibility input/visual plugins | KWin accessibility plugins/effects | software | every inventoried accessibility plugin loads and representative behavior is observable | PENDING-C4 | NOT-REQUIRED |

## C4.15 — Additional Plasma integrations and closure audit

C4.15 owns Plasma feature surfaces discovered through Ubuntu's current Plasma package graph that do not fit earlier gates. Because Aurora promises a complete functional Plasma desktop, these are supported product surfaces unless a later explicit product decision removes them before release.

| ID | User surface / claim | Backend / authoritative state | Test class | PASS criterion | Status | HW |
|---|---|---|---|---|---|---|
| AUR-AUX-001 | KInfoCenter/system information | KInfoCenter modules + kernel/system APIs | software/HW split | every inventoried module opens and reports meaningful data or clearly reports unsupported hardware; no broken module | PENDING-C4 | PENDING-HW |
| AUR-AUX-002 | Plasma System Monitor + monitoring widgets/backend | `plasma-systemmonitor` + KSystemStats | software | application and inventoried widgets receive representative live metrics | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-003 | GTK appearance integration | Breeze GTK + KDE GTK integration | software | representative GTK settings/theme path is coherent and persists | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-004 | Crash handling | DrKonqi | software | controlled non-critical crash reaches usable crash-handling path without destabilizing session | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-005 | SSH askpass | `ksshaskpass` | software | supported askpass invocation returns/cancels correctly in session | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-006 | Pinentry Qt | `pinentry-qt` | software | controlled pinentry request is usable/cancellable in graphical session | PENDING-C4 | NOT-REQUIRED |
| AUR-AUX-007 | Plasma virtual keyboard dependency closure | `plasma-keyboard` + KWin | virtualized | covered by AUR-KWIN-012; no dead direct dependency | PENDING-C4 | VIRTUALIZED-ONLY |
| AUR-AUX-008 | ModemManager dependency closure | ModemManager | hardware | maps to AUR-NET-008 and is functional on representative hardware | PENDING-C4 | PENDING-HW |
| AUR-AUX-009 | rfkill dependency closure | kernel rfkill | hardware/virtualized | maps to AUR-NET-009 and propagates state | PENDING-C4 | PENDING-HW |
| AUR-AUX-010 | `plasma-disks` dependency closure | SMART backend | hardware | maps to AUR-HW-005; no dead surface | PENDING-C4 | PENDING-HW |
| AUR-AUX-012 | Miscellaneous discovered session integration plugin | owning Plasma/KDE component | software | any surface assigned here must be reclassified to a specific capability before C4.15 closure | PENDING-C4 | NOT-REQUIRED |
| AUR-SEC-002 | Plasma Firewall | `plasma-firewall` + UFW/firewalld backend + Polkit | privileged | create/modify/delete controlled rule through shipped UI/API path; backend state matches; cancel/failure safe | PENDING-C4 | NOT-REQUIRED |
| AUR-VAULT-001 | Plasma Vaults | `plasma-vault` + shipped encryption backend(s) | software | create/open/write/close/reopen/remove disposable vault and file-action/applet path work | PENDING-C4 | NOT-REQUIRED |
| AUR-THUNDERBOLT-001 | Thunderbolt authorization | `plasma-thunderbolt` + `bolt` | hardware | software daemon/KCM integration healthy; representative authorize/forget device requires HW | PENDING-C4 | PENDING-HW |
| AUR-BACKUP-001 | Plasma/Kup backup | `kup-backup` + selected backup backend | software/external fixture | configure backup, create real backup, verify and restore controlled file, then cleanup | PENDING-C4 | NOT-REQUIRED |
| AUR-BROWSER-001 | Plasma Browser Integration | native host + browser extension/integration | external-client | shipped supported browser has integration ready without user package installation; representative media/download/browser action works | PENDING-C4 | NOT-REQUIRED |

## Software management / Snap policy

Snap policy remains a certified prerequisite. Discover itself is now in C4 because Ubuntu's current Plasma package graph installs/recommends it and Aurora's complete-Plasma policy therefore treats its visible functionality as product scope.

| ID | Capability | Backend / authoritative state | PASS criterion | Status |
|---|---|---|---|---|
| AUR-SW-001 | Snap blocked by default | APT policy | existing resolver/rootfs/C1-C3 assertions remain green | PREREQUISITE-CERTIFIED |
| AUR-SW-002 | Snap policy is reversible | APT policy | existing resolver-policy tests remain green | PREREQUISITE-CERTIFIED |
| AUR-SW-003 | Discover resolves without Snap backend | package-resolution CI | Snap backend absent/blocked without breaking Discover package resolution | PREREQUISITE-CERTIFIED |
| AUR-SW-004 | Discover manages DEB/APT software and updates | Discover + PackageKit/APT | browse/search/install/remove/update controlled package path works without Snap | PENDING-C4 |
| AUR-SW-005 | Discover manages Flatpak | Discover Flatpak backend + Flatpak | local test Flatpak appears/installs/removes through Discover | PENDING-C4 |
| AUR-SW-006 | Discover firmware updates | Discover fwupd backend + fwupd | backend loads and controlled/no-device path is healthy; representative firmware HW later | PENDING-C4 |

## Explicitly outside the current C4 Plasma surface

The following are not implicitly added merely because unrelated packages exist:

- fingerprint authentication, until a Plasma-visible enrollment/authentication path is deliberately included;
- KDE Connect as a default application, unless it enters the shipped desktop package graph;
- scanner application/workflow, because the current Plasma baseline exposes no scanner UI;
- unrelated KDE applications such as Krita/Kdenlive/KMail/etc.; application-set selection is a later product layer.

Archive handling is different from an arbitrary app decision because the installed KIO `archive` worker is already a shipped surface. C4.11 therefore certifies the currently exposed KIO archive worker. A full Ark/RAR desktop application workflow remains a later application-set decision unless Ark is promoted into the baseline.

## Matrix execution rule

C4.0 is the guard against silent coverage gaps. Before feature subgates are accepted, the runtime inventory must prove that every currently exposed Plasma/KWin/integration surface and every current `plasma-desktop` feature recommendation maps to this matrix.

After C4 is complete, this matrix becomes evidence for making the required product dependencies explicit in `supralinux-desktop`. Reliance on Ubuntu `Recommends` alone is not considered sufficient for a feature that Aurora promises.
