# Aurora C4 — Feature Integration Certification

Status: **implementation active; C4.0 surface reconciliation in progress**

C1, C2 and C3 are certified prerequisites. C4 must not reopen them unless a later product change creates a real regression risk.

## 1. Purpose

C4 certifies that the Plasma features SupraLINUX exposes are functional end-to-end. A visible KCM, plasmoid, applet, Dolphin/KIO action, Plasma-owned application or dialog does not pass merely because it loads. Each claimed capability must account for its frontend, backend, service/API path, permissions, runtime dependencies, happy path, common failure path and resulting state.

Aurora's product rule is deliberately strict:

> If Plasma exposes the function in the shipped SupraLINUX desktop, the user must be able to use it without installing additional packages, helpers, backends or plugins.

For C4, Plasma feature packages installed through Ubuntu's current `plasma-desktop` dependency/recommendation graph are product surfaces, not accidental extras. C4.0 inventories them before `supralinux-desktop` dependencies are made explicit.

The canonical capability inventory lives in `docs/PLASMA_INTEGRATION_MATRIX.md`.

## 2. Non-goals

C4 does not:

- re-certify C1/C2/C3 without a regression trigger;
- freeze `supralinux-desktop` before evidence exists;
- claim broad physical-hardware support from virtual devices;
- install unrelated KDE applications merely to make a checklist green;
- start ISO/installer, branding or C5 manual QA work;
- hide or suppress warnings instead of classifying them.

The “unrelated application” rule does not exclude Plasma-owned feature applications already exposed by the Plasma package graph, such as Discover or Plasma System Monitor. Those are C4 scope when shipped.

## 3. Status vocabulary

Capability execution status:

- `PREREQUISITE-CERTIFIED`
- `PENDING-C4`
- `PASS-C4`
- `FAIL-C4`
- `BLOCKED-UPSTREAM`
- `NOT-EXPOSED`
- `FUTURE`

Hardware claim status is separate:

- `NOT-REQUIRED`
- `VIRTUALIZED-ONLY`
- `PENDING-HW`
- `HW-PASS`

A capability may be `PASS-C4` and still be `PENDING-HW`.

## 4. Required capability contract

Every C4 capability must identify or be traceable to:

1. stable capability ID;
2. C4 subgate owner;
3. user-visible surface;
4. exact product claim;
5. UI package/component;
6. backend implementation;
7. relevant system/user service or unit;
8. authoritative D-Bus/API/state source where applicable;
9. product dependencies;
10. CI-only fixture dependencies;
11. test class;
12. happy-path assertion;
13. common failure-path assertion;
14. persistence requirement where relevant;
15. cleanup/rollback behavior;
16. exact PASS condition;
17. exact FAIL condition;
18. hardware follow-up status;
19. regression scope against C1/C2/C3;
20. evidence pointer after execution.

CI fixtures must never be silently promoted into product dependencies.

## 5. C4 gate layout

### C4.0 — Surface and contract inventory

Goal: prove that the certification matrix covers the complete currently shipped Aurora Plasma surface before feature testing or package correction begins.

The runtime/post-boot inventory must collect at least:

- all KCMs discoverable by the shipped Plasma/KCM stack;
- KCM metadata where present, including distinction between System Settings and KInfoCenter/informational modules;
- KWin configurable plugins/metadata;
- Plasma compiled applets and QML plasmoids;
- KDED session plugins;
- Dolphin/KIO workers, file-item actions, properties-dialog plugins and service menus;
- relevant systemd system and user units;
- relevant D-Bus names/services;
- installed XDG portal backends and routing configuration;
- direct `supralinux-desktop` dependencies;
- current direct `plasma-desktop` feature `Recommends`;
- package owner and version for every discovered plugin/surface where resolvable.

Versioned manifests in `tests/c4/` define the expected surface. The host reconciliation stage compares runtime composite keys against those manifests and verifies that every capability ID referenced by a manifest exists in `docs/PLASMA_INTEGRATION_MATRIX.md`.

PASS requires:

- zero unknown and zero missing KCMs;
- zero unknown and zero missing KWin surfaces;
- zero unknown and zero missing Plasma/KDED/KIO integration surfaces;
- zero unknown and zero missing direct desktop dependencies;
- zero unknown and zero missing portal backends;
- zero unknown and zero missing Plasma feature recommendations;
- zero unresolved package owners for discovered in-scope surfaces;
- portal routing configuration present;
- live Plasma session stability through the inventory.

C4.0 does **not** prove the functionality of those surfaces. It proves that none can escape later certification.

C4.0 must pass before product dependency changes are made for C4 defects.

### C4.1 — System Settings / KWin / Plasma shell behavior

Covers software-only or virtualizable Plasma/KWin settings, built-in shell widgets and desktop services: activities, Baloo/search, autostart, defaults/file associations, notifications, appearance, keyboard layouts, global shortcuts, workspace/session behavior, recent files, KWin animations/effects/scripts, virtual desktops, decorations, rules, XWayland policy, window behavior, screen edges, task switching and screen locking.

Every inventoried built-in Plasma widget/service must at least instantiate/load without a broken dependency. Functions with meaningful actions/configuration require real behavioral assertions and persistence/cleanup where applicable.

Hardware-specific touchpad, touchscreen, tablet and controller claims remain separate `PENDING-HW` entries.

### C4.2 — Polkit + KWallet + privileged desktop actions

Polkit PASS requires a real privileged operation that triggers the Plasma Polkit agent, succeeds with valid authentication, does not succeed on cancel/invalid authorization, and leaves the session healthy.

KWallet PASS requires password-based login rather than C3 autologin, functional KWallet settings, successful wallet access without an unexpected duplicate password prompt, temporary secret write/read, logout/login persistence where applicable, and cleanup.

Also cover reversible privileged paths for date/time, SDDM settings and disposable user-account management.

### C4.3 — NetworkManager + Plasma-NM + VPN

Use a dedicated test NIC so destructive network assertions cannot sever diagnostics.

Cover wired profile lifecycle, NetworkManager authoritative state, OpenVPN/OpenConnect real tunnels, mobile-broadband/rfkill surface classification, proxy settings and hotspot behavior where the fixture supports it.

Wi-Fi and physical modem behavior remain hardware follow-up unless a faithful virtual fixture is documented.

### C4.4 — PipeWire + WirePlumber + Plasma audio

Use virtual audio hardware. PASS requires a real stream, backend-visible nodes, Plasma volume/mute/device changes reflected in PipeWire/WirePlumber, routing where multiple endpoints exist, and service stability.

### C4.5 — Bluetooth + BlueDevil

A CI-only virtual HCI fixture may prove kernel HCI → BlueZ → D-Bus → BlueDevil propagation, adapter enable/disable and discovery. Pairing with representative physical peripherals and Bluetooth audio profiles remain `PENDING-HW`.

### C4.6 — Flatpak + portal routing

Use a locally built test Flatpak.

Record `XDG_CURRENT_DESKTOP`, portal descriptors and effective routing. KDE must own intended Plasma-native interfaces; GTK fallback must not steal them. The KWallet Secret portal is also an explicit product surface and must be tested.

Flatpak permissions must alter real sandbox behavior and then be restored.

### C4.7 — Screenshot / screencast / screen sharing

Exercise the real Wayland portal path through KWin and PipeWire. Obtain valid capture/frames, close sessions cleanly and verify indicators/resources disappear.

The repeated screen-sharing blocker candidate in `docs/UPSTREAM_BLOCKERS.md` still requires at least 30 consecutive start/share/stop cycles per selected representative client path where practical.

### C4.8 — KRDP / RDP

Keep server and external client roles separate. Cover KRDP settings, existing-session path, virtual-monitor/session path, authentication, framebuffer/input lifecycle and clean disconnect.

`krdc` is certified if it remains in the shipped product baseline.

### C4.9 — Printing / CUPS

Use a controlled IPP Everywhere target. Cover discovery/addition, queue creation, real job receipt, state, cancellation and unavailable-printer failure behavior.

### C4.10 — UDisks / Solid / removable media

Use hot-pluggable virtual removable storage. Cover device appearance, Solid/UDisks state, mount/read/write/unmount/eject, automount policy, reattach and cleanup.

SMART software integration is also covered here; meaningful SMART hardware data remains hardware follow-up.

### C4.11 — Samba / KIO / KIO-FUSE

Certify the complete inventoried KIO surface rather than SMB alone. No shipped KIO worker/action may remain a dead plugin.

At minimum exercise controlled fixtures for SMB, SFTP/FTP or equivalent representative remote paths, archive/filter/thumbnail/local workers where deterministic, Bluetooth/MTP/AFC/NFS where hardware or suitable fixtures permit, KDE Purpose/share action, KIO-FUSE, and both incoming/outgoing Samba workflows.

### C4.12 — Power management

Cover PowerDevil policy, actionable power/idle behavior, suspend/resume where supported and Plasma/KWin health afterward.

Battery, brightness, lid, sensors, power profiles and hybrid-GPU hardware claims remain `PENDING-HW` as appropriate, but their installed software integration must not be broken.

### C4.13 — Locale / translations / XDG user directories

C4 does not claim installer behavior. Test pre-first-login locale behavior with clean users.

At minimum exercise `en_US.UTF-8` and `es_AR.UTF-8`, including Plasma/Qt translation, Region & Language settings, regional formats and localized XDG directories.

### C4.14 — Accessibility

Cover AT-SPI, Orca, Speech Dispatcher and every inventoried KWin accessibility plugin/effect relevant to keyboard/mouse/visual assistance. Installing packages alone is insufficient.

### C4.15 — Additional Plasma integrations and closure audit

This gate owns Plasma feature surfaces discovered by C4.0 that do not naturally belong to earlier gates. Current Aurora discovery includes:

- Plasma Firewall and its real firewall backend;
- Plasma Vaults and shipped encryption backend(s);
- Plasma Thunderbolt + `bolt`;
- Kup backup KCM/applet/KIO integration and its backup backend;
- Plasma Browser Integration, including the browser-side component required for supported browsers;
- Plasma Discover with DEB/APT/PackageKit, Flatpak and fwupd paths while Snap remains intentionally blocked;
- Plasma System Monitor + KSystemStats;
- KInfoCenter and all inventoried information modules;
- GTK appearance integration;
- DrKonqi;
- `ksshaskpass`;
- `pinentry-qt`;
- closure of `modemmanager`, `rfkill`, `iio-sensor-proxy`, `switcheroo-control`, `plasma-keyboard` and `plasma-disks`.

A feature already exposed by the shipped Plasma graph may not be labelled “optional” merely to avoid its test. If Aurora does not want to support such a feature, removing the user-visible product surface is a deliberate later product decision requiring regression review; it is not a C4 shortcut.

## 6. Common PASS contract

A capability may become `PASS-C4` only when all applicable points are true:

1. shipped user surface is identified;
2. required product dependencies are present;
3. backend/service/API is available;
4. a real positive action is executed;
5. result is observed using an authoritative state source;
6. a common negative/failure path is exercised;
7. affected desktop/service components remain healthy;
8. no relevant resources are leaked;
9. test state is restored or the disposable guest is destroyed after evidence capture;
10. no relevant failed units/crashes remain unexplained;
11. package versions and targeted logs are recorded;
12. CI-only fixtures are separated from product dependencies.

## 7. Failure classification

Every failure must be classified before changing packages:

- SupraLINUX dependency omission;
- SupraLINUX configuration/policy defect;
- harness/fixture defect;
- VM limitation;
- upstream Ubuntu/KDE/component defect;
- external transient infrastructure failure.

Do not change multiple product variables simultaneously when one defect can be isolated first.

## 8. Evidence contract

Each subgate uses deterministic markers:

```text
AURORA_C4_<GATE>_STAGE=<stage>
AURORA_C4_<CAPABILITY>_PASS
AURORA_C4_<GATE>_SUCCESS
AURORA_C4_<GATE>_FAILURE:<reason>
```

The harness requires exactly one final success marker, zero failure markers and all expected capability markers for that execution set. Runner/QEMU exit code alone is insufficient.

Artifacts include applicable serial logs, capability manifests, package/version ownership, journals, D-Bus/API snapshots, fixture logs, crash/failed-unit inventory, portal routing and cleanup state.

## 9. Regression rule for C1-C3

C4 implementation does not automatically re-run C1-C3. Regression is required only when a change can plausibly affect certified scope:

- core Plasma/KWin/session package changes → C3, and C2 if greeter/session infrastructure overlaps;
- SDDM/KWin greeter configuration → C2 and normally C3;
- kernel/initramfs/base/systemd changes → C1 plus affected later gates;
- XWayland/session compatibility changes → C3;
- documentation/manifests/harness-only C4 changes → no C1-C3 rerun.

## 10. C4 closure rule

C4 is complete only when:

- C4.0 coverage is green;
- every current in-scope matrix capability is `PASS-C4`, `BLOCKED-UPSTREAM` with an explicit release decision, or explicitly hardware-deferred without overstating support;
- every direct `supralinux-desktop` dependency is justified;
- every Plasma feature package Aurora promises is made an explicit product dependency rather than relying accidentally on Ubuntu `Recommends`;
- no unknown exposed Plasma/KWin/KDED/KIO/portal feature remains;
- known warnings/failures have classifications;
- the exact candidate dependency set is re-evaluated and only afterward frozen.

C4 completion does not replace C5 manual VM QA or later physical-hardware certification.

## 11. Current upstream/reference documentation

Recheck before implementing each subgate because Ubuntu 26.04 updates can move package versions/APIs:

- Ubuntu 26.04 package metadata: `https://packages.ubuntu.com/resolute/` and `https://packages.ubuntu.com/resolute-updates/`
- KDE Plasma documentation: `https://docs.kde.org/`
- KDE developer/admin documentation: `https://develop.kde.org/`
- XDG Desktop Portal: `https://flatpak.github.io/xdg-desktop-portal/`
- Flatpak: `https://docs.flatpak.org/`
- NetworkManager: `https://networkmanager.dev/docs/api/latest/`
- PipeWire: `https://docs.pipewire.org/`
- WirePlumber: `https://pipewire.pages.freedesktop.org/wireplumber/`
- BlueZ: `https://bluez.readthedocs.io/en/latest/`
- OpenPrinting/CUPS: `https://openprinting.github.io/cups/`
- UDisks2: `https://storaged.org/doc/udisks2-api/latest/`
- xdg-user-dirs: `https://www.freedesktop.org/wiki/Software/xdg-user-dirs/`

The repository acceptance records remain authoritative for C1-C3.
