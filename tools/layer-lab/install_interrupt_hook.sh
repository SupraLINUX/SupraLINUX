#!/usr/bin/env bash
# Executed by libalpm inside the disposable unapproved deployment.
set -euo pipefail
test -x /usr/bin/tree
test -d /var/lib/pacman/local/tree-2.3.2-1
/usr/bin/tree --version
# Flush the checkpoint so recovery can inspect the unpublished stage.
sync
printf '%s\n' SUPRA_INSTALL_INTERRUPT_POINT > /dev/ttyS0
sleep 180
exit 1
