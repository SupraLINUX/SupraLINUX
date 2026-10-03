#!/usr/bin/env bash
set -Eeuo pipefail

PKGDIR="${1:?missing package build directory}"
EXPECTED=/build/reproducible-path/kf6-kio-6.30.0
EVIDENCE=/tmp/supralinux-round26-evidence
HELPER=/tmp/supralinux-round26-test-stage.sh
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

python3 - "${RECENT}" "${CORE}" "${RULES}" "${EVIDENCE}" <<'PY'
import difflib
import sys
from pathlib import Path

recent=Path(sys.argv[1])
core=Path(sys.argv[2])
rules=Path(sys.argv[3])
evidence=Path(sys.argv[4])

s=recent.read_text()
anchor='''    const auto recentUrls = KRecentDocument::recentUrls();\n    QCOMPARE(recentUrls.length(), 3);\n'''
insert='''    const auto recentUrls = KRecentDocument::recentUrls();\n    const QString capturePath = qEnvironmentVariable("SUPRALINUX_CAPTURE_XBEL");\n    if (!capturePath.isEmpty()) {\n        QFile::remove(capturePath);\n        QFile::copy(m_xbelPath, capturePath);\n        QFile orderFile(capturePath + QStringLiteral(".order"));\n        if (orderFile.open(QIODevice::WriteOnly | QIODevice::Truncate)) {\n            for (const auto &recentUrl : recentUrls) {\n                orderFile.write(recentUrl.fileName().toUtf8());\n                orderFile.write("\\n");\n            }\n            orderFile.close();\n        }\n    }\n    QCOMPARE(recentUrls.length(), 3);\n'''
if s.count(anchor) != 1:
    raise SystemExit(f"unexpected KRecent instrumentation anchor count: {s.count(anchor)}")
recent.write_text(s.replace(anchor,insert,1))

original_core=core.read_text()
c=original_core

old_eviction='''    QMultiMap<QDateTime, QDomNode> bookmarksByModifiedDate;\n    for (int i = 0; i < bookmarkList.length(); ++i) {\n        const auto node = bookmarkList.item(i);\n        const auto modifiedString = node.attributes().namedItem(modifiedAttribute);\n        const auto modifiedTime = QDateTime::fromString(modifiedString.nodeValue(), Qt::ISODate);\n\n        bookmarksByModifiedDate.insert(modifiedTime, node);\n    }\n\n    int i = 0;\n    // entries are traversed in ascending key order\n    for (auto entry = bookmarksByModifiedDate.keyValueBegin(); entry != bookmarksByModifiedDate.keyValueEnd(); ++entry) {\n        // only keep the maxEntries last nodes\n        if (bookmarksByModifiedDate.size() - i > maxEntries) {\n            xbelElement.removeChild(entry->second);\n        }\n        ++i;\n    }\n'''
new_eviction='''    struct BookmarkEntry {\n        QDateTime modified;\n        int xbelOrder;\n        QDomNode node;\n    };\n    QList<BookmarkEntry> bookmarksByModifiedDate;\n    bookmarksByModifiedDate.reserve(bookmarkList.length());\n    for (int i = 0; i < bookmarkList.length(); ++i) {\n        const auto node = bookmarkList.item(i);\n        const auto modifiedString = node.attributes().namedItem(modifiedAttribute);\n        const auto modifiedTime = QDateTime::fromString(modifiedString.nodeValue(), Qt::ISODate);\n        bookmarksByModifiedDate.push_back({modifiedTime, i, node});\n    }\n\n    std::sort(bookmarksByModifiedDate.begin(), bookmarksByModifiedDate.end(), [](const BookmarkEntry &a, const BookmarkEntry &b) {\n        if (a.modified != b.modified) {\n            return a.modified < b.modified;\n        }\n        return a.xbelOrder < b.xbelOrder;\n    });\n\n    const int entriesToRemove = bookmarksByModifiedDate.size() - maxEntries;\n    for (int i = 0; i < entriesToRemove; ++i) {\n        xbelElement.removeChild(bookmarksByModifiedDate.at(i).node);\n    }\n'''
if c.count(old_eviction) != 1:
    raise SystemExit(f"unexpected eviction block count: {c.count(old_eviction)}")
c=c.replace(old_eviction,new_eviction,1)

old_recent='''static QMap<QUrl, QDateTime> xbelRecentlyUsedList()\n{\n    QMap<QUrl, QDateTime> ret;\n    QFile input(xbelPath());\n    if (!input.open(QIODevice::ReadOnly)) {\n        qCWarning(KIO_CORE) << "Failed to open" << input.fileName() << input.errorString();\n        return ret;\n    }\n\n    QXmlStreamReader xml(&input);\n    xml.readNextStartElement();\n    if (xml.name() != QLatin1String("xbel") || xml.attributes().value(QLatin1String("version")) != QLatin1String("1.0")) {\n        qCWarning(KIO_CORE) << "The file is not an XBEL version 1.0 file.";\n        return ret;\n    }\n\n    while (!xml.atEnd() && !xml.hasError()) {\n        if (xml.readNext() != QXmlStreamReader::StartElement || xml.name() != QLatin1String("bookmark")) {\n            continue;\n        }\n\n        const auto urlString = xml.attributes().value(QLatin1String("href"));\n        if (urlString.isEmpty()) {\n            qCInfo(KIO_CORE) << "Invalid bookmark in" << input.fileName();\n            continue;\n        }\n        const QUrl url = QUrl::fromEncoded(urlString.toLatin1());\n        if (url.isLocalFile() && !QFile(url.toLocalFile()).exists()) {\n            continue;\n        }\n        const auto attributes = xml.attributes();\n        const QDateTime modified = QDateTime::fromString(attributes.value(QLatin1String("modified")).toString(), Qt::ISODate);\n        const QDateTime visited = QDateTime::fromString(attributes.value(QLatin1String("visited")).toString(), Qt::ISODate);\n        const QDateTime added = QDateTime::fromString(attributes.value(QLatin1String("added")).toString(), Qt::ISODate);\n        if (modified > visited && modified > added) {\n            ret[url] = modified;\n        } else if (visited > added) {\n            ret[url] = visited;\n        } else {\n            ret[url] = added;\n        }\n    }\n\n    if (xml.hasError()) {\n        qCWarning(KIO_CORE) << "Failed to read" << input.fileName() << xml.errorString();\n    }\n\n    return ret;\n}\n\nQList<QUrl> KRecentDocument::recentUrls()\n{\n    QMap<QUrl, QDateTime> documents = xbelRecentlyUsedList();\n\n    QList<QUrl> ret = documents.keys();\n    std::sort(ret.begin(), ret.end(), [&](const QUrl &doc1, const QUrl &doc2) {\n        return documents.value(doc1) < documents.value(doc2);\n    });\n\n    return ret;\n}\n'''
new_recent='''struct RecentDocumentEntry\n{\n    QUrl url;\n    QDateTime timestamp;\n    int xbelOrder;\n};\n\nstatic QList<RecentDocumentEntry> xbelRecentlyUsedList()\n{\n    QMap<QUrl, RecentDocumentEntry> uniqueEntries;\n    QFile input(xbelPath());\n    if (!input.open(QIODevice::ReadOnly)) {\n        qCWarning(KIO_CORE) << "Failed to open" << input.fileName() << input.errorString();\n        return {};\n    }\n\n    QXmlStreamReader xml(&input);\n    xml.readNextStartElement();\n    if (xml.name() != QLatin1String("xbel") || xml.attributes().value(QLatin1String("version")) != QLatin1String("1.0")) {\n        qCWarning(KIO_CORE) << "The file is not an XBEL version 1.0 file.";\n        return {};\n    }\n\n    int xbelOrder = 0;\n    while (!xml.atEnd() && !xml.hasError()) {\n        if (xml.readNext() != QXmlStreamReader::StartElement || xml.name() != QLatin1String("bookmark")) {\n            continue;\n        }\n\n        const auto urlString = xml.attributes().value(QLatin1String("href"));\n        if (urlString.isEmpty()) {\n            qCInfo(KIO_CORE) << "Invalid bookmark in" << input.fileName();\n            continue;\n        }\n        const QUrl url = QUrl::fromEncoded(urlString.toLatin1());\n        if (url.isLocalFile() && !QFile(url.toLocalFile()).exists()) {\n            continue;\n        }\n        const auto attributes = xml.attributes();\n        const QDateTime modified = QDateTime::fromString(attributes.value(QLatin1String("modified")).toString(), Qt::ISODate);\n        const QDateTime visited = QDateTime::fromString(attributes.value(QLatin1String("visited")).toString(), Qt::ISODate);\n        const QDateTime added = QDateTime::fromString(attributes.value(QLatin1String("added")).toString(), Qt::ISODate);\n        QDateTime timestamp;\n        if (modified > visited && modified > added) {\n            timestamp = modified;\n        } else if (visited > added) {\n            timestamp = visited;\n        } else {\n            timestamp = added;\n        }\n        uniqueEntries.insert(url, {url, timestamp, xbelOrder++});\n    }\n\n    if (xml.hasError()) {\n        qCWarning(KIO_CORE) << "Failed to read" << input.fileName() << xml.errorString();\n    }\n\n    return uniqueEntries.values();\n}\n\nQList<QUrl> KRecentDocument::recentUrls()\n{\n    auto documents = xbelRecentlyUsedList();\n    std::sort(documents.begin(), documents.end(), [](const RecentDocumentEntry &a, const RecentDocumentEntry &b) {\n        if (a.timestamp != b.timestamp) {\n            return a.timestamp < b.timestamp;\n        }\n        return a.xbelOrder < b.xbelOrder;\n    });\n\n    QList<QUrl> ret;\n    ret.reserve(documents.size());\n    for (const auto &document : std::as_const(documents)) {\n        ret.push_back(document.url);\n    }\n    return ret;\n}\n'''
if c.count(old_recent) != 1:
    raise SystemExit(f"unexpected recentUrls block count: {c.count(old_recent)}")
c=c.replace(old_recent,new_recent,1)

evidence.joinpath("krecentdocument.cpp.candidate").write_text(c)
patch=''.join(difflib.unified_diff(
    original_core.splitlines(True),
    c.splitlines(True),
    fromfile="a/src/core/krecentdocument.cpp",
    tofile="b/src/core/krecentdocument.cpp",
))
if not patch:
    raise SystemExit("candidate remediation produced empty diff")
evidence.joinpath("candidate-remediation.patch").write_text(patch)

timestamp_anchor='''    const QString currentTimestamp = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs).chopped(1) + "000Z"_L1;\n'''
timestamp_insert='''    const QString supralinuxTimestampMode = qEnvironmentVariable("SUPRALINUX_KRECENT_TIMESTAMP_MODE");\n    const bool supralinuxControlledUrl = url.fileName().startsWith(QStringLiteral("temp File "));\n    QString currentTimestamp;\n    if (supralinuxControlledUrl && supralinuxTimestampMode == QStringLiteral("monotonic")) {\n        static qint64 supralinuxTimestampSequence = 0;\n        const QDateTime supralinuxBase = QDateTime::fromString(QStringLiteral("2030-01-01T00:00:00.000Z"), Qt::ISODateWithMs);\n        currentTimestamp = supralinuxBase.addMSecs(supralinuxTimestampSequence++).toString(Qt::ISODateWithMs).chopped(1) + "000Z"_L1;\n    } else if (supralinuxControlledUrl && supralinuxTimestampMode == QStringLiteral("fixed")) {\n        currentTimestamp = QStringLiteral("2030-01-01T00:00:00.000000Z");\n    } else {\n        currentTimestamp = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs).chopped(1) + "000Z"_L1;\n    }\n'''
if c.count(timestamp_anchor) != 1:
    raise SystemExit(f"unexpected KRecent timestamp anchor count after candidate remediation: {c.count(timestamp_anchor)}")
core.write_text(c.replace(timestamp_anchor,timestamp_insert,1))

r=rules.read_text()
old='''override_dh_auto_test:\n\tmkdir -p debian/.supralinux-test-home/sbuild\n\tcd obj-$(DEB_HOST_GNU_TYPE) && \\\n\t\tHOME="$(CURDIR)/debian/.supralinux-test-home/sbuild" \\\n\t\tQT_QPA_PLATFORM=xcb \\\n\t\tQT_QPA_SYSTEM_ICON_THEME=breeze \\\n\t\tKDECI_PLATFORM_PATH="$(CURDIR)" \\\n\t\tdbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24" ctest --verbose -j1\n'''
new='''override_dh_auto_test:\n\t/tmp/supralinux-round26-test-stage.sh "$(CURDIR)" "obj-$(DEB_HOST_GNU_TYPE)"\n'''
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
EVIDENCE=/tmp/supralinux-round26-evidence
OBJ="${PKGDIR}/${OBJREL}"
RECENT="${PKGDIR}/autotests/krecentdocumenttest.cpp"
CORE="${PKGDIR}/src/core/krecentdocument.cpp"
RULES="${PKGDIR}/debian/rules"
HIDDEN_HOME="${PKGDIR}/debian/.supralinux-test-home/sbuild"
VISIBLE_HOME="${PKGDIR}/debian/supralinux-test-home/sbuild"

[[ "${PKGDIR}" == "${EXPECTED}" ]]
[[ "$(id -un)" == sbuild ]]
[[ -x "${OBJ}/bin/krecentdocumenttest" ]]
[[ -x "${OBJ}/bin/kdirmodeltest" ]]
[[ -f "${EVIDENCE}/preparation-complete" ]]
: > "${EVIDENCE}/kdirmodel-runs.tsv"

reset_homes() {
  rm -rf "${HIDDEN_HOME}" "${VISIBLE_HOME}"
}

run_kdirmodel_lane() {
  local lane="$1" count="$2" home_dir="$3"
  local i log rc exact_sig
  cd "${OBJ}"
  for ((i=1; i<=count; i++)); do
    reset_homes
    mkdir -p "${home_dir}"
    log="${EVIDENCE}/${lane}-${i}.log"
    rm -f "${log}"

    set +e
    HOME="${home_dir}"       LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild       QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze       KDECI_PLATFORM_PATH="${PKGDIR}"       SUPRALINUX_KRECENT_TIMESTAMP_MODE=native       dbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24"       ctest --verbose -j1 -R '^kiowidgets-kdirmodeltest$' >"${log}" 2>&1
    rc=$?
    set -e

    exact_sig=0
    if grep -Fq "KDirModelTest::testShowRoot()" "${log}" &&        grep -Fq "KDirModelTest::testShowRootAndExpandToUrl()" "${log}" &&        grep -Fq "dirModel.indexForUrl(homeUrl).isValid()" "${log}" &&        grep -Fq "kdirmodeltest.cpp(1353)" "${log}" &&        grep -Fq "kdirmodeltest.cpp(1393)" "${log}"; then
      exact_sig=1
    fi

    printf '%s\t%s\t%s\t%s\n' "${lane}" "${i}" "${rc}" "${exact_sig}" >> "${EVIDENCE}/kdirmodel-runs.tsv"
  done
}

run_kdirmodel_lane hidden-home 10 "${HIDDEN_HOME}"
run_kdirmodel_lane visible-home 20 "${VISIBLE_HOME}"

reset_homes
mkdir -p "${VISIBLE_HOME}"
FULL_LOG="${EVIDENCE}/full-suite-visible.log"
FULL_XBEL="${EVIDENCE}/full-suite-visible.xbel"
rm -f "${FULL_LOG}" "${FULL_XBEL}" "${FULL_XBEL}.order"
set +e
HOME="${VISIBLE_HOME}"   LANG=C.UTF-8 LC_ALL=C.UTF-8 LOGNAME=sbuild USER=sbuild   QT_QPA_PLATFORM=xcb QT_QPA_SYSTEM_ICON_THEME=breeze   KDECI_PLATFORM_PATH="${PKGDIR}"   SUPRALINUX_CAPTURE_XBEL="${FULL_XBEL}"   SUPRALINUX_KRECENT_TIMESTAMP_MODE=native   dbus-run-session -- xvfb-run -a -s "-screen 0 1280x1024x24"   ctest --verbose -j1 >"${FULL_LOG}" 2>&1
FULL_RC=$?
set -e
printf '%s\n' "${FULL_RC}" > "${EVIDENCE}/full-suite-visible.rc"

reset_homes
touch "${EVIDENCE}/test-homes-cleaned" "${EVIDENCE}/matrix-complete"

cp -a "${EVIDENCE}/krecentdocumenttest.cpp.original" "${RECENT}"
cp -a "${EVIDENCE}/krecentdocument.cpp.original" "${CORE}"
cp -a "${EVIDENCE}/debian-rules.original" "${RULES}"
sha256sum "${RECENT}" > "${EVIDENCE}/test-source-after.sha256"
sha256sum "${CORE}" > "${EVIDENCE}/core-source-after.sha256"
sha256sum "${RULES}" > "${EVIDENCE}/rules-after.sha256"
cmp -s "${RECENT}" "${EVIDENCE}/krecentdocumenttest.cpp.original"
cmp -s "${CORE}" "${EVIDENCE}/krecentdocument.cpp.original"
cmp -s "${RULES}" "${EVIDENCE}/debian-rules.original"
[[ ! -e "${HIDDEN_HOME}" && ! -e "${VISIBLE_HOME}" ]]
touch "${EVIDENCE}/source-restored" "${EVIDENCE}/hook-complete"

printf '%s\n' 'SUPRALINUX_ROUND26_EVIDENCE_BASE64_BEGIN'
tar -C "${EVIDENCE}" -czf - . | base64
printf '%s\n' 'SUPRALINUX_ROUND26_EVIDENCE_BASE64_END'
exit 86
EOF_HELPER
chmod 0755 "${HELPER}"

bash -n "${HELPER}"
sha256sum "${RECENT}" > "${EVIDENCE}/test-source-instrumented.sha256"
sha256sum "${EVIDENCE}/krecentdocument.cpp.candidate" > "${EVIDENCE}/candidate-source.sha256"
sha256sum "${EVIDENCE}/candidate-remediation.patch" > "${EVIDENCE}/candidate-patch.sha256"
sha256sum "${CORE}" > "${EVIDENCE}/core-source-instrumented.sha256"
sha256sum "${RULES}" > "${EVIDENCE}/rules-instrumented.sha256"
chown -R sbuild:sbuild "${EVIDENCE}"
touch "${EVIDENCE}/preparation-complete"
chown sbuild:sbuild "${EVIDENCE}/preparation-complete"
printf '%s\n' "SUPRALINUX_ROUND26_PREPARED krecent-candidate-applied-hidden-home-test-ready"
exit 0
