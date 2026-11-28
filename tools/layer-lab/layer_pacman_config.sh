#!/usr/bin/env bash
# Configuration for the disposable offline layer transaction.
# HookDir is interpreted relative to the pacman process, not RootDir.
write_layer_pacman_config() {
    local root=$1 config=$2
    [[ "$root" = /* && "$root" != / && -d "$root" ]] || return 1
    mkdir -p "$root/etc/pacman.d/hooks" || return 1
    cat > "$config" <<CONF
[options]
Architecture = x86_64
SigLevel = Required
LocalFileSigLevel = Required
HookDir = $root/etc/pacman.d/hooks
CONF
}
