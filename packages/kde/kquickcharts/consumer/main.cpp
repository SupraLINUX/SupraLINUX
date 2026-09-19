#include <QCoreApplication>

void qml_register_types_org_kde_quickcharts();

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    qml_register_types_org_kde_quickcharts();
    return 0;
}
