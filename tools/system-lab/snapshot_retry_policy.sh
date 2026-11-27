#!/usr/bin/env bash
# Source-only resolver retry policy. No retry for early unexplained SIGKILL.
resolver_retryable() {
    local status=$1 elapsed=$2 log=$3
    # GNU timeout may return 137 after SIGKILL; elapsed time corroborates the
    # 240-second deadline, but is not proof of why a process was killed.
    if (( status == 124 || (status == 137 && elapsed >= 240) )); then
        return 0
    fi
    grep -Eqi 'connection timed out|operation timed out|operation too slow|could not resolve host|failed to connect|connection reset|HTTP.*(502|503|504)|requested URL returned error: (502|503|504)' "$log"
}
