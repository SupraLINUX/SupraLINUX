#include <KDEDModule>
#include <KPluginFactory>
#include <KPluginMetaData>
#include <QApplication>
#include <KQuickConfigModule>
#include <QQuickItem>
#include <QQuickWindow>
#include <QAbstractItemModel>
#include <QDBusConnection>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QThread>
#include <QSet>
#include <functional>
#include <memory>
#include <iostream>
#include "fakeserver.h"
#include "fakemanager.h"
#include "fakedevice.h"

class Notifications : public QObject {
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface","org.freedesktop.Notifications")
public:
    struct Message {uint id;QString title,body;QStringList actions;};
    QList<Message> messages;
public Q_SLOTS:
    QStringList GetCapabilities(){return {QStringLiteral("body"),QStringLiteral("actions"),QStringLiteral("persistence")};}
    uint Notify(const QString &,uint,const QString &,const QString &title,const QString &body,const QStringList &actions,const QVariantMap &,int){
        uint id=uint(messages.size()+1);messages.append({id,title,body,actions});return id;
    }
    QString GetServerInformation(QString &vendor,QString &version,QString &specVersion){vendor=QStringLiteral("SupraLINUX");version=QStringLiteral("1");specVersion=QStringLiteral("1.2");return QStringLiteral("Private notification fixture");}
    void CloseNotification(uint id){Q_EMIT NotificationClosed(id,3);}
Q_SIGNALS:
    void ActionInvoked(uint id,const QString &key);
    void NotificationClosed(uint id,uint reason);
};
static bool until(const std::function<bool()> &ready,int milliseconds=6000){
    QElapsedTimer timer;timer.start();while(!ready() && timer.elapsed()<milliseconds){QCoreApplication::processEvents(QEventLoop::AllEvents,100);QThread::msleep(10);}return ready();
}
static void settle(int milliseconds){QElapsedTimer t;t.start();while(t.elapsed()<milliseconds){QCoreApplication::processEvents(QEventLoop::AllEvents,100);QThread::msleep(10);}}
int main(int argc,char **argv){
    qputenv("KBOLT_FAKE","1");QApplication app(argc,argv);
    auto fail=[](const char *name){std::cerr<<"Installed Bolt module fixture failed: "<<name<<'\n';return 1;};
    if(argc!=3)return fail("module path");
    Notifications notifications;auto bus=QDBusConnection::sessionBus();
    if(!bus.registerObject(QStringLiteral("/org/freedesktop/Notifications"),&notifications,QDBusConnection::ExportAllSlots|QDBusConnection::ExportAllSignals) || !bus.registerService(QStringLiteral("org.freedesktop.Notifications")))return fail("private notifications");
    FakeServer server;auto manager=server.manager();manager->setAuthMode(QStringLiteral("enabled"));
    auto loaded=KPluginFactory::instantiatePlugin<KDEDModule>(KPluginMetaData(QString::fromLocal8Bit(argv[1])),nullptr);
    if(!loaded){std::cerr<<loaded.errorText.toStdString();return fail("actual installed KDED plugin");}
    std::unique_ptr<KDEDModule> module(loaded.plugin);settle(300);
    auto make=[](const char *uid,const char *name,const char *status){auto device=std::make_unique<FakeDevice>(QString::fromLatin1(uid));device->setName(QString::fromLatin1(name));device->setLabel(QString::fromLatin1(name));device->setVendor(QStringLiteral("Synthetic Vendor"));device->setType(QStringLiteral("peripheral"));device->setStatus(QString::fromLatin1(status));device->setAuthFlags(QStringLiteral("none"));return device;};
    auto temporary=manager->addDevice(make("SupraTemp","Synthetic Temporary Device","connected"));
    if(!until([&]{return notifications.messages.size()==1;}))return fail("actual unauthorized-device notification");
    const auto notification=notifications.messages.front();
    if(!notification.body.contains(QStringLiteral("Synthetic Temporary Device")) || notification.actions.size()<4)return fail("actual notification device and actions");
    auto choose=[&](const Notifications::Message &message,const QString &label){for(qsizetype i=0;i+1<message.actions.size();i+=2){if(message.actions[i+1]==label){Q_EMIT notifications.ActionInvoked(message.id,message.actions[i]);return true;}}return false;};
    if(!choose(notification,QStringLiteral("Authorize Now")))return fail("temporary authorization action");
    if(!until([&]{return temporary->status()==QStringLiteral("authorized");}) || temporary->stored())return fail("actual temporary D-Bus authorization");
    QSet<QString> flags;for(const auto &part:temporary->authFlags().split('|'))flags.insert(part.trimmed());
    if(flags!=QSet<QString>{QStringLiteral("boot"),QStringLiteral("nokey")})return fail("temporary authorization flags");
    const int before=notifications.messages.size();
    manager->addDevice(make("SupraAlready","Synthetic Already Authorized","authorized"));settle(800);
    if(notifications.messages.size()!=before)return fail("already authorized device notification suppression");
    auto permanent=manager->addDevice(make("SupraPermanent","Synthetic Permanent Device","connected"));
    if(!until([&]{return notifications.messages.size()==before+1;}))return fail("permanent-device notification");
    if(!choose(notifications.messages.back(),QStringLiteral("Authorize Permanently")))return fail("permanent enrollment action");
    if(!until([&]{return permanent->stored() && permanent->status()==QStringLiteral("authorized");}) || permanent->policy()!=QStringLiteral("auto"))return fail("actual manager D-Bus enrollment");
    flags.clear();for(const auto &part:permanent->authFlags().split('|'))flags.insert(part.trimmed());
    if(flags!=QSet<QString>{QStringLiteral("boot"),QStringLiteral("nokey")})return fail("permanent authorization flags");
    module.reset();settle(100);
    auto kcmLoaded=KQuickConfigModuleLoader::loadModule(KPluginMetaData(QString::fromLocal8Bit(argv[2])));
    if(!kcmLoaded){std::cerr<<kcmLoaded.errorText.toStdString();return fail("actual installed KCM plugin");}
    std::unique_ptr<KQuickConfigModule> kcm(kcmLoaded.plugin);
    QQuickItem *ui=nullptr;
    if(!until([&]{ui=kcm->mainUi();return ui!=nullptr;})){std::cerr<<kcm->errorString().toStdString();return fail("actual installed KCM QML load");}
    auto view=ui->property("view").value<QObject*>();
    if(!view)return fail("actual KCM device list view");
    if(!until([&]{return view->property("count").toInt()==3;}))return fail("actual KCM private device model");
    if(!view->property("enabled").toBool())return fail("actual enabled KCM device list");
    auto model=view->property("deviceModel").value<QObject*>();
    auto boltManager=model?model->property("manager").value<QObject*>():nullptr;
    if(!boltManager || !boltManager->property("isAvailable").toBool())return fail("KCM private Bolt provider availability");
    QQuickWindow window;window.resize(800,600);ui->setParentItem(window.contentItem());ui->setWidth(800);ui->setHeight(600);window.show();
    auto hasLabel=[&](){QList<QQuickItem*> pending{ui};while(!pending.isEmpty()){auto item=pending.takeFirst();if(item->property("text").toString()==QStringLiteral("Synthetic Temporary Device"))return true;pending.append(item->childItems());}return false;};
    if(!until(hasLabel))return fail("actual rendered KCM device label");
    manager->removeDevice(QStringLiteral("SupraAlready"));
    if(!until([&]{return view->property("count").toInt()==2;}))return fail("actual KCM device removal");
    kcm.reset();settle(100);
    std::cout<<"Installed Thunderbolt KDED plugin, real private device notifications, temporary authorization, permanent enrollment, authorized-device suppression, actual rendered KCM QML and dynamic device model: PASS\n";
    return 0;
}
#include "main.moc"
