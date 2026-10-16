#include <KConfig>
#include <KConfigGroup>
int main(){ KConfig c(QStringLiteral("supralinux-batch9"), KConfig::SimpleConfig); KConfigGroup g(&c, QStringLiteral("smoke")); g.writeEntry("ok", true); return g.readEntry("ok", false) ? 0 : 1; }
