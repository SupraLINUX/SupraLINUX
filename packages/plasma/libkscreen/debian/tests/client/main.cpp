#include <kscreen/config.h>
#include <kscreen/configmonitor.h>
#include <kscreen/edid.h>
#include <kscreen/getconfigoperation.h>
#include <kscreen/mode.h>
#include <kscreen/output.h>
#include <kscreen/screen.h>
#include <kscreen/setconfigoperation.h>
#include <KScreenDpms/Dpms>
#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusReply>
#include <QDeadlineTimer>
#include <QEventLoop>
#include <QGuiApplication>
#include <QThread>
#include <functional>
#include <iostream>
#include <stdexcept>
static void require(bool value, const char *message) { if (!value) throw std::runtime_error(message); }
static void waitFor(const std::function<bool()> &ready, const char *message) {
    QDeadlineTimer deadline(8000);
    while (!ready() && !deadline.hasExpired()) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 20);
        QThread::msleep(1);
    }
    require(ready(), message);
}
static KScreen::ConfigPtr getConfig() {
    auto *operation = new KScreen::GetConfigOperation;
    require(operation->exec(), "Installed GetConfigOperation failed");
    auto config = operation->config();
    require(config && config->isValid(), "Installed backend configuration invalid");
    return config;
}
int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    try {
        require(argc == 2 || (argc == 3 && QString::fromLocal8Bit(argv[2]) == QStringLiteral("xrandr")), "Expected private profile path and optional xrandr mode");
        require(QGuiApplication::platformName() == QStringLiteral("xcb"), "Expected owned Xvfb platform");
        auto bus = QDBusConnection::sessionBus();
        require(bus.isConnected(), "Private D-Bus connection failed");
        QDBusInterface launcher(QStringLiteral("org.kde.KScreen"), QStringLiteral("/"), QStringLiteral("org.kde.KScreen"), bus);
        require(launcher.isValid(), "Installed backend launcher unavailable");
        if (argc == 3) {
            QDBusReply<bool> started = launcher.call(QStringLiteral("requestBackend"), QStringLiteral("XRandR"), QVariantMap{});
            require(started.isValid() && started.value(), "Installed XRandR backend did not load");
            auto actual = getConfig();
            require(actual->screen()->currentSize() == QSize(1280, 800) && actual->outputs().size() == 1, "Owned Xvfb XRandR discovery mismatch");
            auto screen = actual->outputs().first();
            require(screen->isConnected() && screen->isEnabled() && screen->currentMode() && screen->currentMode()->size() == QSize(1280, 800), "Owned Xvfb XRandR output/mode mismatch");
            KScreen::Dpms dpms;
            require(!dpms.isSupported() && !dpms.hasPendingChanges(), "Owned Xvfb DPMS properties mismatch");
            std::cout << "Installed KScreen XRandR backend on private Xvfb, screen/output/mode discovery and unsupported ScreenDpms properties: PASS\n";
            launcher.call(QStringLiteral("quit"));
            return 0;
        }
        QVariantMap args{{QStringLiteral("TEST_DATA"), QString::fromLocal8Bit(argv[1])}};
        QDBusReply<bool> reply = launcher.call(QStringLiteral("requestBackend"), QStringLiteral("Fake"), args);
        require(reply.isValid() && reply.value(), "Installed Fake backend did not load");
        auto config = getConfig();
        require(config->outputs().size() == 1 && config->screen()->currentSize() == QSize(1280, 800), "Initial screen geometry mismatch");
        auto output = config->output(1);
        require(output && output->name() == QStringLiteral("SUPRA1") && output->isConnected() && output->isEnabled(), "Initial output identity/state mismatch");
        require(output->currentModeId() == QStringLiteral("3") && output->currentMode()->size() == QSize(1280, 800) && output->modes().size() == 2, "Initial modes mismatch");
        require(output->edid() && output->edid()->isValid() && output->edid()->name() == QStringLiteral("SupraScreen"), "EDID response/parser mismatch");
        auto clone = config->clone();
        clone->output(1)->setPos(QPoint(100, 50));
        require(output->pos() == QPoint(0, 0), "Configuration clone shares mutable output");
        auto *monitor = KScreen::ConfigMonitor::instance();
        monitor->addConfig(config);
        int monitorSignals = 0, connectedSignals = 0;
        QObject::connect(monitor, &KScreen::ConfigMonitor::configurationChanged, [&] { ++monitorSignals; });
        QObject::connect(output.data(), &KScreen::Output::isConnectedChanged, [&] { ++connectedSignals; });
        auto desired = config->clone();
        desired->output(1)->setCurrentModeId(QStringLiteral("2"));
        auto *apply = new KScreen::SetConfigOperation(desired);
        require(apply->exec(), "Installed SetConfigOperation failed");
        waitFor([&] { return output->currentModeId() == QStringLiteral("2") && monitorSignals > 0; }, "Applied mode/model notification failed");
        require(getConfig()->output(1)->currentMode()->size() == QSize(1024, 768), "Applied mode was not retained by backend");
        QDBusInterface fake(QStringLiteral("org.kde.KScreen"), QStringLiteral("/fake"), QStringLiteral("org.kde.kscreen.FakeBackend"), bus);
        require(fake.isValid(), "Installed Fake control interface unavailable");
        auto change = [&](const QString &method, const QVariantList &arguments) {
            auto result = fake.callWithArgumentList(QDBus::Block, method, arguments);
            require(result.type() != QDBusMessage::ErrorMessage, "Installed Fake control request failed");
        };
        change(QStringLiteral("setConnected"), {1, false});
        waitFor([&] { return !output->isConnected() && connectedSignals == 1; }, "Disconnect signal/state failed");
        change(QStringLiteral("setConnected"), {1, true});
        waitFor([&] { return output->isConnected() && connectedSignals == 2; }, "Reconnect signal/state failed");
        change(QStringLiteral("addOutput"), {2, QStringLiteral("SUPRA2")});
        waitFor([&] { return config->outputs().size() == 2 && config->output(2); }, "Hotplug insertion failed");
        require(config->output(2)->name() == QStringLiteral("SUPRA2"), "Hotplug identity mismatch");
        change(QStringLiteral("removeOutput"), {2});
        waitFor([&] { return config->outputs().size() == 1 && !config->output(2); }, "Hotplug removal failed");
        monitor->removeConfig(config);
        KScreen::Dpms dpms;
        require(!dpms.isSupported() && !dpms.hasPendingChanges(), "Owned Xvfb should expose unsupported DPMS without pending changes");
        std::cout << "Installed KScreen D-Bus/Fake backend, get/set configuration, EDID, mode persistence, cloning, monitor signals and hotplug: PASS\n";
        std::cout << "Installed ScreenDpms construction/properties on private Xvfb without DPMS: PASS; power switching and Wayland remain integration QA\n";
        launcher.call(QStringLiteral("quit"));
        return 0;
    } catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
}
