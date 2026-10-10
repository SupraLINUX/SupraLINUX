#include <QApplication>
#include <QDBusInterface>
#include <QDBusReply>
#include <QScreen>
#include <QPixmap>
#include <QImage>
#include <QSet>
#include <cstdio>
#include <cstdlib>
#include <cstring>
int main(int argc,char **argv) {
 const char *d=std::getenv("DISPLAY"),*owned=std::getenv("SUPRA_PRIVATE_XVFB_DISPLAY");
 if(!d||!owned||std::strcmp(d,owned)||argc!=3)return 2;
 QApplication app(argc,argv);
 if(QString::fromLocal8Bit(argv[1])=="select") {
  QDBusInterface menu("org.kde.kmenuedit","/KMenuEdit","org.kde.kmenuedit");
  if(!menu.isValid())return 3;
  QDBusReply<void> selected=menu.call("selectMenuEntry",QString::fromLocal8Bit(argv[2]));
  if(!selected.isValid()){std::fprintf(stderr,"%s\n",qPrintable(selected.error().message()));return 4;}
  std::puts("{\"state\":\"PASS\",\"scope\":\"original public Qt typed KMenuEdit selection\"}");return 0;
 }
 if(QString::fromLocal8Bit(argv[1])!="screenshot")return 5;
 auto screen=app.primaryScreen();if(!screen)return 6;
 QImage pixels=screen->grabWindow(0).toImage();QSet<QRgb> colors;
 for(int y=0;y<pixels.height();y+=4)for(int x=0;x<pixels.width();x+=4)colors.insert(pixels.pixel(x,y));
 if(pixels.size()!=QSize(1024,768)||colors.size()<20||!pixels.save(QString::fromLocal8Bit(argv[2])))return 7;
 std::printf("{\"state\":\"PASS\",\"scope\":\"owned Xvfb actual installed GUI pixels\",\"colors\":%d}\n",int(colors.size()));return 0;
}
