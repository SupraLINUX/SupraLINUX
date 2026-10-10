// SPDX-License-Identifier: CC0-1.0
#include <kglobalacceld.h>
#include <QGuiApplication>
#include <iostream>
#include <stdexcept>
static void check(bool ok,const char *why) { if (!ok) throw std::runtime_error(why); }
int main(int argc,char **argv)
{
    try {
        QGuiApplication app(argc,argv); KGlobalAccelD daemon; check(daemon.init(),"Installed private C++ API initialization failed");
        const QStringList id{QStringLiteral("org.supralinux.direct-sdk"),QStringLiteral("direct-key"),QStringLiteral("Direct SDK"),QStringLiteral("Private key")};
        daemon.doRegister(id);
        using Keys=decltype(daemon.shortcutKeys(id));
        const Keys keys{QKeySequence(Qt::CTRL|Qt::ALT|Qt::Key_F11)};
        check(daemon.setShortcutKeys(id,keys,KGlobalAccelD::SetPresent|KGlobalAccelD::NoAutoloading)==keys,"Installed private C++ setter differs");
        check(daemon.shortcutKeys(id)==keys,"Installed private C++ getter differs");
        check(daemon.setShortcutKeys(id,keys,KGlobalAccelD::IsDefault)==keys,"Installed private C++ default setter differs");
        check(daemon.defaultShortcutKeys(id)==keys,"Installed private C++ default getter differs");
        daemon.setForeignShortcutKeys(id,keys);
        check(daemon.unregister(id[0],id[1]),"Installed private C++ removal failed");
        check(daemon.shortcutKeys(id).isEmpty(),"Installed private C++ removal retained shortcut");
        std::cout<<"Installed KGlobalAccelD Ubuntu private C++ SDK: setter/getter, defaults, foreign setter and removal PASS\n";
    } catch (const std::exception &error) { std::cerr<<error.what()<<'\n'; return 1; }
}
