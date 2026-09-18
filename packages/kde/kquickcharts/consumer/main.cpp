#include <QCoreApplication>

void qml_register_types_org_kde_quickcharts();
void qml_register_types_org_kde_quickcharts_controls();

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    qml_register_types_org_kde_quickcharts();
    qml_register_types_org_kde_quickcharts_controls();
    return 0;
}
