// SPDX-License-Identifier: CC0-1.0
// Public CLI consumer; every file and D-Bus service belongs to the fixture.
#include <QCoreApplication>
#include <QDBusAbstractAdaptor>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusContext>
#include <QDir>
#include <QElapsedTimer>
#include <QFile>
#include <QImage>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QStandardPaths>
#include <QThread>
#include <QUrl>
#include <functional>

static void require(bool condition,const char *message) { if(!condition)qFatal("fixture assertion: %s",message); }
static void waitFor(const std::function<bool()> &condition,const char *message,int seconds=20)
{
    QElapsedTimer timer;timer.start();
    while(!condition() && timer.elapsed()<seconds*1000) {
        QCoreApplication::processEvents(QEventLoop::AllEvents,30);QThread::msleep(10);
    }
    require(condition(),message);
}
struct Calls { int power=0,screen=0,night=0,notification=0;QStringList peers; };

class Power : public QObject,protected QDBusContext {
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface","org.freedesktop.PowerManagement.Inhibit")
public: Power(QObject *parent,Calls *calls):QObject(parent),calls(calls){}
public Q_SLOTS: uint Inhibit(const QString &application,const QString &reason) {
    require(!application.isEmpty() && reason=="/usr/bin/python3","power call arguments");
    ++calls->power;calls->peers<<message().service();return 101;
}
private: Calls *calls;
};
class Screen : public QObject,protected QDBusContext {
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface","org.freedesktop.ScreenSaver")
public: Screen(QObject *parent,Calls *calls):QObject(parent),calls(calls){}
public Q_SLOTS: uint Inhibit(const QString &application,const QString &reason) {
    require(!application.isEmpty() && reason=="/usr/bin/python3","screen call arguments");
    ++calls->screen;calls->peers<<message().service();return 102;
}
private: Calls *calls;
};
class Night : public QObject,protected QDBusContext {
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface","org.kde.KWin.NightLight")
public: Night(QObject *parent,Calls *calls):QObject(parent),calls(calls){}
public Q_SLOTS: uint inhibit() { ++calls->night;calls->peers<<message().service();return 103; }
private: Calls *calls;
};
class Notifications : public QObject,protected QDBusContext {
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface","org.freedesktop.Notifications")
public: Notifications(QObject *parent,Calls *calls):QObject(parent),calls(calls){}
public Q_SLOTS: uint Inhibit(const QString &application,const QString &reason,const QVariantMap &hints) {
    require(!application.isEmpty() && reason=="/usr/bin/python3" && hints.isEmpty(),"notification call arguments");
    ++calls->notification;calls->peers<<message().service();return 104;
}
private: Calls *calls;
};
class Broadcast : public QObject {
    Q_OBJECT
public: int count=0;QVariantMap received;
public Q_SLOTS: void Notify(const QVariantMap &properties) { ++count;received=properties; }
};
static QByteArray read(const QString &path) { QFile file(path);require(file.open(QIODevice::ReadOnly),"owned file read");return file.readAll(); }
static void write(const QString &path,const QByteArray &bytes) { QFile file(path);require(file.open(QIODevice::WriteOnly|QIODevice::NewOnly),"owned file creation");require(file.write(bytes)==bytes.size(),"complete owned file write"); }

int main(int argc,char **argv)
{
    QCoreApplication app(argc,argv);
    require(argc==2,"expected owned output directory");
    const QString directory=QString::fromLocal8Bit(argv[1]);
    require(QDir(directory).exists(),"owned directory exists");
    const QString address=qEnvironmentVariable("DBUS_SESSION_BUS_ADDRESS");
    require(address.startsWith("unix:path=") && qEnvironmentVariable("DBUS_SYSTEM_BUS_ADDRESS")==address,"both connections use owned fixture bus");
    auto bus=QDBusConnection::sessionBus();
    require(bus.isConnected(),"owned bus connected");
    Calls calls;
    Power power(nullptr,&calls);Screen screen(nullptr,&calls);Night night(nullptr,&calls);Notifications notification(nullptr,&calls);
    const QList<QPair<QString,QPair<QString,QObject *>>> services={
        {"org.freedesktop.PowerManagement.Inhibit",{"/org/freedesktop/PowerManagement/Inhibit",&power}},
        {"org.freedesktop.ScreenSaver",{"/org/freedesktop/ScreenSaver",&screen}},
        {"org.kde.KWin.NightLight",{"/org/kde/KWin/NightLight",&night}},
        {"org.freedesktop.Notifications",{"/org/freedesktop/Notifications",&notification}}};
    for(const auto &service:services) {
        require(bus.registerService(service.first),"owned mock service");
        require(bus.registerObject(service.second.first,service.second.second,QDBusConnection::ExportAllSlots),"owned mock object");
    }
    Broadcast broadcast;
    require(QDBusConnection::systemBus().connect({},"/org/kde/kbroadcastnotification","org.kde.BroadcastNotifications","Notify",&broadcast,SLOT(Notify(QVariantMap))),"owned broadcast listener");
    int commands=0;
    auto run=[&](const QString &name,const QStringList &arguments,const QByteArray &input=QByteArray()) {
        const QString executable=QStandardPaths::findExecutable(name);
        require(!executable.isEmpty(),"installed tool exists");
        QProcess process;process.setWorkingDirectory(directory);process.start(executable,arguments);
        require(process.waitForStarted(3000),"installed tool started");
        process.write(input);process.closeWriteChannel();
        waitFor([&]{return process.state()==QProcess::NotRunning;},"installed tool finished");
        const QByteArray stdoutBytes=process.readAllStandardOutput(),stderrBytes=process.readAllStandardError();
        const QString prefix=directory+QString("/command-%1-%2").arg(++commands).arg(name);
        write(prefix+"-stdout",stdoutBytes);write(prefix+"-stderr",stderrBytes);
        require(process.exitStatus()==QProcess::NormalExit && process.exitCode()==0,"installed tool successful exit");
        return stdoutBytes;
    };
    const QByteArray text="SupraLINUX owned local file fixture\n";
    write(directory+"/source.txt",text);
    const QByteArray svg="<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"40\" height=\"20\"><rect width=\"20\" height=\"20\" fill=\"#ff0000\"/><rect x=\"20\" width=\"20\" height=\"20\" fill=\"#0000ff\"/></svg>";
    write(directory+"/fixture.svg",svg);
    require(run("kmimetypefinder",{directory+"/source.txt"}).trimmed()=="text/plain","actual text MIME");
    require(run("kmimetypefinder",{"--content",directory+"/fixture.svg"}).trimmed()=="image/svg+xml","actual SVG MIME");
    run("ksvgtopng",{"20","10",directory+"/fixture.svg",directory+"/render.png"});
    QImage image(directory+"/render.png");
    require(image.size()==QSize(20,10) && image.pixelColor(2,2)==QColor("#ff0000") && image.pixelColor(18,8)==QColor("#0000ff"),"actual SVG pixels and dimensions");
    require(run("kmimetypefinder",{"-"},read(directory+"/render.png")).trimmed()=="image/png","actual stdin MIME");
    const QString source=QUrl::fromLocalFile(directory+"/source.txt").toString();
    const QString copy=QUrl::fromLocalFile(directory+"/copy.txt").toString();
    const QString moved=QUrl::fromLocalFile(directory+"/moved.txt").toString();
    require(run("kioclient",{"--noninteractive","cat",source})==text,"actual KIO local read");
    run("kdecp",{"--noninteractive",source,copy});require(read(directory+"/copy.txt")==text,"actual KIO local copy");
    run("kdemv",{"--noninteractive",copy,moved});require(!QFile::exists(directory+"/copy.txt") && read(directory+"/moved.txt")==text,"actual KIO local move");
    require(run("kmimetypefinder5",{directory+"/moved.txt"}).trimmed()=="text/plain","compatibility CLI link");
    write(directory+"/child.py","from pathlib import Path\nimport sys,time\ntime.sleep(.15)\nPath(sys.argv[1]).write_text('owned child completed\\n')\n");
    run("kde-inhibit",{"--power","--screenSaver","--colorCorrect","--notifications","/usr/bin/python3",directory+"/child.py",directory+"/child-result"});
    require(read(directory+"/child-result")=="owned child completed\n","inhibited command actually completed");
    require(calls.power==1 && calls.screen==1 && calls.night==1 && calls.notification==1,"four actual typed inhibit calls");
    for(const QString &peer:calls.peers) {
        require(peer.startsWith(':'),"actual tool bus sender");
        waitFor([&]{return !bus.interface()->isServiceRegistered(peer).value();},"tool connection released on exit");
    }
    run("kbroadcastnotification",{"--application","SupraFixture","--summary","Owned notification","--uids","424242","--timeout","1000","Owned body"});
    waitFor([&]{return broadcast.count==1;},"actual private broadcast signal");
    require(broadcast.received.value("appName")=="SupraFixture" && broadcast.received.value("summary")=="Owned notification"
        && broadcast.received.value("body")=="Owned body" && broadcast.received.value("uids").toStringList()==QStringList{"424242"}
        && broadcast.received.value("timeout").toInt()==1000,"actual broadcast payload");
    for(const auto &service:services) {
        bus.unregisterObject(service.second.first);require(bus.unregisterService(service.first),"owned mock service cleanup");
    }
    const QJsonObject result{{"state","PASS"},{"scope","installed public CLI against owned files and D-Bus fixtures"},
        {"commands",commands},{"inhibit_calls",4},{"broadcast_signals",broadcast.count},
        {"hardware_access",false},{"privilege_authorization",false}};
    printf("%s\n",QJsonDocument(result).toJson(QJsonDocument::Compact).constData());return 0;
}
#include "main.moc"
