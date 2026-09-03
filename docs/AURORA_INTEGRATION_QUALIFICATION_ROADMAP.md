# SupraLINUX Aurora — Integration Qualification Roadmap

Status: **ADOPTED ROADMAP — implementation gated behind KDE Stack Qualification**

Adopted: 2026-09-03

This document turns the SupraLINUX product goal — a complete, reliable, current-stable KDE desktop on Ubuntu 26.04 LTS — into an ordered integration and certification roadmap.

It does **not** reopen KSQ-0, does **not** redefine the currently qualified KDE candidate, and does **not** authorize mixing feature work into an open KSQ-1 build gate. The active KDE Stack Qualification remains the prerequisite for downstream integration work.

## 1. Binding architecture

SupraLINUX remains an Ubuntu 26.04 LTS derivative with a deliberately narrow ownership boundary:

- Ubuntu owns kernel, firmware infrastructure, Mesa/libdrm, systemd, PipeWire/WirePlumber, NetworkManager, Wayland runtime, Qt, base compiler/runtime libraries, Secure Boot foundations and comparable platform infrastructure unless a separately qualified architecture decision proves an override is necessary.
- SupraLINUX owns product integration, KDE packaging where intentionally qualified, SupraLINUX packages/defaults, repository generations, qualification gates, installer integration, release evidence and user-facing completeness.
- KDE releases are selected from official stable upstream releases only. Beta, RC, git/master and technology-preview functionality are not product baselines.
- A visible feature is incomplete until its backend, dependencies, permissions, happy path and common failure path are installed and tested end-to-end.
- A previous PASS is version-scoped evidence. A package or platform change that can affect a certified behavior triggers the relevant regression gate.

## 2. Current KDE candidate

The existing Aurora candidate remains:

- Ubuntu 26.04 LTS (`resolute`)
- Ubuntu Qt 6.10.2
- KDE Frameworks 6.29.x candidate
- KDE Plasma/KWin 6.7.4 candidate
- KDE Gear evaluated independently

As of 2026-09-03 KDE upstream lists Plasma 6.7.4 and Frameworks 6.29.0 as current stable releases. This roadmap does not promote them by documentation alone; existing KSQ promotion requirements remain binding.

Decision: **CONTINUE / PROBE** the existing candidate. Do not chase a newer KDE generation if that would require replacing Ubuntu-owned Qt, Wayland runtime, Mesa, kernel or another platform layer merely to satisfy version requirements.

## 3. New project-wide qualification principles

### 3.1 KDE LTS fix-parity gate — ADOPT

Because Aurora intentionally evaluates a KDE stack newer than the Ubuntu/Kubuntu frozen baseline, SupraLINUX must not assume that newer automatically means better maintained.

For each materially relevant KDE/Kubuntu fix published for the Ubuntu 26.04 LTS desktop baseline, the maintained SupraLINUX KDE stack must classify the fix as one of:

1. already present upstream in the shipped SupraLINUX version;
2. applicable and backported/updated through the normal qualified source path;
3. not applicable, with evidence;
4. pending investigation, which blocks stable promotion when security or serious data-loss/session reliability is involved.

This parity gate is especially important for security, KWin/session crashes, login/session startup, display regressions, KWallet/PAM, networking, portals, power management, data loss and user-visible LTS integration fixes.

Any adopted parity fix triggers regressions for the package and all affected functional gates.

### 3.2 Immutable SupraLINUX repository generations — ADOPT

`stable` and `testing` are channels, not mutable untracked package buckets.

Every promoted repository state must be represented by an immutable generation containing at least:

- generation identifier and creation time;
- Ubuntu snapshot identity used for qualification where applicable;
- exact SupraLINUX binary package versions;
- exact corresponding source package identities;
- Release/InRelease metadata and signing identity;
- package index hashes;
- package SHA-256 hashes;
- `.changes` and `.buildinfo` evidence where applicable;
- source provenance and SupraLINUX delta metadata for overrides/backports;
- qualification manifest and PASS/FAIL gate references;
- SBOM/provenance artifacts when implemented;
- explicit predecessor generation for rollback testing.

Promotion must publish a generation deliberately. CI success alone must never mutate `stable` automatically.

### 3.3 Ubuntu Snapshot mapping — ADOPT

Every release/update qualification that depends on Ubuntu archive state must record the exact Ubuntu Snapshot Service timestamp or an equivalently immutable Ubuntu input identity.

The snapshot identity is part of the qualification evidence. Moving to a newer Ubuntu snapshot is a platform-input change and triggers the regressions mapped to changed packages.

### 3.4 Package-generation rollback — PROBE

SupraLINUX will design and certify rollback between known repository generations independently of filesystem snapshots.

The rollback mechanism must prove:

- the previous generation remains addressable;
- APT can deterministically resolve the intended downgrade/restore set;
- package maintainer scripts support the tested transition;
- configuration/state migrations are either reversible or explicitly handled;
- boot/login/session functionality remains valid after rollback;
- rollback cannot silently cross an unsupported Ubuntu platform boundary;
- rollback evidence records both source and destination generations.

This does **not** change Aurora's ext4 baseline.

### 3.5 Filesystem snapshots/Btrfs — DEFER

Btrfs, subvolume layouts, filesystem snapshots and filesystem-level rollback remain deferred until their complete design and failure modes are understood. They are not required to solve package-generation rollback.

### 3.6 Supply-chain provenance and SBOM — ADOPT

Before public release, SupraLINUX release artifacts should gain machine-readable provenance and software bill of materials coverage for at least:

- ISO/recovery images;
- SupraLINUX-owned DEBs;
- KDE override/backport DEBs maintained by SupraLINUX;
- repository-generation manifests.

Where GitHub Actions remains part of the pipeline, GitHub artifact attestations may be used for signed build provenance/SBOM evidence, provided the exact workflow trust model, source revision, reusable workflow boundary and signing identity are documented and qualified.

Provenance does not replace reproducible builds; it records what produced an artifact. Both are required where reproducibility is claimed.

## 4. Integration qualification gates

No gate below starts as a substitute for the currently open KSQ. These become executable product gates only after the KDE stack they target has been qualified sufficiently for downstream evidence to be meaningful.

### AIQ-0 — Runtime surface and dependency contract

Goal: establish the complete user-visible feature inventory for the promoted KDE stack and map every surface to packages/backends/permissions.

PASS requires:

- complete Plasma KCM/widget/service/runtime-surface inventory;
- package/backend mapping for every exposed feature;
- explicit unsupported/hidden surfaces if any;
- no visible function whose required backend is knowingly absent;
- dependency ownership assigned to Ubuntu, SupraLINUX, KDE override, optional hardware, or external service;
- machine-readable regression ownership map from packages to affected AIQ gates.

### AIQ-1 — Clean installation, update and package-generation rollback

Goal: prove a real installed system can enter, update within and leave a repository generation safely.

PASS requires:

- clean install from supported installer path;
- exact repository-generation manifest on the installed system;
- `testing -> stable` promotion path tested where applicable;
- upgrade from previous supported generation;
- rollback to previous supported generation;
- boot, SDDM, Plasma Wayland login, KWallet and core desktop smoke tests after each transition;
- no undeclared third-party repository required;
- no manual package repair steps.

### AIQ-2 — Display, KWin, GPU and laptop graphics

Goal: certify the visible desktop/compositor path across representative hardware.

Minimum matrix:

- Intel iGPU;
- AMD iGPU/dGPU;
- NVIDIA proprietary driver from Ubuntu mechanisms;
- Intel+NVIDIA hybrid;
- AMD+NVIDIA hybrid where supported hardware is available;
- internal laptop panel plus external monitor;
- at least one mixed-DPI multi-monitor configuration.

Required scenarios:

- cold boot/login/logout/relogin;
- hotplug/unplug;
- suspend/resume;
- lid close/open where applicable;
- external display connected through dGPU path where applicable;
- fractional scaling;
- XWayland application compatibility;
- variable refresh rate where hardware supports it;
- screen capture/recording;
- power state battery/AC transitions on laptops.

#### HDR, ICC and mixed-DPI — PROBE

Do not claim HDR/color-management completeness from feature presence alone. Probe and certify SDR+HDR combinations, ICC handling, Night Light interactions, screenshots, screen recording, fullscreen video, VRR and mixed-DPI behavior across available GPU vendors before promotion.

Any KWin, Mesa, NVIDIA driver, kernel DRM, Qt Wayland or color-management change affecting these scenarios triggers AIQ-2 regression.

### AIQ-3 — XDG portals, Flatpak and remote desktop

Goal: make sandboxed application integration and Plasma remote-desktop surfaces work end-to-end.

Required portal coverage includes where applicable:

- FileChooser;
- OpenURI;
- Print;
- Notifications;
- Camera;
- microphone/audio access paths;
- Screenshot;
- ScreenCast;
- RemoteDesktop;
- clipboard/data-transfer paths exposed through the supported portal stack;
- persistent permissions and restoration behavior.

PASS also requires:

- `xdg-desktop-portal` and the correct KDE backend installed and selected;
- Flatpak Discover integration working;
- permission changes reflected correctly;
- sandboxed browser/video-conference screen sharing tested;
- KRDP/related Plasma remote-desktop functionality tested against the same PipeWire/portal stack when shipped;
- no manual backend installation after first boot.

Any change to portal, portal-kde, PipeWire, KWin screen-cast interfaces, Flatpak or remote-desktop packages triggers the mapped AIQ-3 regression.

### AIQ-4 — Audio and Bluetooth

Goal: certify normal desktop audio plus Bluetooth profile policy, not just device discovery.

Required scenarios:

- speakers/headphones/microphone;
- USB audio hotplug;
- HDMI/DisplayPort audio where present;
- Bluetooth pairing, reconnect and removal;
- A2DP playback;
- HFP/HSP call/microphone mode;
- automatic profile switching where supported;
- suspend/resume reconnect;
- simultaneous input/output device switching;
- per-application routing and volume persistence;
- headset hardware volume where supported.

WirePlumber/PipeWire remain Ubuntu-owned infrastructure. Do not replace them merely to obtain a codec/profile feature.

#### LE Audio/BAP/LC3 — PROBE

WirePlumber exposes BAP roles and LC3 support, but SupraLINUX must not claim LE Audio support until controller, kernel/firmware, BlueZ, PipeWire/WirePlumber and real headset behavior are proven together on representative hardware.

Any PipeWire, WirePlumber, BlueZ, kernel Bluetooth, firmware or Plasma audio/Bluetooth integration change triggers AIQ-4 regression.

### AIQ-5 — Networking and VPN

Goal: certify the networking features Plasma exposes through NetworkManager.

Required baseline:

- Ethernet DHCP/static;
- Wi-Fi open/WPA2/WPA3 where hardware supports it;
- hidden network flow;
- captive-portal behavior where practical;
- IPv4/IPv6 connectivity;
- DNS behavior;
- suspend/resume reconnection;
- hotspot/tethering if exposed;
- WireGuard;
- OpenVPN;
- IKEv2/strongSwan;
- OpenConnect for supported enterprise VPN families.

VPN support must include the appropriate NetworkManager plugin, editor integration, secret storage path and connect/disconnect tests. A visible VPN type without its required plugin is incomplete.

#### PPTP — REJECTED AS BASELINE

Do not install or promote PPTP as a SupraLINUX baseline VPN capability. NetworkManager upstream marks the plugin unmaintained and the protocol cryptographically broken.

Unmaintained VPN plugins are not baseline candidates without a separately justified compatibility decision.

Any NetworkManager, Plasma-NM, VPN plugin, KWallet secret integration or DNS/resolver change triggers AIQ-5 regression.

### AIQ-6 — Printing, scanning and OCR

Goal: provide a complete modern document-peripheral path.

#### Printing — ADOPT driverless-first

Prefer IPP Everywhere/AirPrint/Mopria-compatible driverless printing through CUPS for modern printers. Treat legacy PPD/driver paths as compatibility mechanisms, not the architecture for new devices.

PASS requires:

- automatic/network discovery where supported;
- IPP Everywhere printing;
- USB printer path where supported;
- print from native Qt/KDE application;
- print from sandboxed Flatpak through the Print portal;
- duplex/color/media-size options where device supports them;
- job cancel/error path;
- representative legacy printer fallback if Aurora claims such support.

#### Scanning — ADOPT driverless-first

Evaluate `sane-airscan` plus `ipp-usb` as baseline integration for eSCL/AirScan and WSD capable scanners/MFPs, while retaining vendor/backend compatibility only where justified by hardware coverage.

PASS requires:

- network eSCL discovery/scan;
- WSD scan where available;
- USB IPP-over-USB/eSCL path where applicable;
- flatbed and ADF where hardware provides them;
- cancel/error behavior;
- integration with the selected KDE scanning application.

#### OCR language completeness — ADOPT

If a shipped application exposes OCR, the installer language/support policy must install the corresponding OCR language data for every officially supported language where a maintained package exists. SupraLINUX must not expose "Spanish OCR" as an apparent complete feature and then require the user to discover/install `tesseract-ocr-spa` manually.

Installer/language changes affecting OCR trigger AIQ-6 plus localization regression.

### AIQ-7 — Multimedia and codecs

Goal: ensure common user media works immediately without post-install dependency research.

The exact codec/package set must be determined by Ubuntu 26.04 availability, redistribution/license constraints and the selected default applications.

PASS must cover at least:

- common H.264/H.265/AV1/VP9 playback according to legally redistributable baseline;
- AAC/MP3/Opus/Vorbis/FLAC;
- common container formats;
- hardware video decode on representative Intel/AMD/NVIDIA systems where the platform supports it;
- browser playback path;
- KDE media application path;
- thumbnails/previews for supported formats;
- screen recording output playback;
- no hidden dependency on Snap.

Any codec, FFmpeg/GStreamer, browser media integration, Mesa/NVIDIA video acceleration or default media application change triggers AIQ-7 regression.

### AIQ-8 — Firmware, power and suspend

#### fwupd/LVFS — ADOPT

Firmware update capability through fwupd/LVFS should be part of the product baseline when supported by hardware and correctly integrated into Discover or another supported user-facing path.

PASS requires:

- device enumeration;
- metadata refresh;
- update availability presentation;
- update flow on representative supported hardware when safe test hardware exists;
- reboot/offline update path if required;
- error/no-update paths;
- no private signing key exposure in client systems.

#### Power policy — ADOPT Ubuntu platform

Keep Ubuntu's power-profiles-daemon as the power-policy owner and certify Plasma's integration with the profiles available on each machine.

Required scenarios:

- balanced;
- power-saver;
- performance where exposed by hardware/backend;
- battery/AC transition;
- suspend/resume;
- lid behavior;
- idle/screen-off;
- application profile holds where used;
- idle power regression measurements on representative laptops.

#### TLP or parallel default policy managers — REJECTED

Do not install TLP or another competing default power-policy daemon merely to advertise battery tuning. A second policy owner is acceptable only after a measured deficiency is proven, conflicts are understood and an architecture decision qualifies the change.

Any kernel, firmware, power-profiles-daemon, UPower, Plasma PowerDevil or GPU power-policy change triggers AIQ-8 regression.

### AIQ-9 — Accessibility, input and localization

Goal: make accessibility and language features product-complete.

#### Screen reader/accessibility — ADOPT

If Plasma exposes screen-reader support, ship and validate the required supporting stack rather than leaving the user to install it manually. KDE documentation explicitly calls for a screen reader such as Orca, `speech-dispatcher` and a text-to-speech synthesizer.

Required scenarios include:

- screen-reader activation and usable Plasma navigation;
- keyboard-only navigation of core shell and settings;
- sticky/slow/bounce/mouse keys where exposed;
- zoom/magnifier;
- color-blindness correction and relevant visual accessibility controls;
- on-screen/virtual keyboard where part of the supported configuration;
- login/session boundary behavior where applicable.

#### Localization — ADOPT expanded contract

For each officially supported installation language, certify:

- installer language;
- generated locale;
- Plasma/Qt translations;
- locale formats;
- keyboard layout;
- XDG user directories;
- spellchecking/hyphenation resources where baseline apps expose them;
- OCR language resources where OCR is exposed;
- first graphical session has no known partially untranslated state caused by missing packages/setup order.

Any locale/language package, Calamares language module, Plasma translation or XDG-user-dirs change triggers AIQ-9 regression for affected languages.

### AIQ-10 — Diagnostics and crash evidence

#### SupraLINUX diagnostic collector — ADOPT

Create an explicit, local, user-controlled diagnostic collection path. It must gather enough evidence to reproduce integration failures without mandatory telemetry.

Target data includes, with privacy filtering and explicit user control:

- SupraLINUX release and repository generation;
- package manifest for SupraLINUX/KDE overrides;
- kernel and firmware summary;
- GPU/driver/Mesa/NVIDIA state;
- KWin/Wayland session information;
- monitor topology and display properties;
- PipeWire/WirePlumber summary;
- NetworkManager/VPN plugin summary;
- Bluetooth controller/device capability summary;
- fwupd support summary;
- Secure Boot state;
- relevant journal/coredump metadata;
- installer/update/rollback generation identifiers.

The tool must not upload anything automatically.

#### Debug symbols — ADOPT

Retain and index debug symbols/Build-IDs for SupraLINUX-owned binaries and maintained KDE overrides so crashes can be symbolized against the exact released binary generation.

A release is not operationally supportable if its own overridden crashing binary cannot later be identified/symbolized.

### AIQ-11 — Recovery and encryption

Goal: build a recoverable desktop without coupling first release correctness to an unqualified filesystem design.

Near-term work:

- signed/authenticated recovery media and manifests;
- reinstall/factory-reset design;
- preserve-user-data path only when demonstrably safe;
- package-generation rollback independent of filesystem snapshots;
- recovery documentation and failure-mode tests.

#### TPM-backed FDE — DEFER

Do not expose TPM-backed full-disk encryption in the Aurora baseline yet.

Canonical's Ubuntu 26.04 security announcement describes TPM/FDE as general availability/production-ready, while the current Ubuntu Desktop 26.04 how-to and hardware-requirements documentation still explicitly label the feature Beta and document limitations. SupraLINUX also uses Calamares rather than the Ubuntu Desktop installer path that implements the feature.

Promotion therefore requires a separate architecture and installer qualification covering at least:

- Calamares-compatible implementation path;
- TPM/UEFI eligibility checks;
- recovery-key lifecycle;
- PIN/passphrase behavior and keyboard layout;
- firmware-update interaction;
- Secure Boot interaction;
- storage/kernel-module requirements;
- reset/recovery behavior;
- dual-boot policy if ever claimed;
- representative supported hardware matrix.

Traditional qualified LUKS encryption remains the safer path until this gate is resolved.

### AIQ-12 — Release integrity and full-system regression

Goal: prove a candidate repository generation is a releasable product rather than a collection of individually passing subsystems.

PASS requires:

- all applicable AIQ gates PASS on the exact release generation;
- no unresolved critical/high release blocker;
- KDE LTS fix-parity review current;
- clean install, update and rollback current;
- exact Ubuntu snapshot and SupraLINUX generation recorded;
- signed repository metadata;
- ISO/recovery checksums;
- SBOM/provenance present at the maturity level claimed;
- reproducibility evidence complete for SupraLINUX-maintained packages where required;
- diagnostic symbol retention verified;
- release notes and known limitations synchronized with actual state;
- explicit human promotion from `testing` to `stable`.

## 5. Experimental/new functionality policy

The project does not adopt features merely because they exist in the newest Plasma release.

Technology-preview/experimental functionality, including preview theming mechanisms or other features upstream does not present as stable product interfaces, is **REJECTED as an Aurora product baseline** until upstream promotes it and SupraLINUX independently certifies it.

This does not prohibit isolated research.

## 6. GitHub Actions Ubuntu 26.04 policy

As of 2026-09-03 GitHub documents `ubuntu-26.04` hosted runners as **Public preview**.

Decision:

- **PROBE / qualification use allowed** when the experiment specifically needs an Ubuntu 26.04 host and the result records the exact runner image/revision and all relevant builder inputs.
- **NOT accepted as final release infrastructure while GitHub continues to label the runner Public preview.**
- A successful direct-runner `mmdebstrap --mode=unshare --variant=buildd` + `sbuild --chroot-mode=unshare` experiment would prove that build architecture on that host; it would not by itself remove the release-infrastructure maturity gate.
- Do not relax AppArmor, require privileged Docker, add outer `CAP_SYS_ADMIN`, or weaken host security policy simply to force the architecture to pass.

When GitHub promotes `ubuntu-26.04` out of preview, rerun the infrastructure qualification against the then-current runner image before adopting it for release builds.

## 7. Regression ownership map

At minimum, changes in these families automatically trigger the following regressions:

| Change family | Required regression |
|---|---|
| Plasma/KWin/Frameworks/Qt/Wayland integration | KSQ as applicable + AIQ-0/1/2 and all feature gates touched by changed packages |
| Mesa/libdrm/kernel DRM/NVIDIA driver | AIQ-2, AIQ-7 hardware decode where relevant, AIQ-8 laptop/power where relevant |
| xdg-desktop-portal / portal-kde / Flatpak | AIQ-3 plus AIQ-6 print portal if changed |
| PipeWire/WirePlumber/BlueZ | AIQ-4, AIQ-3 screen-share/remote-desktop audio paths where relevant |
| NetworkManager/Plasma-NM/VPN plugin | AIQ-5 |
| CUPS/printing stack | AIQ-6 + AIQ-3 sandboxed printing |
| SANE/sane-airscan/ipp-usb | AIQ-6 |
| Tesseract/language resource mapping | AIQ-6 + AIQ-9 affected languages |
| FFmpeg/GStreamer/codecs/browser media integration | AIQ-7 |
| fwupd/firmware integration | AIQ-8 and AIQ-11 if recovery/encryption interaction changes |
| power-profiles-daemon/UPower/PowerDevil | AIQ-8 |
| Calamares/locale/language packages | AIQ-1 + AIQ-9; AIQ-6 when OCR mapping changes |
| APT/repository generation/update policy | AIQ-1 + AIQ-12 |
| recovery/encryption/bootloader/Secure Boot path | AIQ-11 + AIQ-1 boot/install + AIQ-12 |
| diagnostic collector/dbgsym publication | AIQ-10 + AIQ-12 evidence checks |

A PASS may be reused only when the changed input is proven irrelevant to that gate, not merely because package versions look similar.

## 8. Execution order

Current order of work:

1. **Finish KDE Stack Qualification.** KSQ-1 remains the active build/reproducibility gate; do not mix AIQ implementation into it.
2. AIQ-0 runtime/dependency surface reconciliation.
3. AIQ-1 installation/update/package-generation rollback.
4. AIQ-2 display/GPU/hybrid/HDR-color qualification.
5. AIQ-3 portals/Flatpak/remote desktop.
6. AIQ-4 audio/Bluetooth.
7. AIQ-5 networking/VPN.
8. AIQ-6 printing/scanning/OCR.
9. AIQ-7 multimedia/codecs.
10. AIQ-8 firmware/power/suspend.
11. AIQ-9 accessibility/input/localization.
12. AIQ-10 diagnostics/debug evidence.
13. AIQ-11 recovery/encryption.
14. AIQ-12 supply-chain/release-integrity full-system acceptance.

Supply-chain implementation may be developed earlier where it does not invalidate an open qualification, but AIQ-12 is the final release gate.

## 9. Source basis checked 2026-09-03

Primary/current upstream and platform references used for this roadmap:

- KDE announcements, current stable releases: https://kde.org/announcements/
- KDE Plasma 6.7.4: https://kde.org/announcements/plasma/6/6.7.4/
- KDE Frameworks 6.29.0: https://kde.org/announcements/frameworks/6/6.29.0/
- Ubuntu Snapshot Service: https://snapshot.ubuntu.com/
- GitHub-hosted runners: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- GitHub artifact attestations: https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations
- XDG Desktop Portal documentation: https://flatpak.github.io/xdg-desktop-portal/docs/
- WirePlumber Bluetooth configuration: https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/bluetooth.html
- NetworkManager VPN support: https://networkmanager.dev/docs/vpn/
- OpenPrinting CUPS driver/driverless direction: https://openprinting.github.io/cups/drivers.html
- sane-airscan upstream: https://github.com/alexpevzner/sane-airscan
- LVFS/fwupd: https://fwupd.org/
- power-profiles-daemon D-Bus API: https://upower.pages.freedesktop.org/power-profiles-daemon/gdbus-org.freedesktop.UPower.PowerProfiles.html
- KDE Plasma accessibility documentation: https://docs.kde.org/stable_kf6/en/plasma-desktop/kcontrol/kcmaccess/index.html
- Ubuntu 26.04 security announcement: https://ubuntu.com/blog/ubuntu-26-04-lts-security-updates
- Ubuntu Desktop 26.04 TPM/FDE how-to: https://documentation.ubuntu.com/desktop/en/26.04/how-to/encrypt-your-disk-with-tpm/
- Ubuntu Desktop 26.04 TPM/FDE requirements: https://documentation.ubuntu.com/desktop/en/26.04/reference/hardware-backed-disk-encryption-requirements/

These references establish direction and platform capability. Package inclusion and final product support remain subject to exact Ubuntu 26.04 package metadata, redistribution/license review, dependency closure and the relevant qualification gate.

## 10. Non-goals of this roadmap

This roadmap does not authorize:

- replacing Ubuntu infrastructure simply to chase a newer KDE release;
- manual post-install repair instructions for advertised baseline features;
- unqualified experimental Plasma features;
- mandatory telemetry;
- Btrfs/filesystem snapshots as a prerequisite for Aurora;
- PPTP as a default supported VPN;
- TLP as a competing default power-policy owner;
- TPM-backed FDE before a SupraLINUX-specific qualification;
- final release builds on a GitHub runner still officially marked Public preview;
- weakening AppArmor/host security merely to make CI pass.

The objective is not the largest feature list. It is a desktop where the features SupraLINUX chooses to expose are current-stable, complete, diagnosable, recoverable and demonstrably functional.
