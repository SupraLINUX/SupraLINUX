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
#include <X11/Xlib.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
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
static void stroke(Display *display)
{
    const KeySym keys[]={XK_Control_L,XK_Alt_L,XK_k};
    for (auto key:keys) check(XTestFakeKeyEvent(display,XKeysymToKeycode(display,key),True,20),"Private XTEST key press failed");
    for (int i=2;i>=0;--i) check(XTestFakeKeyEvent(display,XKeysymToKeycode(display,keys[i]),False,20),"Private XTEST key release failed");
    XSync(display,False);
}
int main(int argc,char **argv)
{
    try {
        QApplication app(argc,argv); app.setApplicationName(QStringLiteral("org.supralinux.shortcut-fixture"));
        check(qEnvironmentVariable("SUPRA_PRIVATE_XVFB_DISPLAY")==qEnvironmentVariable("DISPLAY"),"Private Xvfb display admission absent");
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
        auto display=std::unique_ptr<Display,decltype(&XCloseDisplay)>(XOpenDisplay(nullptr),XCloseDisplay);
        check(display!=nullptr,"Private Xvfb connection absent");
        QWidget window; window.resize(200,100); window.show(); app.processEvents();
        XSetInputFocus(display.get(),window.winId(),RevertToParent,CurrentTime); XSync(display.get(),False);
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
        std::cout<<"Ubuntu KGlobalAccel SDK and actual installed daemon: QAction trigger, legacy D-Bus/defaults/conflict, block/unblock and removal PASS\n";
    } catch (const std::exception &error) { std::cerr<<error.what()<<'\n'; return 1; }
}
