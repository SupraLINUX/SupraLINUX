#include <kglobalacceld.h>
#include <QCoreApplication>
int main(int n,char **v) { QCoreApplication a(n,v); KGlobalAccelD daemon; return daemon.shortcutKeys({}).size(); }
