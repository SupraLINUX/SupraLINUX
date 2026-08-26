# SupraLINUX CI — Aurora package validation

The first CI gate validates packaging and APT dependency resolution on the same Ubuntu generation used by Aurora.

## Runner

The workflow uses GitHub's `ubuntu-26.04` x64 runner. As of August 2026 this runner image is in public preview, so the workflow explicitly verifies `VERSION_CODENAME=resolute` before doing any project work.

## Current workflow

`.github/workflows/package-validation.yml`

It currently runs only:

- manually through `workflow_dispatch`; or
- on a pull request targeting `main` when packaging/CI files changed.

It does **not** run on every development commit. This is deliberate while the repository is private so CI minutes are not consumed by every small audit/edit.

## What it proves

1. the package sources build into DEB packages on Ubuntu 26.04;
2. the runner is actually amd64 Resolute;
3. `supralinux-snap-policy`, `supralinux-base` and `supralinux-desktop` can be presented to APT together without unresolved package names/dependencies;
4. the SupraLINUX Snap policy removes installable APT candidates for `snapd` and `plasma-discover-backend-snap` in a fresh APT state;
5. resolving Plasma Discover under the policy must not pull the Snap backend.

## What it does NOT prove

This gate is intentionally not called a desktop test. It does not prove:

- Plasma boots;
- SDDM works;
- a Wayland session starts;
- audio/network/Bluetooth work;
- KRDP works;
- locale/XDG first-login behavior is correct;
- suspend/resume works;
- hardware-specific integrations work.

Those require the next clean-system/VM validation layer.

## Storage policy

The workflow does not upload GitHub Actions artifacts. DEBs exist only inside the ephemeral runner for the duration of the validation job. This avoids using artifact storage for routine development validation.

When release/test packages need persistent distribution, they belong in the SupraLINUX APT repository rather than GitHub Actions artifact storage.
