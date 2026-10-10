#include <KTextTemplate/Engine>

int main()
{
    KTextTemplate::Engine engine;
    engine.setSmartTrimEnabled(true);
    return engine.smartTrimEnabled() ? 0 : 1;
}
