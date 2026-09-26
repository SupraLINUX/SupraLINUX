#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154
set -Eeuo pipefail

R17_KDIR="${SRC}/src/widgets/kdirmodel.cpp"
R17_KNEW="${SRC}/src/filewidgets/knewfilemenu.cpp"
R17_ORIGINAL="${WORK}/round17-original"
mkdir -p "${R17_ORIGINAL}"
cp "${R17_KDIR}" "${R17_ORIGINAL}/kdirmodel.cpp"
cp "${R17_KNEW}" "${R17_ORIGINAL}/knewfilemenu.cpp"

sha256sum "${R17_KDIR}" "${R17_KNEW}" > "${EVIDENCE}/original-source-sha256.txt"

r17_restore_sources() {
  cp "${R17_ORIGINAL}/kdirmodel.cpp" "${R17_KDIR}"
  cp "${R17_ORIGINAL}/knewfilemenu.cpp" "${R17_KNEW}"
  cmp -s "${R17_ORIGINAL}/kdirmodel.cpp" "${R17_KDIR}"
  cmp -s "${R17_ORIGINAL}/knewfilemenu.cpp" "${R17_KNEW}"
}

r17_patch_kdirmodel_local_result() {
  r17_restore_sources
  python3 - "${R17_KDIR}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1])
old='''                } else {
                    return KIconUtils::addOverlays(icon, item.overlays());
                }
'''
new='''                } else {
                    const QIcon r17Result = KIconUtils::addOverlays(icon, item.overlays());
                    return r17Result;
                }
'''
s=p.read_text()
if s.count(old)!=1:
    raise SystemExit(f"kdirmodel local-result anchor count={s.count(old)}")
p.write_text(s.replace(old,new,1))
PY
  diff -u "${R17_ORIGINAL}/kdirmodel.cpp" "${R17_KDIR}" > "${EVIDENCE}/variant-kdirmodel-local-result.patch" || true
  grep -F 'const QIcon r17Result = KIconUtils::addOverlays' "${R17_KDIR}" >/dev/null
}

r17_patch_knew_named_default() {
  r17_restore_sources
  python3 - "${R17_KNEW}" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1])
old='''    const QString defaultFolderIconName = QStringLiteral("inode-directory");
    setIcon(QIcon::fromTheme(defaultFolderIconName));
'''
new='''    const QString defaultFolderIconName = QStringLiteral("inode-directory");
    const QIcon r17DefaultFolderIcon = QIcon::fromTheme(defaultFolderIconName);
    setIcon(r17DefaultFolderIcon);
'''
s=p.read_text()
if s.count(old)!=1:
    raise SystemExit(f"knewfilemenu named-default anchor count={s.count(old)}")
p.write_text(s.replace(old,new,1))
PY
  diff -u "${R17_ORIGINAL}/knewfilemenu.cpp" "${R17_KNEW}" > "${EVIDENCE}/variant-knewfilemenu-named-default.patch" || true
  grep -F 'const QIcon r17DefaultFolderIcon = QIcon::fromTheme' "${R17_KNEW}" >/dev/null
}
