#include <KDBusService>
#include <QCoreApplication>
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    app.setApplicationName("supralinux-kdbusaddons-smoke");
    app.setOrganizationDomain("supralinux.invalid");
    KDBusService service(KDBusService::Multiple | KDBusService::NoExitOnFailure);
    return service.isRegistered() ? 0 : 1;
}
