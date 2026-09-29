#include <KAuth/Action>
#include <QCoreApplication>
#include <QString>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    KAuth::Action action(QStringLiteral("org.supralinux.kauth.consumer-smoke"));
    if (!action.isValid()) {
        return 2;
    }
    return action.name() == QStringLiteral("org.supralinux.kauth.consumer-smoke") ? 0 : 3;
}
