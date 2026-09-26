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
                const bool r17Trace = QDir::isAbsolutePath(iconName);
                if (r17Trace) {
                    qInfo().noquote() << QStringLiteral("R17|KDIR|stage=fallback|source=%1|name=%2|null=%3|theme=%4|fallback=%5")
                                            .arg(iconName)
                                            .arg(fallbackIcon.name())
                                            .arg(fallbackIcon.isNull() ? 1 : 0)
                                            .arg(QIcon::themeName())
                                            .arg(QIcon::fallbackThemeName());
                }
                QIcon icon;

                if (QDir::isAbsolutePath(iconName)) {
                    icon = QIcon(iconName);
                    qInfo().noquote() << QStringLiteral("R17|KDIR|stage=absolute-qicon|source=%1|name=%2|null=%3")
                                            .arg(iconName)
                                            .arg(icon.name())
                                            .arg(icon.isNull() ? 1 : 0);
                }
                if (icon.isNull()
                    || (!(iconName.endsWith(QLatin1String(".svg")) || iconName.endsWith(QLatin1String(".svgz"))) && icon.availableSizes().isEmpty())) {
                    icon = QIcon::fromTheme(iconName, fallbackIcon);
                    if (r17Trace) {
                        qInfo().noquote() << QStringLiteral("R17|KDIR|stage=after-fromtheme|source=%1|name=%2|null=%3")
                                                .arg(iconName)
                                                .arg(icon.name())
                                                .arg(icon.isNull() ? 1 : 0);
                    }
                }

                const auto parentNode = node->parent();
                if (parentNode->isOnNetwork()) {
                    return icon;
                } else {
                    const auto overlays = item.overlays();
                    if (r17Trace) {
                        qInfo().noquote() << QStringLiteral("R17|KDIR|stage=before-overlays|source=%1|name=%2|null=%3|overlays=%4")
                                                .arg(iconName)
                                                .arg(icon.name())
                                                .arg(icon.isNull() ? 1 : 0)
                                                .arg(overlays.size());
                    }
                    const QIcon result = KIconUtils::addOverlays(icon, overlays);
                    if (r17Trace) {
                        qInfo().noquote() << QStringLiteral("R17|KDIR|stage=after-overlays|source=%1|name=%2|null=%3")
                                                .arg(iconName)
                                                .arg(result.name())
                                                .arg(result.isNull() ? 1 : 0);
                    }
                    return result;
                }
'''
replace_once(kdir,kdir_old,kdir_new,"kdirmodel decoration")

seticon_old='''void KNewFileMenuPrivate::setIcon(const QIcon &icon)
{
    m_iconLabel->setProperty("iconName", icon.name());
    if (!icon.isNull()) {
        const QSize iconSize{KIconLoader::SizeHuge, KIconLoader::SizeHuge};
        m_iconLabel->setPixmap(icon.pixmap(iconSize, m_fileDialog->devicePixelRatioF()));
    }
    m_iconLabel->setVisible(!icon.isNull());
}
'''
seticon_new='''void KNewFileMenuPrivate::setIcon(const QIcon &icon)
{
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=seticon-input|name=%1|null=%2|theme=%3|fallback=%4")
                            .arg(icon.name())
                            .arg(icon.isNull() ? 1 : 0)
                            .arg(QIcon::themeName())
                            .arg(QIcon::fallbackThemeName());
    m_iconLabel->setProperty("iconName", icon.name());
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=seticon-property|name=%1")
                            .arg(m_iconLabel->property("iconName").toString());
    if (!icon.isNull()) {
        const QSize iconSize{KIconLoader::SizeHuge, KIconLoader::SizeHuge};
        m_iconLabel->setPixmap(icon.pixmap(iconSize, m_fileDialog->devicePixelRatioF()));
    }
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=seticon-after-pixmap|name=%1")
                            .arg(m_iconLabel->property("iconName").toString());
    m_iconLabel->setVisible(!icon.isNull());
}
'''
replace_once(knew,seticon_old,seticon_new,"knew setIcon")

ctor_old='''{
    // Don't fill the menu yet
'''
ctor_new='''{
    const QIcon r17CtorProbe = QIcon::fromTheme(QStringLiteral("inode-directory"));
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=constructor-body|name=%1|theme=%2|fallback=%3")
                            .arg(r17CtorProbe.name())
                            .arg(QIcon::themeName())
                            .arg(QIcon::fallbackThemeName());
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
    const QIcon r17EntryProbe = QIcon::fromTheme(QStringLiteral("inode-directory"));
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=check-entry|name=%1|theme=%2|fallback=%3")
                            .arg(r17EntryProbe.name())
                            .arg(QIcon::themeName())
                            .arg(QIcon::fallbackThemeName());
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
    const QIcon r17ExitProbe = QIcon::fromTheme(QStringLiteral("inode-directory"));
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=check-exit|name=%1|theme=%2|fallback=%3")
                            .arg(r17ExitProbe.name())
                            .arg(QIcon::themeName())
                            .arg(QIcon::fallbackThemeName());
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
    const QIcon r17ShowEntry = QIcon::fromTheme(QStringLiteral("inode-directory"));
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=show-entry|name=%1|theme=%2|fallback=%3")
                            .arg(r17ShowEntry.name())
                            .arg(QIcon::themeName())
                            .arg(QIcon::fallbackThemeName());
    initDialog();
    const QIcon r17AfterInit = QIcon::fromTheme(QStringLiteral("inode-directory"));
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=show-after-init|name=%1|theme=%2|fallback=%3")
                            .arg(r17AfterInit.name())
                            .arg(QIcon::themeName())
                            .arg(QIcon::fallbackThemeName());

    m_fileDialog->setWindowTitle(m_windowTitle.isEmpty() ? i18nc("@title:window", "Create New Folder") : m_windowTitle);
'''
replace_once(knew,show_old,show_new,"knew show entry")

default_old='''    const QString defaultFolderIconName = QStringLiteral("inode-directory");
    setIcon(QIcon::fromTheme(defaultFolderIconName));
'''
default_new='''    const QString defaultFolderIconName = QStringLiteral("inode-directory");
    const QIcon r17DefaultFolderIcon = QIcon::fromTheme(defaultFolderIconName);
    qInfo().noquote() << QStringLiteral("R17|KNEW|stage=default-created|name=%1|null=%2|theme=%3|fallback=%4")
                            .arg(r17DefaultFolderIcon.name())
                            .arg(r17DefaultFolderIcon.isNull() ? 1 : 0)
                            .arg(QIcon::themeName())
                            .arg(QIcon::fallbackThemeName());
    setIcon(r17DefaultFolderIcon);
'''
replace_once(knew,default_old,default_new,"knew default icon")

grid_old='''        m_chooseIconBox->show();
    }

    m_creatingDirectory = true;
'''
grid_new='''        m_chooseIconBox->show();
        qInfo().noquote() << QStringLiteral("R17|KNEW|stage=grid-ready|name=%1")
                                .arg(m_iconLabel->property("iconName").toString());
    }

    m_creatingDirectory = true;
'''
replace_once(knew,grid_old,grid_new,"knew grid ready")
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
data={
 "diagnostic_only":True,
 "canonical_source_modified":False,
 "files":{
   "src/widgets/kdirmodel.cpp":{"before":sha(work/"original/kdirmodel.cpp"),"after":sha(kdir)},
   "src/filewidgets/knewfilemenu.cpp":{"before":sha(work/"original/knewfilemenu.cpp"),"after":sha(knew)},
 }
}
out.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
PY
grep -F 'R17|KDIR' "${KDIR}" >/dev/null
grep -F 'R17|KNEW' "${KNEW}" >/dev/null
