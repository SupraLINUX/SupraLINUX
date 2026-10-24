// SPDX-License-Identifier: CC0-1.0
// Private provider using the actual public SDK's registered D-Bus types.
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusMetaType>
#include <QSet>
#include <QTimer>
#include <systemstats/DBusInterface.h>
#include <systemstats/SensorInfo.h>

using StatsInfo = KSysGuard::SensorInfoMap;
using StatsData = KSysGuard::SensorDataList;

class StatsProvider : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.kde.ksystemstats1")
public:
    StatsProvider()
    {
        const QList<QPair<QString, KSysGuard::Unit>> seeds = {
            {QStringLiteral("cpu/all/usage"), KSysGuard::UnitPercent},
            {QStringLiteral("memory/physical/used"), KSysGuard::UnitByte},
            {QStringLiteral("network/all/download"), KSysGuard::UnitByteRate},
            {QStringLiteral("disk/all/used"), KSysGuard::UnitByte},
        };
        for (const auto &seed : seeds) {
            KSysGuard::SensorInfo info;
            info.name = QStringLiteral("Private sensor ")+seed.first;
            info.shortName = seed.first;
            info.description = QStringLiteral("SupraLINUX private integration fixture");
            info.variantType = QVariant::Double;
            info.unit = seed.second;
            info.min = 0;
            info.max = seed.second == KSysGuard::UnitPercent ? 100 : 1048576;
            metadata.insert(seed.first, info);
            values.insert(seed.first, seed.second == KSysGuard::UnitPercent ? 25.0 : 4096.0);
        }
        connect(&timer, &QTimer::timeout, this, [this] {
            emit newSensorData(sensorData(subscribed.keys()));
        });
        timer.start(100);
    }
public Q_SLOTS:
    StatsInfo allSensors() const { return metadata; }
    StatsInfo sensors(const QStringList &ids) const
    {
        StatsInfo result;
        for (const auto &id : ids) if (metadata.contains(id)) result.insert(id, metadata.value(id));
        return result;
    }
    StatsData sensorData(const QStringList &ids) const
    {
        StatsData result;
        for (const auto &id : ids) if (values.contains(id)) result.append(KSysGuard::SensorData(id, values.value(id)));
        return result;
    }
    void subscribe(const QStringList &ids) { for (const auto &id : ids) ++subscribed[id]; }
    void unsubscribe(const QStringList &ids)
    {
        for (const auto &id : ids) {
            auto entry = subscribed.find(id);
            if (entry != subscribed.end() && --entry.value() <= 0) subscribed.erase(entry);
        }
    }
    void advance()
    {
        values[QStringLiteral("cpu/all/usage")] = 75.0;
        values[QStringLiteral("memory/physical/used")] = 8192.0;
        emit newSensorData(sensorData(subscribed.keys()));
    }
Q_SIGNALS:
    void sensorAdded(const QString &id);
    void sensorRemoved(const QString &id);
    void sensorMetaDataChanged(const StatsInfo &info);
    void newSensorData(const StatsData &data);
private:
    StatsInfo metadata;
    QHash<QString, QVariant> values;
    QHash<QString, int> subscribed;
    QTimer timer;
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    qDBusRegisterMetaType<KSysGuard::SensorInfo>();
    qDBusRegisterMetaType<KSysGuard::SensorData>();
    qDBusRegisterMetaType<StatsInfo>();
    qDBusRegisterMetaType<StatsData>();
    auto bus = QDBusConnection::sessionBus();
    StatsProvider provider;
    // The installed public SDK uses the versioned service/path. The alias is
    // required by the upstream autotests' legacy daemon-presence checks.
    if (!bus.registerService(KSysGuard::SystemStats::ServiceName)
        || !bus.registerService(QStringLiteral("org.kde.ksystemstats"))
        || !bus.registerObject(KSysGuard::SystemStats::ObjectPath, &provider,
                               QDBusConnection::ExportAllSlots | QDBusConnection::ExportAllSignals)
        || !bus.registerObject(QStringLiteral("/"), &provider,
                               QDBusConnection::ExportAllSlots | QDBusConnection::ExportAllSignals)) return 1;
    return app.exec();
}
#include "stats-server.moc"
