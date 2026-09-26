#!/usr/bin/env bash
# shellcheck disable=SC2034,SC2154
set -Eeuo pipefail

STAGE=instrumentation
KDIR="${SRC}/src/widgets/kdirmodel.cpp"
KNEW="${SRC}/src/filewidgets/knewfilemenu.cpp"
mkdir -p "${WORK}/original"
cp "${KDIR}" "${WORK}/original/kdirmodel.cpp"
cp "${KNEW}" "${WORK}/original/knewfilemenu.cpp"

python3 - "${KDIR}" "${KNEW}" <<'PY'
import sys
from pathlib import Path
kdir,knew=map(Path,sys.argv[1:])

def replace_once(path,old,new,label):
    text=path.read_text()
    if text.count(old)!=1:
        raise SystemExit(f"{label}: expected one anchor, got {text.count(old)}")
    path.write_text(text.replace(old,new,1))

kdir_old='''                static const QIcon fallbackIcon = QIcon::fromTheme(QStringLiteral("unknown"));

                const QString iconName(item.iconName());
                QIcon icon;

                if (QDir::isAbsolutePath(iconName)) {
                    icon = QIcon(iconName);
                }
                if (icon.isNull()
                    || (!(iconName.endsWith(QLatin1String(".svg")) || iconName.endsWith(QLatin1String(".svgz"))) && icon.availableSizes().isEmpty())) {
                    icon = QIcon::fromTheme(iconName, fallbackIcon);
                }

                const auto parentNode = node->parent();
                if (parentNode->isOnNetwork()) {
                    return icon;
                } else {
                    return KIconUtils::addOverlays(icon, item.overlays());
                }
'''
kdir_new='''                static const QIcon fallbackIcon = QIcon::fromTheme(QStringLiteral("unknown"));

                const QString iconName(item.iconName());
                const QString r17Touch = qEnvironmentVariable("SUPRALINUX_R17_TOUCH");
                if (r17Touch == QStringLiteral("KDIR_FALLBACK")) {
                    (void)fallbackIcon.name();
                }
                QIcon icon;

                if (QDir::isAbsolutePath(iconName)) {
                    icon = QIcon(iconName);
                    if (r17Touch == QStringLiteral("KDIR_ABSOLUTE")) {
                        (void)icon.name();
                    }
                }
                if (icon.isNull()
                    || (!(iconName.endsWith(QLatin1String(".svg")) || iconName.endsWith(QLatin1String(".svgz"))) && icon.availableSizes().isEmpty())) {
                    icon = QIcon::fromTheme(iconName, fallbackIcon);
                    if (r17Touch == QStringLiteral("KDIR_FROMTHEME")) {
                        (void)icon.name();
                    }
                }

                const auto parentNode = node->parent();
                if (parentNode->isOnNetwork()) {
                    return icon;
                } else {
                    if (r17Touch == QStringLiteral("KDIR_BEFORE_OVERLAYS")) {
                        (void)icon.name();
                    }
                    const QIcon result = KIconUtils::addOverlays(icon, item.overlays());
                    if (r17Touch == QStringLiteral("KDIR_AFTER_OVERLAYS")) {
                        (void)result.name();
                    }
                    return result;
                }
'''
replace_once(kdir,kdir_old,kdir_new,"kdirmodel touch points")

ctor_old='''{
    // Don't fill the menu yet
'''
ctor_new='''{
    if (qEnvironmentVariable("SUPRALINUX_R17_TOUCH") == QStringLiteral("KNEW_CONSTRUCTOR")) {
        (void)QIcon::fromTheme(QStringLiteral("inode-directory")).name();
    }
    // Don't fill the menu yet
'''
replace_once(knew,ctor_old,ctor_new,"knew constructor")

check_old='''void KNewFileMenu::checkUpToDate()
{
    KNewFileMenuSingleton *s = kNewMenuGlobals();
    // qDebug() << this << "m_menuItemsVersion=" << d->m_menuItemsVersion
    //              << "s->templatesVersion=" << s->templatesVersion;
    if (d->m_menuItemsVersion < s->templatesVersion || s->templatesVersion == 0) {
        // qDebug() << "recreating actions";
        // We need to clean up the action collection
        // We look for our actions using the group
        qDeleteAll(d->m_newMenuGroup->actions());

        if (!s->templatesList) { // No templates list up to now
            s->templatesList = new KNewFileMenuSingleton::EntryList;
            d->slotFillTemplates();
        }

        d->fillMenu();

        d->m_menuItemsVersion = s->templatesVersion;
    }
}
'''
check_new='''void KNewFileMenu::checkUpToDate()
{
    const QString r17Touch = qEnvironmentVariable("SUPRALINUX_R17_TOUCH");
    if (r17Touch == QStringLiteral("KNEW_CHECK_ENTRY")) {
        (void)QIcon::fromTheme(QStringLiteral("inode-directory")).name();
    }
    KNewFileMenuSingleton *s = kNewMenuGlobals();
    // qDebug() << this << "m_menuItemsVersion=" << d->m_menuItemsVersion
    //              << "s->templatesVersion=" << s->templatesVersion;
    if (d->m_menuItemsVersion < s->templatesVersion || s->templatesVersion == 0) {
        // qDebug() << "recreating actions";
        // We need to clean up the action collection
        // We look for our actions using the group
        qDeleteAll(d->m_newMenuGroup->actions());

        if (!s->templatesList) { // No templates list up to now
            s->templatesList = new KNewFileMenuSingleton::EntryList;
            d->slotFillTemplates();
        }

        d->fillMenu();

        d->m_menuItemsVersion = s->templatesVersion;
    }
    if (r17Touch == QStringLiteral("KNEW_CHECK_EXIT")) {
        (void)QIcon::fromTheme(QStringLiteral("inode-directory")).name();
    }
}
'''
replace_once(knew,check_old,check_new,"knew checkUpToDate")

show_old='''void KNewFileMenuPrivate::showNewDirNameDlg(const QString &name)
{
    initDialog();

    m_fileDialog->setWindowTitle(m_windowTitle.isEmpty() ? i18nc("@title:window", "Create New Folder") : m_windowTitle);
'''
show_new='''void KNewFileMenuPrivate::showNewDirNameDlg(const QString &name)
{
    const QString r17Touch = qEnvironmentVariable("SUPRALINUX_R17_TOUCH");
    if (r17Touch == QStringLiteral("KNEW_SHOW_ENTRY")) {
        (void)QIcon::fromTheme(QStringLiteral("inode-directory")).name();
    }
    initDialog();
    if (r17Touch == QStringLiteral("KNEW_AFTER_INIT")) {
        (void)QIcon::fromTheme(QStringLiteral("inode-directory")).name();
    }

    m_fileDialog->setWindowTitle(m_windowTitle.isEmpty() ? i18nc("@title:window", "Create New Folder") : m_windowTitle);
'''
replace_once(knew,show_old,show_new,"knew showNewDirNameDlg")

default_old='''    const QString defaultFolderIconName = QStringLiteral("inode-directory");
    setIcon(QIcon::fromTheme(defaultFolderIconName));
'''
default_new='''    const QString defaultFolderIconName = QStringLiteral("inode-directory");
    QIcon r17DefaultFolderIcon = QIcon::fromTheme(defaultFolderIconName);
    if (r17Touch == QStringLiteral("KNEW_DEFAULT_CREATED")) {
        (void)r17DefaultFolderIcon.name();
    }
    setIcon(r17DefaultFolderIcon);
'''
replace_once(knew,default_old,default_new,"knew default icon")

seticon_old='''void KNewFileMenuPrivate::setIcon(const QIcon &icon)
{
    m_iconLabel->setProperty("iconName", icon.name());
'''
seticon_new='''void KNewFileMenuPrivate::setIcon(const QIcon &icon)
{
    if (qEnvironmentVariable("SUPRALINUX_R17_TOUCH") == QStringLiteral("KNEW_SETICON_INPUT")) {
        (void)icon.name();
    }
    m_iconLabel->setProperty("iconName", icon.name());
'''
replace_once(knew,seticon_old,seticon_new,"knew setIcon input")
PY

{
  diff -u "${WORK}/original/kdirmodel.cpp" "${KDIR}" || true
  diff -u "${WORK}/original/knewfilemenu.cpp" "${KNEW}" || true
} > "${EVIDENCE}/instrumentation.patch"

python3 - "${WORK}" "${KDIR}" "${KNEW}" "${EVIDENCE}/instrumentation.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
work,kdir,knew,out=map(Path,sys.argv[1:])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
out.write_text(json.dumps({
 "diagnostic_only":True,
 "canonical_source_modified":False,
 "strategy":"conditional-single-QIcon-name-read-perturbation",
 "files":{
   "src/widgets/kdirmodel.cpp":{"before":sha(work/"original/kdirmodel.cpp"),"after":sha(kdir)},
   "src/filewidgets/knewfilemenu.cpp":{"before":sha(work/"original/knewfilemenu.cpp"),"after":sha(knew)}
 }
},indent=2,sort_keys=True)+"\n")
PY
grep -F 'SUPRALINUX_R17_TOUCH' "${KDIR}" >/dev/null
grep -F 'SUPRALINUX_R17_TOUCH' "${KNEW}" >/dev/null
