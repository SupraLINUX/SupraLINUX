// SPDX-License-Identifier: CC0-1.0
// Public installed SDK: real owned process and private D-Bus sensor traffic.
#include <QCoreApplication>
#include <QGuiApplication>
#include <QDBusInterface>
#include <QDebug>
#include <QElapsedTimer>
#include <QProcess>
#include <QSignalSpy>
#include <QTest>
#include <QThread>
#include <QJsonArray>
#include <QQmlEngine>
#include <QQuickWindow>
#include <QQuickItem>
#include <QTemporaryDir>
#include <KConfig>
#include <KConfigGroup>
#include <cmath>
#include <stdexcept>
#include <unistd.h>
#include <formatter/Formatter.h>
#include <processcore/processes.h>
#include <sensors/Sensor.h>
#include <sensors/SensorDataModel.h>
#include <sensors/SensorTreeModel.h>
#include <systemstats/DBusInterface.h>
#include <systemstats/SensorContainer.h>
#include <systemstats/SensorObject.h>
#include <systemstats/SensorProperty.h>
#include <faces/SensorFaceController.h>

static void require(bool condition, const char *message)
{
    if (!condition) throw std::runtime_error(message);
}
template <class Predicate> static void wait(Predicate predicate, const char *message)
{
    QElapsedTimer deadline;
    deadline.start();
    while (!predicate() && deadline.elapsed() < 8000) {
        QCoreApplication::processEvents();
        QThread::msleep(10);
    }
    require(predicate(), message);
}
struct OwnedProcess {
    QProcess process;
    ~OwnedProcess() {
        if (process.state() != QProcess::NotRunning) {
            process.kill();
            process.waitForFinished(5000);
        }
    }
};

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    try {
        require(argc == 2, "Expected private results directory");
        using namespace KSysGuard;
        require(Formatter::scaleDownFactor(8192, UnitByte, MetricPrefixKilo) == 1024,
                "Installed formatter binary scaling failed");
        require(Formatter::scaleDownFactor(25, UnitPercent, MetricPrefixUnity) == 1,
                "Installed formatter percentage scaling failed");
        require(Formatter::formatValue(8192, UnitByte, MetricPrefixKilo).contains(QStringLiteral("8")),
                "Installed formatter output failed");
        require(!Formatter::symbol(UnitByteRate).isEmpty(), "Installed formatter unit symbol absent");

        OwnedProcess owned;
        owned.process.start(QStringLiteral("/usr/bin/python3"), {
            QStringLiteral("-c"), QStringLiteral("import sys,time; data=bytearray(8*1024*1024); print('ready',flush=True); time.sleep(60)")});
        require(owned.process.waitForStarted(5000) && owned.process.waitForReadyRead(5000),
                "Owned memory process did not start");
        require(owned.process.readAllStandardOutput().contains("ready"), "Owned process readiness missing");
        const auto pid = owned.process.processId();
        require(pid > 0, "Invalid owned PID");
        Processes processes;
        processes.updateAllProcesses(0, Processes::StandardInformation | Processes::IOStatistics | Processes::Smaps);
        auto *process = processes.getProcess(pid);
        require(process && process->pid() == pid && process->parentPid() == getpid(),
                "Installed process collector lost owned PID/parent");
        require(process->uid() == getuid() && process->memory() > 4096,
                "Installed process collector UID/memory failed");
        require(processes.numberProcessorCores() > 0 && processes.totalPhysicalMemory() > 0,
                "Installed process collector machine counters failed");
        owned.process.kill();
        require(owned.process.waitForFinished(5000), "Owned process not reaped");
        // Public collector keeps the Ended state for one scan, then removes it.
        // This also checks the transition used by KDE's upstream process test.
        processes.updateAllProcesses(0);
        require(processes.getProcess(pid) && processes.getProcess(pid)->status() == Process::Ended,
                "Reaped owned PID was not marked Ended");
        processes.updateAllProcesses(0);
        require(processes.getProcess(pid) == nullptr, "Reaped owned PID remained in collector");

        Sensor sensor(QStringLiteral("cpu/all/usage"));
        QSignalSpy updates(&sensor, &Sensor::valueChanged);
        SensorDataModel model({QStringLiteral("cpu/all/usage"), QStringLiteral("memory/physical/used")});
        SensorTreeModel tree;
        wait([&] { return sensor.status() == Sensor::Status::Ready && sensor.value().toDouble() == 25.0
                          && model.isReady() && tree.rowCount() > 0; }, "Installed private sensors did not become ready");
        require(sensor.unit() == UnitPercent && sensor.maximum() == 100 && sensor.minimum() == 0,
                "Installed sensor metadata/unit decode failed");
        require(sensor.name().contains(QStringLiteral("Private sensor")) && !sensor.formattedValue().isEmpty(),
                "Installed sensor name/format failed");
        require(model.columnCount() == 2 && model.headerData(0, Qt::Horizontal, SensorDataModel::SensorId).toString()
                == QStringLiteral("cpu/all/usage"), "Installed sensor model identity failed");
        require(model.headerData(1, Qt::Horizontal, SensorDataModel::Unit).value<KSysGuard::Unit>() == UnitByte,
                "Installed sensor model metadata failed");
        const auto oldUpdates = updates.size();
        QDBusInterface provider(SystemStats::ServiceName, SystemStats::ObjectPath,
                                SystemStats::InterfaceName);
        require(provider.isValid() && provider.call(QStringLiteral("advance")).type() != QDBusMessage::ErrorMessage,
                "Private D-Bus provider control failed");
        wait([&] { return sensor.value().toDouble() == 75 && updates.size() > oldUpdates; },
             "Installed sensor did not receive changed value and signal");
        model.setSensors({QStringLiteral("memory/physical/used"), QStringLiteral("cpu/all/usage")});
        wait([&] { return model.isReady(); }, "Installed reordered sensor model not ready");
        require(model.headerData(0, Qt::Horizontal, SensorDataModel::SensorId).toString()
                == QStringLiteral("memory/physical/used"), "Installed sensor model reorder failed");

        SensorPlugin plugin(nullptr, {});
        auto *container = new SensorContainer(QStringLiteral("private"), QStringLiteral("Private"), &plugin);
        auto *object = new SensorObject(QStringLiteral("owned"), container);
        auto *property = new SensorProperty(QStringLiteral("value"), QStringLiteral("Owned value"), 1.0, object);
        property->setUnit(UnitPercent);
        property->setMin(0);
        property->setMax(100);
        wait([&] { return container->object(QStringLiteral("owned")) == object; },
             "Installed systemstats object registration failed");
        require(property->path() == QStringLiteral("private/owned/value") && property->info().unit == UnitPercent,
                "Installed systemstats property path/metadata failed");
        QSignalSpy propertyUpdates(property, &SensorProperty::valueChanged);
        property->subscribe();
        require(property->isSubscribed() && object->isSubscribed(), "Installed systemstats subscription failed");
        property->setValue(42.0);
        require(propertyUpdates.size() > 0 && property->value().toDouble() == 42.0,
                "Installed systemstats value/signal failed");
        property->unsubscribe();
        require(!property->isSubscribed() && property->value().toDouble() == 1.0,
                "Installed systemstats initial value reset failed");
        container->removeObject(object);
        require(container->object(QStringLiteral("owned")) == nullptr,
                "Installed systemstats explicit object removal failed");
        delete object;

        QTemporaryDir faceState;
        require(faceState.isValid(), "Private face configuration unavailable");
        KConfig config(faceState.path()+QStringLiteral("/face.ini"), KConfig::SimpleConfig);
        auto group = config.group(QStringLiteral("Face"));
        QQmlEngine engine;
        QQuickWindow window;
        window.resize(420, 280);
        SensorFaceController face(group, &engine, &engine);
        face.setFaceId(QStringLiteral("org.kde.ksysguard.textonly"));
        face.setTitle(QStringLiteral("Supra private sensors"));
        face.setHighPrioritySensorIds(QJsonArray{QStringLiteral("cpu/all/usage")});
        face.setLowPrioritySensorIds(QJsonArray{});
        face.setSensorLabels({{QStringLiteral("cpu/all/usage"), QStringLiteral("Private CPU")}});
        wait([&] { return face.availableFacesModel()->rowCount() > 0
                          && face.highPrioritySensorIds().size() == 1; },
             "Installed sensor face/package model did not become ready");
        require(face.faceId() == QStringLiteral("org.kde.ksysguard.textonly")
                && face.title() == QStringLiteral("Supra private sensors") && !face.name().isEmpty(),
                "Installed sensor face package/title metadata failed");
        auto *representation = face.fullRepresentation();
        require(representation, "Installed sensor face QML representation failed");
        representation->setParentItem(window.contentItem());
        representation->setSize(QSizeF(420, 280));
        window.show();
        QTest::qWait(500);
        auto rendered = window.grabWindow();
        require(!rendered.isNull() && rendered.size() == QSize(420, 280),
                "Installed sensor face software rendering failed");
        require(rendered.save(QString::fromLocal8Bit(argv[1])+QStringLiteral("/sensor-face.png")),
                "Installed sensor face image retention failed");
        config.sync();
        require(config.hasGroup(QStringLiteral("Face")), "Installed sensor face private configuration missing");
        representation->setParentItem(nullptr);
        qInfo() << "Installed formatter/process collector, SystemStats lifecycle, private D-Bus sensors/models, SensorFaces package/QML/rendering: PASS";
    } catch (const std::exception &error) {
        qCritical() << error.what();
        return 1;
    }
    return 0;
}
