#!/usr/bin/env bash
set -Eeuo pipefail

PKGDIR="${1:?missing package build directory}"
EXPECTED=/build/reproducible-path/kf6-kio-6.30.0
EVIDENCE=/tmp/supralinux-round24-evidence
HELPER=/tmp/supralinux-round24-test-stage.sh
RECENT="${PKGDIR}/autotests/krecentdocumenttest.cpp"
CORE="${PKGDIR}/src/core/krecentdocument.cpp"
RULES="${PKGDIR}/debian/rules"

[[ "${PKGDIR}" == "${EXPECTED}" ]]
[[ "$(id -un)" == root ]]
[[ -f "${RECENT}" && -f "${CORE}" && -f "${RULES}" ]]
getent passwd sbuild >/dev/null
getent group sbuild >/dev/null

rm -rf "${EVIDENCE}"
install -d -o sbuild -g sbuild "${EVIDENCE}" "${EVIDENCE}/xbels"
cp -a "${RECENT}" "${EVIDENCE}/krecentdocumenttest.cpp.original"
cp -a "${CORE}" "${EVIDENCE}/krecentdocument.cpp.original"
cp -a "${RULES}" "${EVIDENCE}/debian-rules.original"
sha256sum "${RECENT}" > "${EVIDENCE}/test-source-before.sha256"
sha256sum "${CORE}" > "${EVIDENCE}/core-source-before.sha256"
sha256sum "${RULES}" > "${EVIDENCE}/rules-before.sha256"
getent passwd sbuild > "${EVIDENCE}/sbuild-passwd.txt"
id sbuild > "${EVIDENCE}/sbuild-id.txt"
dpkg-query -W | sort > "${EVIDENCE}/chroot-packages.tsv"
printf '%s\n' "${PKGDIR}" > "${EVIDENCE}/package-build-dir.txt"

python3 - "${RECENT}" "${CORE}" "${RULES}" <<'PY'
import sys
from pathlib import Path

recent=Path(sys.argv[1])
core=Path(sys.argv[2])
rules=Path(sys.argv[3])

s=recent.read_text()
anchor='''    const auto recentUrls = KRecentDocument::recentUrls();\n    QCOMPARE(recentUrls.length(), 3);\n'''
insert='''    const auto recentUrls = KRecentDocument::recentUrls();\n    const QString capturePath = qEnvironmentVariable("SUPRALINUX_CAPTURE_XBEL");\n    if (!capturePath.isEmpty()) {\n        QFile::remove(capturePath);\n        QFile::copy(m_xbelPath, capturePath);\n        QFile orderFile(capturePath + QStringLiteral(".order"));\n        if (orderFile.open(QIODevice::WriteOnly | QIODevice::Truncate)) {\n            for (const auto &recentUrl : recentUrls) {\n                orderFile.write(recentUrl.fileName().toUtf8());\n                orderFile.write("\\n");\n            }\n            orderFile.close();\n        }\n    }\n    QCOMPARE(recentUrls.length(), 3);\n'''
if s.count(anchor) != 1:
    raise SystemExit(f"unexpected KRecent instrumentation anchor count: {s.count(anchor)}")
recent.write_text(s.replace(anchor,insert,1))

c=core.read_text()
timestamp_anchor='''    const QString currentTimestamp = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs).chopped(1) + "000Z"_L1;\n'''
timestamp_insert='''    const QString supralinuxTimestampMode = qEnvironmentVariable("SUPRALINUX_KRECENT_TIMESTAMP_MODE");\n    const bool supralinuxControlledUrl = url.fileName().startsWith(QStringLiteral("temp File "));\n    QString currentTimestamp;\n    if (supralinuxControlledUrl && supralinuxTimestampMode == QStringLiteral("monotonic")) {\n        static qint64 supralinuxTimestampSequence = 0;\n        const QDateTime supralinuxBase = QDateTime::fromString(QStringLiteral("2030-01-01T00:00:00.000Z"), Qt::ISODateWithMs);\n        currentTimestamp = supralinuxBase.addMSecs(supralinuxTimestampSequence++).toString(Qt::ISODateWithMs).chopped(1) + "000Z"_L1;\n    } else if (supralinuxControlledUrl && supralinuxTimestampMode == QStringLiteral("fixed")) {\n        currentTimestamp = QStringLiteral("2030-01-01T00:00:00.000000Z");\n    } else {\n        currentTimestamp = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs).chopped(1) + "000Z"_L1;\n    }\n'''
if c.count(timestamp_anchor) != 1:
    raise SystemExit(f"unexpected KRecent timestamp anchor count: {c.count(timestamp_anchor)}")
core.write_text(c.replace(timestamp_anchor,timestamp_insert,1))

r=rules.read_text()
old='''override_dh_auto_test:\n\tmkdir -p debian/.supralinux-test-home/sbuild\n\tcd obj-$(DEB_HOST_GNU_TYPE) && \\\n\t\tHOME="$(CURDIR)/debian/.supralinux-test-home/sbuild" \\\n\t\tQT_QPA_PLATFORM=xcb \\\n\t\tQT_QPA_SYSTEM_ICON_THEME=breeze \\\n\t\tKDECI_PLATFORM_PATH="$(CURDIR)" \\\n\t\tdbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24" ctest --verbose -j1\n'''
new='''override_dh_auto_test:\n\t/tmp/supralinux-round24-test-stage.sh "$(CURDIR)" "obj-$(DEB_HOST_GNU_TYPE)"\n'''
if r.count(old) != 1:
    raise SystemExit(f"unexpected debian/rules test block count: {r.count(old)}")
rules.write_text(r.replace(old,new,1))
PY

cat > "${HELPER}" <<'EOF_HELPER'
#!/usr/bin/env bash
set -Eeuo pipefail

PKGDIR="${1:?missing package dir}"
OBJREL="${2:?missing object dir}"
EXPECTED=/build/reproducible-path/kf6-kio-6.30.0
EVIDENCE=/tmp/supralinux-round24-evidence
OBJ="${PKGDIR}/${OBJREL}"
RECENT="${PKGDIR}/autotests/krecentdocumenttest.cpp"
CORE="${PKGDIR}/src/core/krecentdocument.cpp"
RULES="${PKGDIR}/debian/rules"
HOME_DIR="${PKGDIR}/debian/.supralinux-test-home/sbuild"

[[ "${PKGDIR}" == "${EXPECTED}" ]]
[[ "$(id -un)" == sbuild ]]
[[ -x "${OBJ}/bin/krecentdocumenttest" ]]
[[ -f "${EVIDENCE}/preparation-complete" ]]
: > "${EVIDENCE}/runs.tsv"

run_lane() {
  local lane="$1" count="$2" timestamp_mode="$3"
  shift 3
  local -a args=("$@")
  local i cap order log rc sig failed captures order_lines
  cd "${OBJ}"
  for ((i=1; i<=count; i++)); do
    rm -rf "${HOME_DIR}"
    mkdir -p "${HOME_DIR}"
    rm -f "${OBJ}/autotests"/temp\ File* 2>/dev/null || true
    cap="${EVIDENCE}/xbels/${lane}-${i}.xbel"
    order="${cap}.order"
    log="${EVIDENCE}/${lane}-${i}.log"
    rm -f "${cap}" "${order}" "${log}"

    set +e
    HOME="${HOME_DIR}" \
      LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild \
      QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze \
      KDECI_PLATFORM_PATH="${PKGDIR}" SUPRALINUX_CAPTURE_XBEL="${cap}" \
      SUPRALINUX_KRECENT_TIMESTAMP_MODE="${timestamp_mode}" \
      dbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24" \
      ctest --verbose -j1 "${args[@]}" >"${log}" 2>&1
    rc=$?
    set -e

    sig=0
    if grep -Fq 'Actual   (recentUrls.at(i).fileName())' "${log}" && \
       grep -Fq '"temp File 11"' "${log}" && grep -Fq '"temp File 12"' "${log}"; then
      sig=1
    fi
    failed=0
    if grep -Fq 'kiocore-krecentdocumenttest' "${log}" && \
       { grep -Fq '***Failed' "${log}" || grep -Fq 'FAIL!' "${log}"; }; then
      failed=1
    fi
    captures=0
    [[ -s "${cap}" ]] && captures=1
    order_lines=0
    [[ -s "${order}" ]] && order_lines="$(wc -l < "${order}" | tr -d ' ')"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "${lane}" "${i}" "${rc}" "${sig}" "${failed}" "${captures}:${order_lines}" \
      >> "${EVIDENCE}/runs.tsv"
  done
}

run_lane native 40 native -R '^kiocore-krecentdocumenttest$'
run_lane monotonic 40 monotonic -R '^kiocore-krecentdocumenttest$'
run_lane fixed 20 fixed -R '^kiocore-krecentdocumenttest$'

touch "${EVIDENCE}/matrix-complete"

cp -a "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT}"
cp -a "${EVIDENCE}/krecentdocument.cpp.original" "${CORE}"
cp -a "${EVIDENCE}/debian-rules.original" "${RULES}"
sha256sum "${RECENT}" > "${EVIDENCE}/test-source-after.sha256"
sha256sum "${CORE}" > "${EVIDENCE}/core-source-after.sha256"
sha256sum "${RULES}" > "${EVIDENCE}/rules-after.sha256"
cmp -s "${RECENT}" "${EVIDENCE}/krecentdocumenttest.cpp.original"
cmp -s "${CORE}" "${EVIDENCE}/krecentdocument.cpp.original"
cmp -s "${RULES}" "${EVIDENCE}/debian-rules.original"
touch "${EVIDENCE}/source-restored" "${EVIDENCE}/hook-complete"

printf '%s\n' 'SUPRALINUX_ROUND24_EVIDENCE_BASE64_BEGIN'
tar -C "${EVIDENCE}" -czf - . | base64
printf '%s\n' 'SUPRALINUX_ROUND24_EVIDENCE_BASE64_END'
exit 86
EOF_HELPER
chmod 0755 "${HELPER}"

bash -n "${HELPER}"
sha256sum "${RECENT}" > "${EVIDENCE}/test-source-instrumented.sha256"
sha256sum "${CORE}" > "${EVIDENCE}/core-source-instrumented.sha256"
sha256sum "${RULES}" > "${EVIDENCE}/rules-instrumented.sha256"
chown -R sbuild:sbuild "${EVIDENCE}"
touch "${EVIDENCE}/preparation-complete"
chown sbuild:sbuild "${EVIDENCE}/preparation-complete"
exit 0
