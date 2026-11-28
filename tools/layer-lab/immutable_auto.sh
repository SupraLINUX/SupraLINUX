#!/usr/bin/env bash
# Laboratory-only systemd health dependency and observer; no native bless CLI
# mutation here. Normal generator is responsible for starting the native unit.
immutable_auto_units() {
    local root=$1 dir="$1/etc/systemd/system"
    mkdir -p "$dir/boot-complete.target.d" "$dir/systemd-bless-boot.service.d" "$dir/multi-user.target.wants"
    cat > "$dir/supra-lab-health.service" <<'UNIT'
[Unit]
Description=Supra disposable immutable deployment health check
DefaultDependencies=no
After=multi-user.target
Before=boot-complete.target
ConditionKernelCommandLine=supra_immutable_auto_bless=1

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/libexec/supra-immutable-boot
StandardOutput=journal+console
StandardError=journal+console
TimeoutStartSec=120
UNIT
    cat > "$dir/boot-complete.target.d/50-supra-lab-health.conf" <<'UNIT'
[Unit]
Requires=supra-lab-health.service
After=supra-lab-health.service
UNIT
    cat > "$dir/systemd-bless-boot.service.d/50-supra-lab-esp.conf" <<'UNIT'
[Service]
Environment=SYSTEMD_ESP_PATH=/run/supra-auto-esp
UNIT
    ln -s ../supra-lab-health.service "$dir/multi-user.target.wants/supra-lab-health.service"
    test -f "$root/usr/lib/systemd/system/systemd-bless-boot.service"
}

immutable_auto_observe() {
    local health=supra-lab-health.service native=systemd-bless-boot.service state status i
    local esp=/run/supra-auto-esp
    local count=/sys/firmware/efi/efivars/LoaderBootCountPath-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f
    test "$(cat /etc/supra-lab-deployment)" = layer
    for ((i=0;i<120;i++)); do
        state=$(systemctl show -p ActiveState --value "$health")
        if [[ "$state" = active || "$state" = failed ]]; then break; fi
        sleep 1
    done
    test "$(findmnt -n -o SOURCE --mountpoint "$esp")" = /dev/vda1
    export SYSTEMD_ESP_PATH="$esp"
    if grep -qw supra_immutable_reject=1 /proc/cmdline; then
        test "$state" = failed
        test "$(systemctl show -p ExecMainStatus --value "$health")" = 23
        # Allow the dependency transaction to settle before asserting that
        # neither boot-complete nor its consumer was reached.
        for ((i=0;i<30;i++)); do
            if ! systemctl list-jobs --no-legend --plain --no-pager | grep -E 'boot-complete.target|systemd-bless-boot.service'; then break; fi
            sleep 1
        done
        test "$i" -lt 30
        if systemctl is-active --quiet boot-complete.target; then return 1; fi
        test "$(systemctl show -p ExecMainStartTimestampMonotonic --value "$native")" = 0
        test "$(/usr/lib/systemd/systemd-bless-boot status)" = indeterminate
        test -f "$esp/loader/entries/supra-immutable-layer+0-1.conf"
        test ! -e "$esp/loader/entries/supra-immutable-layer.conf"
        printf '%s\n' SUPRA_AUTO_BLESS_BLOCKED > /dev/ttyS0
    else
        test "$state" = active
        if [[ -e "$count" ]]; then
            for ((i=0;i<30;i++)); do
                status=$(/usr/lib/systemd/systemd-bless-boot status)
                if [[ "$status" = good ]]; then break; fi
                sleep 1
            done
            test "$status" = good
            systemctl is-active --quiet boot-complete.target
            test "$(systemctl show -p Result --value "$native")" = success
            test "$(systemctl show -p ExecMainStatus --value "$native")" = 0
            test "$(systemctl show -p ExecMainStartTimestampMonotonic --value "$native")" -gt 0
            printf '%s\n' SUPRA_AUTO_BLESS_NATIVE_GOOD > /dev/ttyS0
        else
            test "$(/usr/lib/systemd/systemd-bless-boot status)" = clean
            printf '%s\n' SUPRA_AUTO_BLESS_PERSISTED > /dev/ttyS0
        fi
        test -f "$esp/loader/entries/supra-immutable-layer.conf"
        test ! -e "$esp/loader/entries/supra-immutable-layer+1-1.conf"
    fi
    sync
    umount "$esp"
    printf '%s\n' SUPRA_AUTO_BLESS_READY > /dev/ttyS0
}
