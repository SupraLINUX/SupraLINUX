#!/bin/sh
set -eu

echo AURORA_NATIVE_BUILD_NETWORK_WRAPPER=START
printf 'AURORA_NATIVE_BUILD_LABEL='
cat /proc/self/attr/current

host_netns="$(cat /mnt/host-netns.txt)"
current_netns="$(readlink /proc/self/ns/net)"
echo "AURORA_NATIVE_HOST_NETNS=$host_netns"
echo "AURORA_NATIVE_BUILD_NETNS=$current_netns"
if [ "$current_netns" = "$host_netns" ]; then
    echo AURORA_NATIVE_BUILD_NETNS_DIFFERENT=FAIL
    exit 96
fi
echo AURORA_NATIVE_BUILD_NETNS_DIFFERENT=PASS

proc_ifaces="$(awk -F: 'NR > 2 {gsub(/[[:space:]]/, "", $1); if ($1 != "") print $1}' /proc/net/dev | sort | paste -sd, -)"
echo "AURORA_NATIVE_BUILD_PROC_NETIFS=$proc_ifaces"
if [ "$proc_ifaces" != "lo" ]; then
    echo AURORA_NATIVE_BUILD_PROC_NETIFS_ONLY_LO=FAIL
    exit 97
fi
echo AURORA_NATIVE_BUILD_PROC_NETIFS_ONLY_LO=PASS

ipv4_routes="$(awk 'NR > 1 {count++} END {print count+0}' /proc/net/route)"
echo "AURORA_NATIVE_BUILD_IPV4_ROUTES=$ipv4_routes"
sed 's/^/AURORA_NATIVE_BUILD_ROUTE: /' /proc/net/route || true
if [ "$ipv4_routes" -ne 0 ]; then
    echo AURORA_NATIVE_BUILD_IPV4_ROUTE_ISOLATION=FAIL
    exit 98
fi
echo AURORA_NATIVE_BUILD_IPV4_ROUTE_ISOLATION=PASS

# sbuild-usernsexec creates the network namespace after the buildd rootfs has
# inherited its sysfs mount. A pre-existing sysfs superblock can therefore
# retain the host namespace's tagged device view. Record it for diagnostics,
# but do not use /sys/class/net as the network-isolation gate. The namespace
# identity and /proc/self/net-backed data above are the authoritative checks.
sysfs_ifaces="$(find /sys/class/net -mindepth 1 -maxdepth 1 -printf '%f\n' | sort | paste -sd, -)"
echo "AURORA_NATIVE_BUILD_SYSFS_NETIFS_INHERITED_VIEW=$sysfs_ifaces"
echo AURORA_NATIVE_BUILD_SYSFS_NETIFS_GATE=NOT_USED

echo AURORA_NATIVE_BUILD_NETWORK=isolated
exec "$@"
