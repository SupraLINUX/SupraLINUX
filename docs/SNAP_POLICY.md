# SupraLINUX Snap Policy — Aurora

Status: **design accepted at product level; package implementation pending**.

SupraLINUX does not install Snap by default and blocks Snap by default. The block must be explicit, reversible and understandable. Removing the block must not itself install Snap.

## Goals

1. A fresh SupraLINUX installation must not contain `snapd`.
2. APT must not silently install `snapd` through transitional/recommended packages while the block is active.
3. Plasma/Discover must not pull the Snap backend while the block is active.
4. The user must be able to remove the block later without reinstalling the operating system.
5. Removing the block means only “APT may install Snap”; it does not install `snapd` or any Snap package by itself.

## Proposed implementation

Create a small policy package, tentatively named:

```text
supralinux-snap-policy
```

The package should own the default block rather than scattering shell commands through the ISO build.

### APT policy

The preferred mechanism is an APT preferences file owned by the package, for example:

```text
/etc/apt/preferences.d/supralinux-no-snap
```

The policy must at minimum prevent automatic installation of:

- `snapd`
- `plasma-discover-backend-snap`

The exact pin values and package set must be validated with APT resolver tests before release.

### User opt-out

A future SupraLINUX settings UI can offer an explicit action such as:

```text
Allow Snap packages
```

That action should remove/disable the SupraLINUX Snap policy package or its policy file through a privileged, documented mechanism. It must not run `apt install snapd`.

After the policy is removed, the user is back to ordinary Ubuntu APT behavior. If they later install `snapd` or a package that legitimately depends on it, APT may proceed normally.

## Discover interaction

Ubuntu 26.04's `plasma-discover` package recommends `plasma-discover-backend-snap`. Because APT installs recommendations by default, SupraLINUX must not add Discover to the baseline until this policy has been tested against that exact resolver path.

Acceptance test:

```text
SupraLINUX Snap policy installed
+
apt install plasma-discover
=
Discover installs successfully
AND plasma-discover-backend-snap is not installed
AND snapd is not installed
```

A second acceptance test must prove reversibility:

```text
remove/disable SupraLINUX Snap policy
+
apt install snapd
=
succeeds normally
```

## Non-goals

- Do not patch APT.
- Do not replace Ubuntu's package manager.
- Do not delete Snap files behind the user's back.
- Do not continually remove Snap after the user has explicitly opted in.
- Do not make packages fail with misleading errors when a clear APT policy explanation can be provided.

## Release gate

Snap blocking is a release-level policy. Aurora must not be declared ready until automated resolver tests prove that common Ubuntu transitional/recommended paths cannot silently bypass it.
