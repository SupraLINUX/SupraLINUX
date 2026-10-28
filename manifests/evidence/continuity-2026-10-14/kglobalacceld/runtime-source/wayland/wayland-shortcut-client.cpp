// SPDX-License-Identifier: CC0-1.0
#include <KGlobalAccel>
#include <QAction>
#include <QApplication>
#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusMetaType>
#include <QDBusReply>
#include <QElapsedTimer>
#include <QThread>
#include <QWidget>
#include <QWindow>
#include <wayland-client.h>
#include "fake-input-client.h"
#include <linux/input-event-codes.h>
#include <algorithm>
#include <functional>
#include <iostream>
#include <memory>
#include <stdexcept>

static void check(bool ok, const char *why) { if (!ok) throw std::runtime_error(why); }
static bool waitFor(const std::function<bool()> &predicate, int timeout=3000)
{
    QElapsedTimer timer; timer.start();
    do { QApplication::processEvents(); if (predicate()) return true; QThread::msleep(10); } while (timer.elapsed()<timeout);
    return false;
}
struct wl_display;
static org_kde_kwin_fake_input *fake = nullptr;
static void global(void *, wl_registry *registry, uint32_t name, const char *interface, uint32_t version)
{
    if (std::string(interface)=="org_kde_kwin_fake_input" && version>=4)
        fake=static_cast<org_kde_kwin_fake_input *>(wl_registry_bind(registry,name,&org_kde_kwin_fake_input_interface,std::min(version,6u)));
}
static void removed(void *,wl_registry *,uint32_t) {}
static const wl_registry_listener listener={global,removed};
static void stroke(wl_display *display)
{
    const uint32_t keys[]={KEY_LEFTCTRL,KEY_LEFTALT,KEY_K};
    for (auto key:keys) org_kde_kwin_fake_input_keyboard_key(fake,key,1);
    for (int i=2;i>=0;--i) org_kde_kwin_fake_input_keyboard_key(fake,keys[i],0);
    check(wl_display_roundtrip(display)>=0,"Owned virtual Wayland key roundtrip failed");
}

int main(int argc,char **argv)
{
    try {
        QApplication app(argc,argv); app.setApplicationName(QStringLiteral("org.supralinux.shortcut-fixture"));
        check(!qEnvironmentVariable("SUPRA_PRIVATE_WAYLAND_SOCKET").isEmpty() && qEnvironmentVariable("SUPRA_PRIVATE_WAYLAND_SOCKET")==qEnvironmentVariable("WAYLAND_DISPLAY"),"Owned private Wayland socket admission absent");
        QDBusInterface daemon(QStringLiteral("org.kde.kglobalaccel"),QStringLiteral("/kglobalaccel"),QStringLiteral("org.kde.KGlobalAccel"));
        check(waitFor([&]{return daemon.isValid();}),"Private installed daemon did not register");
        QAction action; action.setObjectName(QStringLiteral("private-key")); action.setText(QStringLiteral("Private shortcut fixture"));
        const QKeySequence key(Qt::CTRL|Qt::ALT|Qt::Key_K);
        auto *accel=KGlobalAccel::self();
        check(accel->setDefaultShortcut(&action,{key}),"Ubuntu SDK default shortcut rejected");
        check(accel->setShortcut(&action,{key},KGlobalAccel::NoAutoloading),"Ubuntu SDK active shortcut rejected");
        check(accel->shortcut(&action)==QList<QKeySequence>{key},"Assigned Ubuntu SDK shortcut differs");
        check(accel->defaultShortcut(&action)==QList<QKeySequence>{key},"Assigned Ubuntu SDK default differs");
        const QStringList id{app.applicationName(),action.objectName(),app.applicationName(),action.text()};
        qDBusRegisterMetaType<QList<int>>();
        QDBusReply<QList<int>> legacy=daemon.call(QStringLiteral("shortcut"),id);
        check(legacy.isValid() && legacy.value()==QList<int>{key[0].toCombined()},"Legacy Ubuntu D-Bus shortcut differs");
        QDBusReply<QList<int>> defaults=daemon.call(QStringLiteral("defaultShortcut"),id);
        check(defaults.isValid() && defaults.value()==legacy.value(),"Legacy Ubuntu D-Bus default differs");
        QDBusReply<bool> available=daemon.call(QStringLiteral("isGlobalShortcutAvailable"),key[0].toCombined(),QStringLiteral("another-component"));
        check(available.isValid() && !available.value(),"Private shortcut conflict not detected");
        int triggers=0; QObject::connect(&action,&QAction::triggered,[&]{++triggers;});
        auto display=std::unique_ptr<wl_display,decltype(&wl_display_disconnect)>(wl_display_connect(nullptr),wl_display_disconnect);
        check(display!=nullptr,"Owned virtual Wayland connection absent");
        auto registry=wl_display_get_registry(display.get());
        wl_registry_add_listener(registry,&listener,nullptr);
        check(wl_display_roundtrip(display.get())>=0 && fake,"Owned virtual fake input protocol absent");
        org_kde_kwin_fake_input_authenticate(fake,"SupraLINUX owned offline KVM diagnostic","Test own shortcuts on virtual compositor only");
        check(wl_display_roundtrip(display.get())>=0,"Owned input authentication roundtrip failed");
        QWidget window; window.resize(200,100); window.show(); app.processEvents();
        check(waitFor([&]{return window.windowHandle() && window.windowHandle()->isExposed();}),"Owned virtual Wayland window was not exposed");
        if (app.arguments().contains(QStringLiteral("--probe"))) { std::cout<<"Owned Wayland permission, fake input and exposed Qt window PASS\n"; return 0; }
        waitFor([]{return false;},1000);
        stroke(display.get()); check(waitFor([&]{return triggers==1;}),"Actual global key did not trigger QAction");
        QDBusReply<void> blocked=daemon.call(QStringLiteral("blockGlobalShortcuts"),true); check(blocked.isValid(),"Private global blocking failed");
        stroke(display.get()); waitFor([]{return false;},300); check(triggers==1,"Blocked global key triggered QAction");
        QDBusReply<void> unblocked=daemon.call(QStringLiteral("blockGlobalShortcuts"),false); check(unblocked.isValid(),"Private global unblocking failed");
        stroke(display.get()); check(waitFor([&]{return triggers==2;}),"Unblocked global key did not trigger QAction");
        accel->removeAllShortcuts(&action);
        QDBusReply<bool> released=daemon.call(QStringLiteral("isGlobalShortcutAvailable"),key[0].toCombined(),QStringLiteral("another-component"));
        check(released.isValid() && released.value(),"Private shortcut removal did not release key");
        stroke(display.get()); waitFor([]{return false;},300); check(triggers==2,"Removed global key triggered QAction");
        std::cout<<"Owned Qt/KGlobalAccel public client and original Ubuntu virtual KWin: QAction trigger, legacy D-Bus/defaults/conflict, block/unblock and removal PASS\n";
    } catch (const std::exception &error) { std::cerr<<error.what()<<'\n'; return 1; }
}
