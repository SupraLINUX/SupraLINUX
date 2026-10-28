#include <KWayland/Client/compositor.h>
#include <KWayland/Client/connection_thread.h>
#include <KWayland/Client/event_queue.h>
#include <KWayland/Client/plasmawindowmanagement.h>
#include <KWayland/Client/plasmawindowmodel.h>
#include <KWayland/Client/region.h>
#include <KWayland/Client/registry.h>
#include <KWayland/Client/surface.h>
#include <QCoreApplication>
#include <QDeadlineTimer>
#include <QEventLoop>
#include <QRegion>
#include <QThread>
#include <functional>
#include <iostream>
#include <memory>
#include <stdexcept>
using namespace KWayland::Client;
static void require(bool ok, const char *message) { if (!ok) throw std::runtime_error(message); }
static void waitFor(const std::function<bool()> &ready, const char *message) {
    QDeadlineTimer deadline(8000);
    while (!ready() && !deadline.hasExpired()) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 20);
        QThread::msleep(1);
    }
    require(ready(), message);
}
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    try {
        ConnectionThread connection;
        connection.setSocketName(QStringLiteral("supra-compat"));
        bool connected = false;
        QObject::connect(&connection, &ConnectionThread::connected, [&] { connected = true; });
        connection.initConnection();
        waitFor([&] { return connected; }, "Wayland connection did not establish");
        {
            EventQueue queue;
            queue.setup(&connection);
            require(queue.isValid(), "Event queue invalid");
            Registry registry;
            registry.setEventQueue(&queue);
            registry.create(&connection);
            bool announced = false;
            QObject::connect(&registry, &Registry::interfacesAnnounced, [&] { announced = true; });
            registry.setup();
            waitFor([&] { return announced; }, "Registry discovery did not finish");
            auto ci = registry.interface(Registry::Interface::Compositor);
            auto wi = registry.interface(Registry::Interface::PlasmaWindowManagement);
            require(ci.name && ci.version == 4 && wi.name && wi.version == 16, "Wrong announced interfaces");
            std::unique_ptr<Compositor> compositor(registry.createCompositor(ci.name, ci.version));
            std::unique_ptr<Region> region(compositor->createRegion(QRegion(QRect(1, 2, 10, 20)), nullptr));
            std::unique_ptr<Surface> surface(compositor->createSurface());
            require(compositor->isValid() && region->isValid() && surface->isValid(), "Invalid native objects");
            bool frame = false;
            QObject::connect(surface.get(), &Surface::frameRendered, [&] { frame = true; });
            surface->setScale(2);
            surface->setInputRegion(region.get());
            surface->damage(QRect(3, 4, 5, 6));
            surface->commit();
            waitFor([&] { return frame; }, "Frame callback did not arrive");
            std::unique_ptr<PlasmaWindowManagement> wm(registry.createPlasmaWindowManagement(wi.name, wi.version));
            PlasmaWindowModel *model = wm->createWindowModel();
            int desktopSignals = 0;
            QObject::connect(wm.get(), &PlasmaWindowManagement::showingDesktopChanged, [&] { ++desktopSignals; });
            waitFor([&] { return wm->windows().size() == 1 && model->rowCount() == 1; }, "Window/model discovery failed");
            PlasmaWindow *window = wm->windows().first();
            require(window->pid() == 4242 && window->uuid() == QByteArray("supra-window"), "PID/UUID mismatch");
            require(window->title() == QStringLiteral("Supra initial") && window->appId() == QStringLiteral("org.supralinux.compat"), "Window metadata mismatch");
            require(window->isActive() && wm->activeWindow() == window, "Active window mismatch");
            require(model->data(model->index(0), PlasmaWindowModel::Pid).toUInt() == 4242, "Model PID mismatch");
            require(model->data(model->index(0), Qt::DisplayRole).toString() == window->title(), "Model title mismatch");
            int titleSignals = 0, minimizedSignals = 0;
            QObject::connect(window, &PlasmaWindow::titleChanged, [&] { ++titleSignals; });
            QObject::connect(window, &PlasmaWindow::minimizedChanged, [&] { ++minimizedSignals; });
            window->requestToggleMinimized();
            waitFor([&] { return window->isMinimized() && titleSignals == 1 && minimizedSignals == 1; }, "Window request/signals failed");
            require(window->title() == QStringLiteral("Supra updated"), "Updated title mismatch");
            require(model->data(model->index(0), PlasmaWindowModel::IsMinimized).toBool(), "Model state did not update");
            wm->showDesktop();
            waitFor([&] { return wm->isShowingDesktop() && desktopSignals == 1; }, "Show desktop exchange failed");
            wm->hideDesktop();
            waitFor([&] { return !wm->isShowingDesktop() && desktopSignals == 2; }, "Hide desktop exchange failed");
            window->requestClose();
            waitFor([&] { return wm->windows().isEmpty() && model->rowCount() == 0; }, "Window/model removal failed");
            surface->release();
            region->release();
            connection.flush();
            connection.roundtrip();
            require(!connection.hasError(), "Wayland connection reported an error");
            std::cout << "Installed KWayland connection/registry/event queue, region/surface/frame, window metadata/signals, Qt model changes/removal and show-desktop exchanges: PASS\n";
        }
        connection.flush();
        return 0;
    } catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
}
