# Aurora C1 Acceptance Record

Status: **GREEN**

This record permanently captures the evidence used to accept the Aurora C1 kernel + systemd boot gate. The raw GitHub Actions artifact is intentionally temporary; the source commit, artifact identifiers, marker counts, and SHA-256 hashes below make the accepted evidence traceable after artifact expiry.

## Accepted source

- Repository: `SupraLINUX/SupraLINUX`
- Branch at validation: `development`
- Source commit: `28f3919746545fff957b6cee085b9c38f3f80279`
- Commit message: `ci: avoid pipefail false negatives in C1 probe`
- Workflow run: `32991483642`
- Job: `98249819703` (`Aurora C1 boot validation`)
- Workflow conclusion: `success`
- Evidence artifact: `aurora-c1-boot-diagnostics`
- Artifact ID: `9615014958`
- Artifact digest reported by GitHub: `sha256:c9f9d1505f35a4d705276ca6f04427ee5839cd7bacf2ca266fe4d653ef0b440b`
- Artifact created: `2026-08-26T17:05:44Z`

## Complete artifact inventory reviewed

All files present in the artifact were read in full before acceptance.

| File | Bytes | Physical lines | SHA-256 |
| --- | ---: | ---: | --- |
| `aurora-c1-serial.log` | 77,626 | 991 | `424fe7ff9f1c7641a547b722ac5d356181890b7a09cda9a041a691d65b38dd22` |
| `c1-validation.log` | 737,585 | 10,204 | `e30d6c67cebfae7b0d48c1cfa24c6b83fa0581a365379fd4532c9eecb53a4b56` |
| `debootstrap.log` | 15,031 | 442 | `2fae459bd5957fe42032b4674909c909c5a3ae922339a85d387f70021fbb59fc` |
| `rootfs-discover-simulation.log` | 278 | 7 | `25be157344b48fdd0d93e635c15c42aed7ffcb073d43f82360306692c56558e5` |

The serial stream contains carriage-return status updates, so logical line splitting can produce a larger count than `wc -l`; the physical line counts above are the newline counts from the stored files.

## Runtime acceptance evidence

The serial console contains:

- exactly one `AURORA_C1_CHECK_START`;
- exactly one `AURORA_C1_SUCCESS`;
- zero `AURORA_C1_FAILURE` markers;
- `Reached target multi-user.target - Multi-User System.`;
- `aurora-ci-c1-check.service: Deactivated successfully.`;
- a clean systemd shutdown ending in `reboot: Power down`.

The C1 guest probe represented by the accepted source commit verifies, before emitting the success marker:

- PID 1 is systemd;
- `multi-user.target` is active;
- neither emergency nor rescue target is active;
- `/` is mounted read/write;
- `apt-get check` succeeds after boot;
- `supralinux-snap-policy`, `supralinux-base`, `supralinux-desktop`, Plasma, the Wayland session, KWin Wayland and SDDM are installed;
- `snapd` and `plasma-discover-backend-snap` are absent/non-installable through APT while the policy is active;
- `display-manager.service` is configured and resolves to `sddm.service`.

The host harness independently requires the success marker and rejects a serial log containing `AURORA_C1_FAILURE:`.

## Non-blocking observations

The reviewed logs include expected/non-C1-blocking warnings from the chroot/VM environment, including NetworkManager/system-bus warnings during rootfs composition and a speculative return stack overflow warning from the virtualized CPU. During the clean shutdown, `dmesg.service` reports `Failed with result 'signal'`; this occurs after the C1 probe has completed successfully and the machine is powering off. None of these observations contradicts the C1 acceptance criteria.

## Verdict

Aurora C1 is formally accepted as **GREEN**. This does not imply that SDDM reaches a usable graphical greeter or that a Plasma Wayland user session starts; those are later boot-validation stages.
