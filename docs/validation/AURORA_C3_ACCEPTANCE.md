# Aurora C3 Acceptance Record

Status: **ACCEPTED / GREEN**

This record permanently captures the evidence used to accept the Aurora C3 real Plasma Wayland user-session gate. The raw GitHub Actions artifact is intentionally temporary; the tested source commit, workflow attempt, artifact identifiers, marker counts, and SHA-256 hashes below make the accepted evidence traceable after artifact expiry.

## Accepted source state

- Repository: `SupraLINUX/SupraLINUX`
- Branch under test: `development`
- Technical source commit: `7b9ea6ae47f181eff838a7a4e555e30eff096467`
- Commit message: `ci: verify first-login Look-and-Feel defaults state`
- C3 workflow run: `33103929801`
- Accepted workflow attempt: `2`
- Accepted C3 job: `98631447422` (`Boot a real Plasma Wayland user session`)
- Workflow conclusion: `success`

The accepted attempt used the exact same technical source commit as attempt 1. Attempt 1 failed during `debootstrap` before the guest VM booted because a single Ubuntu mirror package download (`liblz4-1`) failed. Re-running the same commit succeeded past the same bootstrap point and completed C3 without source changes, isolating that first result as an external/transient download failure rather than an Aurora runtime failure.

## Persistent runtime evidence

GitHub Actions artifact from accepted attempt 2:

- Name: `aurora-c3-session-diagnostics-33103929801-2`
- Artifact ID: `9660144002`
- Artifact size reported by GitHub: `144094` bytes
- Artifact digest reported by GitHub: `sha256:7a90c706838431de171eb2d0f39e10853f2177f7a7c4cff2a3487960b539795d`
- Artifact created: `2026-08-27T18:47:26Z`

The downloaded ZIP independently hashed to the exact same SHA-256 value before extraction.

All five files present in the accepted artifact were read in full before acceptance. The physical line counts below are newline counts from the stored files; serial/status carriage returns may produce more logical lines when split for analysis.

| File | Bytes | Physical lines | SHA-256 |
| --- | ---: | ---: | --- |
| `aurora-c3-serial.log` | 84,486 | 1,080 | `a249ef652a8c67e93455a0d86cd8479ebdcff072a9484fa4161739fc4fb2ede7` |
| `aurora-c3-wayland-session.log` | 297 | 5 | `6110a2028088853d49af92da96d75aad7bd20fd65aac8bc1d05a7d2fbf5c22e7` |
| `c3-validation.log` | 754,509 | 10,300 | `af2d22f6f22f8f579f54db79d8d112de514032da6ed600430e5b6eacd205fd60` |
| `debootstrap.log` | 15,037 | 442 | `6c1eef7ef6fb226f4f07b02bb4de8c85af27a3400801aa846f657f8f6b421145` |
| `rootfs-discover-simulation.log` | 278 | 7 | `25be157344b48fdd0d93e635c15c42aed7ffcb073d43f82360306692c56558e5` |

No decoding replacement characters or NUL bytes were present in the reviewed text logs.

## Deterministic guest evidence

The accepted serial console contains exactly one of every required C3 stage marker:

- `SYSTEM`
- `LOGIN`
- `WAYLAND`
- `USER_DBUS`
- `GRAPHICAL_SESSION`
- `KWIN`
- `PLASMASHELL`
- `PLASMA_TARGETS`
- `LOOKANDFEEL_DEFAULTS`
- `XRESOURCES`
- `PIPEWIRE`
- `WIREPLUMBER`
- `POLKIT`
- `PORTAL`
- `XWAYLAND`
- `STABILITY`
- `COMPLETE`

It also contains exactly:

- `1 × AURORA_C3_CHECK_START`
- `1 × AURORA_C3_LOOKANDFEEL_DEFAULTS_SUCCESS`
- `1 × AURORA_C3_XRESOURCES_SUCCESS`
- `1 × AURORA_C3_XWAYLAND_TEST_START`
- `1 × AURORA_C3_XWAYLAND_SUCCESS`
- `1 × AURORA_C3_SUCCESS`
- `0 × AURORA_C3_FAILURE:`

The host harness independently rejects the run unless the final success marker, Look-and-Feel marker, Xresources marker, XWayland marker, and every required stage occur exactly once.

## Runtime assertions proven before success

The accepted C3 probe can emit `AURORA_C3_SUCCESS` only after all of the following assertions succeed:

- PID 1 is systemd;
- `graphical.target` and `multi-user.target` are active;
- emergency and rescue targets are inactive;
- `/` is mounted read/write;
- `apt-get check` succeeds after boot;
- the required SupraLINUX, Plasma, Wayland, XWayland, SDDM, portal, PipeWire/WirePlumber, Polkit and System Settings packages are installed;
- Snap remains absent/blocked and the Plasma X11 session remains absent;
- the disposable `auroraci` user obtains an active, local login session;
- the login session reports `Type=wayland`;
- the user D-Bus is usable;
- `graphical-session.target` becomes active through the normal session path;
- `kwin_wayland` and `plasmashell` are running;
- the real `plasmashell` environment contains `XDG_SESSION_TYPE=wayland` and `LANG=C.UTF-8`;
- `WAYLAND_DISPLAY`, its socket, `DISPLAY`, `XAUTHORITY`, and the Xauthority file are valid in the Plasma session;
- `plasma-workspace-wayland.target`, `plasma-workspace.target`, and `plasma-plasmashell.service` are active;
- Plasma persists `~/.config/kdedefaults/package` and its contents exactly match the configured `LookAndFeelPackage`;
- `xrdb -query` succeeds against the live XWayland display and exposes a numeric `Xft.dpi` resource;
- `pipewire.service` starts and becomes active;
- `wireplumber.service` starts and becomes active;
- `plasma-polkit-agent.service` starts and becomes active;
- both `org.freedesktop.portal.Desktop` and the KDE portal backend can be D-Bus activated and register their expected user-bus names;
- the already-installed `systemsettings` process remains running when explicitly forced to `QT_QPA_PLATFORM=xcb` inside the Wayland session;
- that X11 test process inherits the Plasma Xauthority file and a live XWayland process is present;
- the original KWin and plasmashell PIDs remain alive and unchanged through the final stability interval, proving no immediate restart loop.

The guest then emits `AURORA_C3_SUCCESS` and deliberately powers off. The serial log ends in a normal power-down path.

## Full-log warning classification

The complete accepted artifact was reviewed for `failed`, `error`, `warning`, `fatal`, panic, segfault, core-dump, OOM, rescue/emergency, timeout, missing-file, and related failure indicators. No C3 runtime failure marker, crash, OOM, emergency/rescue activation, or KWin/plasmashell restart was found.

### Rootfs-composition messages

The large `c3-validation.log` contains expected package-maintainer-script messages while building the filesystem in a chroot rather than in a booted system:

- repeated `invoke-rc.d: could not determine current runlevel` paired with `policy-rc.d denied execution ...`;
- NetworkManager unable to connect/reload because the system bus is not running inside the composition chroot;
- a PackageKit/system-bus connection failure for the same reason;
- one post-install command reporting that systemd is not PID 1 inside the chroot;
- `update-rc.d` compatibility warnings from Plymouth;
- a `dpkg-statoverride` warning while Chrony is being installed before its runtime log directory exists;
- NetworkManager's first unpack observing that `/etc/NetworkManager/system-connections` does not yet exist.

These occur before `==> Booting Aurora C3 VM`. The composition harness intentionally installs `policy-rc.d` so package scripts cannot start host-facing services during chroot installation. Package installation completes, `apt-get check` succeeds, and the resulting real guest subsequently boots and passes the runtime assertions.

References to `rescue.target.wants` and `emergency.target.wants` in the composition log are symlink creation by `grub-initrd-fallback`; they are not evidence that either target became active. The guest probe explicitly rejects active rescue/emergency targets before proceeding.

### First-login Plasma session messages

`aurora-c3-wayland-session.log` contains five startup diagnostics:

- the initial read of `~/.config/kdedefaults/package` before that first-login state file exists;
- `/usr/bin/xrdb: Can't open display ''`;
- `xcb_connect() failed`;
- two `QPixmap: QGuiApplication must be created before calling defaultDepth()` messages.

These are not hidden or discarded. They occur during the asynchronous first-login startup sequence before the C3 readiness probe completes. The accepted source was deliberately hardened so acceptance depends on observing the resulting live state rather than assuming these messages are harmless:

- `LOOKANDFEEL_DEFAULTS` proves Plasma subsequently creates and persists the expected Look-and-Feel state;
- `XRESOURCES` proves `xrdb` can subsequently query the live XWayland resource database and that `Xft.dpi` exists;
- `XWAYLAND` proves a real Qt/XCB `systemsettings` process stays alive through XWayland with the correct Xauthority;
- `STABILITY` proves KWin and plasmashell do not crash or restart during the probe.

The two QPixmap diagnostics are consistent with a startup helper querying `QPixmap::defaultDepth()` before a `QGuiApplication` exists; they are not accompanied by a fatal Qt error or process/session failure, and the subsequent GUI/session assertions pass.

### VM/kernel and shutdown observations

The serial console reports speculative-execution vulnerability/microcode warnings and unavailable PMU hardware from the virtualized CPU. These describe the KVM virtual CPU/host microcode exposure, not a missing Aurora desktop component.

After `AURORA_C3_SUCCESS`, during the deliberate poweroff transaction, systemd logs one `rfkill` device job that cannot be enqueued because `systemd-poweroff.service` already has a conflicting shutdown transaction. It occurs after every C3 assertion and success marker and does not invalidate the running-session evidence.

## Scope of acceptance

Aurora C3 proves that the package-defined Ubuntu 26.04 / Plasma baseline can boot into a real disposable **Plasma Wayland user session** and sustain the core session plumbing required by the C3 definition, including portals, PipeWire/WirePlumber service readiness, the Plasma Polkit agent, first-login Look-and-Feel state, Xresources state, and XWayland application compatibility.

C3 does **not** certify every desktop feature end-to-end, real-hardware GPU compatibility, audio playback/recording, Bluetooth pairing, printing, network configuration UX, screen sharing, KRDP, suspend/resume, or the complete KCM matrix. Those belong to C4 and later hardware/manual gates.

## Verdict

Aurora C3 is formally accepted as **GREEN** for the defined C3 scope.

C4 is now unblocked. Feature-level integration must still be validated individually; C3 success must not be used to mark those later checks complete.