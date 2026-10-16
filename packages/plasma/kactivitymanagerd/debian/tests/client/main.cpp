// SPDX-License-Identifier: CC0-1.0
#include <PlasmaActivities/Controller>
#include <PlasmaActivities/Info>
#include <PlasmaActivities/ActivitiesModel>
#include <QGuiApplication>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QThread>
#include <QQmlEngine>
#include <QQmlComponent>
#include <QUuid>
#include <QDBusInterface>
#include <QDBusReply>
#include <QFile>
#include <QDir>
#include <iostream>
#include <memory>
template<class Predicate> bool until(Predicate condition) {
    QElapsedTimer timer;timer.start();
    while (!condition() && timer.elapsed()<10000) {
        QCoreApplication::processEvents(QEventLoop::AllEvents,100);
        QThread::msleep(10);
    }
    return condition();
}
template<class T> bool ready(QFuture<T> &future) { return until([&](){return future.isFinished();}); }
int main(int argc,char **argv) {
    QGuiApplication app(argc,argv);
    app.setProperty("org.kde.KActivities.core.disableAutostart",true);
    const auto fail=[](const char *check){std::cerr<<"Activities client check failed: "<<check<<'\n';return 1;};
    KActivities::Controller controller;
    if (argc>1 && QString::fromLocal8Bit(argv[1])==QStringLiteral("--offline")) {
        const QString nullid=QStringLiteral("00000000-0000-0000-0000-000000000000");
        if (!until([&](){return controller.serviceStatus()==KActivities::Consumer::NotRunning;}) ||
            controller.currentActivity()!=nullid || controller.activities()!=QStringList{nullid}) return fail("offline status and null activity");
        auto rejected=controller.addActivity(QStringLiteral("must-not-create"));
        auto selected=controller.setCurrentActivity(QStringLiteral("invalid"));
        if (!ready(rejected) || !rejected.result().isEmpty() || !ready(selected) || selected.result()) return fail("offline futures");
        std::cout<<"Public offline status, null activity and rejected futures: PASS\n";return 0;
    }
    if (!until([&](){return controller.serviceStatus()==KActivities::Consumer::Running;}) || controller.currentActivity().isEmpty()) return fail("real daemon availability");
    const QString agent=QStringLiteral("org.supralinux.private-test");
    const QString resource=QString::fromLocal8Bit(qgetenv("XDG_DATA_HOME"))+QStringLiteral("/private-resource.txt");
    QDBusInterface linking(QStringLiteral("org.kde.ActivityManager"), QStringLiteral("/ActivityManager/Resources/Linking"), QStringLiteral("org.kde.ActivityManager.ResourcesLinking"));
    if (!linking.isValid()) return fail("actual installed SQLite resource-linking plugin unavailable");
    const auto linked=[&](const QString &id) { QDBusReply<bool> reply=linking.call(QStringLiteral("IsResourceLinkedToActivity"),agent,resource,id); return reply.isValid() && reply.value(); };
    const auto link=[&](const QString &method,const QString &id) { return linking.call(method,agent,resource,id).type()!=QDBusMessage::ErrorMessage; };
    const QString statePath=QString::fromLocal8Bit(qgetenv("XDG_STATE_HOME"))+QStringLiteral("/fixture-state");
    if (argc>1 && QString::fromLocal8Bit(argv[1])==QStringLiteral("--verify-persistence")) {
        QFile state(statePath);if (!state.open(QIODevice::ReadOnly)) return fail("private state absent");
        const QString id=QString::fromUtf8(state.readLine()).trimmed();
        KActivities::Info persisted(id);
        if (QUuid(id).isNull() || !controller.activities().contains(id) || !until([&](){return persisted.name()==QStringLiteral("persisted") && persisted.description()==QStringLiteral("private compatibility test") && persisted.icon()==QStringLiteral("folder");}) || !linked(id)) return fail("activity metadata and SQLite link did not survive actual daemon restart");
        if (!link(QStringLiteral("UnlinkResourceFromActivity"),id) || linked(id)) return fail("persistent link removal failed");
        auto removed=controller.removeActivity(id);if (!ready(removed) || !until([&](){return !controller.activities().contains(id);})) return fail("persistent activity cleanup failed");
        std::cout<<"Actual daemon restart preserved activity metadata and SQLite resource link; cleanup: PASS\n";return 0;
    }
    QFile resourceFile(resource);if (!resourceFile.open(QIODevice::WriteOnly) || resourceFile.write("private fixture\n")<=0) return fail("private resource creation failed");resourceFile.close();
    const auto original=controller.currentActivity();
    QString added,removed,current;
    QObject::connect(&controller,&KActivities::Consumer::activityAdded,[&](const QString &id){added=id;});
    QObject::connect(&controller,&KActivities::Consumer::activityRemoved,[&](const QString &id){removed=id;});
    QObject::connect(&controller,&KActivities::Consumer::currentActivityChanged,[&](const QString &id){current=id;});
    auto created=controller.addActivity(QStringLiteral("SupraLINUX test"));
    if (!ready(created)) return fail("create future timeout");
    const auto id=created.result();
    if (QUuid(id).isNull() || !until([&](){return added==id && controller.activities().contains(id);})) return fail("created UUID and addition signal");
    KActivities::Info info(id);
    KActivities::ActivitiesModel model;
    auto name=controller.setActivityName(id,QStringLiteral("renamed"));
    auto description=controller.setActivityDescription(id,QStringLiteral("private compatibility test"));
    auto icon=controller.setActivityIcon(id,QStringLiteral("folder"));
    if (!ready(name) || !ready(description) || !ready(icon) ||
        !until([&](){return info.availability()!=KActivities::Info::Nothing && info.name()==QStringLiteral("renamed") && info.description()==QStringLiteral("private compatibility test") && info.icon()==QStringLiteral("folder");})) return fail("metadata futures and Info refresh");
    auto selected=controller.setCurrentActivity(id);
    if (!ready(selected) || !selected.result() || !until([&](){return current==id && info.isCurrent() && controller.currentActivity()==id;})) return fail("current activity future and signal");
    if (!until([&](){for(int row=0;row<model.rowCount();++row) if(model.data(model.index(row,0),KActivities::ActivitiesModel::ActivityId).toString()==id) return true;return false;})) return fail("C++ activity model");
    QQmlEngine engine;QQmlComponent component(&engine);
    component.setData("import org.kde.activities 0.1\nActivityInfo {}",QUrl());
    if (component.isError()) {std::cerr<<component.errorString().toStdString();return fail("installed QML plugin");}
    std::unique_ptr<QObject> qml(component.createWithInitialProperties({{QStringLiteral("activityId"),id}}));
    if (!qml || !until([&](){return qml->property("valid").toBool() && qml->property("name").toString()==QStringLiteral("renamed") && qml->property("description").toString()==QStringLiteral("private compatibility test") && qml->property("icon").toString()==QStringLiteral("folder");})) return fail("QML activity metadata");
    auto restore=controller.setCurrentActivity(original);
    if (!ready(restore) || !restore.result() || !until([&](){return controller.currentActivity()==original;})) return fail("restore original activity");
    if (!link(QStringLiteral("LinkResourceToActivity"),id) || !linked(id)) return fail("actual SQLite link creation failed");
    if (!link(QStringLiteral("UnlinkResourceFromActivity"),id) || linked(id)) return fail("actual SQLite link removal failed");
    if (!link(QStringLiteral("LinkResourceToActivity"),id) || !linked(id)) return fail("actual SQLite persistent link creation failed");
    auto persistedName=controller.setActivityName(id,QStringLiteral("persisted"));if (!ready(persistedName) || !until([&](){return info.name()==QStringLiteral("persisted");})) return fail("persistent activity name failed");
    QFile state(statePath);if (!state.open(QIODevice::WriteOnly) || state.write(id.toUtf8()+"\n")<=0) return fail("private fixture state creation failed");state.close();
    const QString configPath=QString::fromLocal8Bit(qgetenv("XDG_CONFIG_HOME"))+QStringLiteral("/kactivitymanagerdrc");
    if (!until([&](){QFile config(configPath);return config.open(QIODevice::ReadOnly) && config.readAll().contains(id.toUtf8()+"=persisted");})) return fail("daemon did not flush its documented delayed activity configuration");
    std::cout<<"Real private daemon, create/rename/select/restore futures and signals, C++ model, QML plugin and SQLite linking: PASS\n";
    return 0;
}
