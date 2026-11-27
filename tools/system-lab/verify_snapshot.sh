#!/usr/bin/env bash
# S03: inside a digest-pinned disposable Arch builder, never install packages.
set -euo pipefail
export LC_ALL=C
umask 077
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
keyring="$work/gnupg"
mkdir -m 700 "$keyring"
pacman-key --gpgdir "$keyring" --init
pacman-key --gpgdir "$keyring" --populate archlinux
pacman -Q archlinux-keyring > "$work/verification-keyring.txt"
gpg --version > "$work/verification-gpg.txt"
# Publish only non-secret metadata, readable by the unprivileged CI runner.
install -m 0644 "$work/verification-keyring.txt" /out/verification-keyring.txt
install -m 0644 "$work/verification-gpg.txt" /out/verification-gpg.txt
source /snapshot_download.sh
report="$work/verified.tsv"
count=0
while IFS=$'\t' read -r name hash url; do
    [[ "$name" =~ ^[a-z0-9][a-z0-9+_.@-]*$ ]]
    [[ "$hash" =~ ^[0-9a-f]{64}$ ]]
    [[ "$url" =~ ^https://archive\.archlinux\.org/repos/[0-9]{4}/[0-9]{2}/[0-9]{2}/(core|extra)/os/x86_64/[A-Za-z0-9+_.@:-]+\.pkg\.tar\.(zst|xz)$ ]]
    printf 'Verifying package %s (index %s)\n' "$name" "$((count+1))"
    download "$url" "$work/package"
    printf '%s  %s\n' "$hash" "$work/package" | sha256sum --check --strict
    download "$url.sig" "$work/package.sig"
    # A good signature alone is insufficient; require the Arch web of trust.
    gpg --homedir "$keyring" --batch --no-auto-key-retrieve --status-fd 1 \
        --verify "$work/package.sig" "$work/package" > "$work/status"
    if grep -Eq '^\[GNUPG:\] (BADSIG|ERRSIG|EXPSIG|EXPKEYSIG|REVKEYSIG|KEYEXPIRED|SIGEXPIRED|KEYREVOKED|NO_PUBKEY|TRUST_NEVER|TRUST_UNDEFINED|TRUST_MARGINAL)( |$)' "$work/status"; then
        echo "Rejected signature status for $name" >&2
        exit 1
    fi
    grep -Eq '^\[GNUPG:\] TRUST_(FULLY|ULTIMATE)( |$)' "$work/status"
    signer=$(awk '$1=="[GNUPG:]" && $2=="VALIDSIG" {print $3}' "$work/status")
    [[ "$signer" =~ ^[A-F0-9]{40,64}$ ]]
    printf '%s\t%s\t%s\n' "$name" "$hash" "$signer" >> "$report"
    # Optional private cache for S04. Never publish package payloads as evidence.
    if [[ -d /packages ]]; then
        filename=${url##*/}
        install -m 0644 "$work/package" "/packages/$filename"
        install -m 0644 "$work/package.sig" "/packages/$filename.sig"
    fi
    count=$((count+1))
    rm -f "$work/package" "$work/package.sig" "$work/status"
done < /out/verification-input.tsv
(( count > 0 ))
install -m 0644 "$report" /out/verified-packages.tsv
printf 'Verified %s package hashes and trusted detached signatures\n' "$count"
