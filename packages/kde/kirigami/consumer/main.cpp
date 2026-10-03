#include <QCoreApplication>
#include <Kirigami/Platform/StyleHints>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    Kirigami::Platform::StyleHints::setMakeStyleHintsFunction(
        [](QObject *) -> Kirigami::Platform::StyleHints * { return nullptr; });
    return 0;
}
