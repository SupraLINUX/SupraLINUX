#!/usr/bin/env bash
# Source-only transport helper. Authentication of content belongs to verify_snapshot.sh.
download() {
    local url=$1 destination=$2 part status rc attempt
    local -a protocol=()
    for attempt in 1 2 3; do
        part=$(mktemp "${destination}.part.XXXXXX") || return 1
        if status=$(curl --fail --silent --show-error --location \
            --proto '=https' --proto-redir '=https' --connect-timeout 30 \
            --max-time 300 --write-out '%{http_code}' \
            "${protocol[@]}" --output "$part" "$url"); then
            if mv -f -- "$part" "$destination"; then
                return 0
            fi
            rm -f -- "$part"
            return 1
        else
            rc=$?
        fi
        rm -f -- "$part" || return 1
        printf 'Download attempt %s/3 failed: %s curl=%s http=%s\n' \
            "$attempt" "${url##*/}" "$rc" "$status" >&2
        case "$rc" in
            92) protocol=(--http1.1) ;;
            5|6|7|18|28|52|55|56) ;;
            22)
                case "$status" in
                    408|429|500|502|503|504) ;;
                    *) return "$rc" ;;
                esac ;;
            *) return "$rc" ;;
        esac
        if (( attempt == 3 )); then
            return "$rc"
        fi
        sleep "$attempt"
    done
}
