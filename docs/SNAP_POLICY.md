# SupraLINUX Snap Policy — Aurora

Status: **implemented and validated in development; release freeze remains pending normal release-gate review**.

SupraLINUX does not install Snap by default and blocks Snap by default. The block is explicit, reversible and owned by a package rather than by ISO-only shell edits. Removing the block does not itself install Snap.

## Goals

1. A fresh SupraLINUX installation must not contain `snapd`.
2. APT must not silently install `snapd` through transitional/recommended packages while the block is active.
3. Plasma/Discover must not pull the Snap backend while the block is active.
4. The user must be able to remove the block later without reinstalling the operating system.
5. Removing the block means only “APT may install Snap”; it does not install `snapd` or any Snap package by itself.

## Current implementation

The policy package is:

```text
supralinux-snap-policy
```

It owns an APT preferences file containing version pins for:

```text
snapd
plasma-discover-backend-snap
```

with negative priority while the policy package is installed.

The current implementation intentionally pins by package/version match rather than depending on a specific archive origin, so an additional APT source cannot silently bypass the default policy merely by publishing the same package names.

Canonical package source:

```text
packages/supralinux-snap-policy/
```

Canonical policy file:

```text
packages/supralinux-snap-policy/files/supralinux-no-snap.pref
```

## Reversibility

Removing `supralinux-snap-policy` removes the policy file through normal dpkg package ownership. It does not install `snapd`, enable a Snap service or perform unrelated state changes.

After the policy is removed, the system returns to ordinary APT candidate resolution for packages such as `snapd`.

A future SupraLINUX UI may expose an explicit user action to remove/disable this policy through a privileged documented mechanism. That UI does not exist yet and is not required for the current Plasma integration gate.

## Discover interaction

Ubuntu 26.04's `plasma-discover` recommends `plasma-discover-backend-snap`. Because APT normally installs recommendations, this resolver path is part of the Snap policy contract.

Development CI already verifies that, with the policy active, Discover can be resolved/installed without pulling:

- `plasma-discover-backend-snap`;
- `snapd`.

This resolver result does not make Discover part of the hard `supralinux-desktop` baseline. Its final product role remains a later application/software-management decision.

## Validation state

The policy has been exercised by the package-resolution and clean-system gates and retained through the accepted boot/session composition.

Current validated development properties include:

- policy package installs normally;
- APT has no installable candidate for blocked Snap components while the policy is active;
- clean Aurora composition contains no `snapd`;
- clean Aurora composition contains no `plasma-discover-backend-snap`;
- Discover resolver simulation does not bypass the policy;
- the policy remains installed/active through the certified C1-C3 system state.

The exact historical evidence is preserved by the corresponding CI/rootfs/boot artifacts and acceptance records.

## Non-goals

- Do not patch APT.
- Do not replace Ubuntu's package manager.
- Do not delete Snap files behind the user's back.
- Do not continually remove Snap after a user has explicitly opted in.
- Do not make policy removal install Snap automatically.
- Do not add Discover to the hard desktop baseline merely because its Snap interaction is now resolver-safe.

## Regression triggers

The Snap policy must be re-tested when changes affect:

- `supralinux-snap-policy` contents or package ownership;
- APT pin semantics used by the package;
- the package names Ubuntu uses for Snap/Discover integration;
- the hard desktop/software-management dependency set;
- Ubuntu package metadata in a way that introduces a new Snap dependency/recommendation path relevant to Aurora.

Ordinary C4 feature-harness work does not by itself reopen the Snap policy.

## Release gate

The implementation is no longer pending. The remaining work is release-level regression/review: before Aurora is promoted, current Ubuntu 26.04 package metadata must still demonstrate that supported installation/update paths cannot silently bypass the policy and that opt-out remains reversible.
