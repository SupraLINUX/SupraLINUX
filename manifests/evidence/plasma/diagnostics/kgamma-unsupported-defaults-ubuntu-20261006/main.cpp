// SPDX-License-Identifier: CC0-1.0
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QFileInfo>
#include <QLabel>
#include <QSlider>
#include <QStackedWidget>
#include <KConfig>
#include <KConfigGroup>
#include <KCModule>
#include <KPluginFactory>
#include <KPluginMetaData>
#include <cmath>
#include <dlfcn.h>
#include <iostream>
#include <memory>
#include <stdexcept>

static void check(bool condition,const char *message)
{
    if(!condition)throw std::runtime_error(message);
}
using Snapshot=void (*)(float *,unsigned *);
static Snapshot snapshot;
static void gamma(float r,float g,float b)
{
    float values[3];unsigned writes;snapshot(values,&writes);
    check(std::abs(values[0]-r)<0.002f && std::abs(values[1]-g)<0.002f && std::abs(values[2]-b)<0.002f,"Actual gamma backend values differ");
    check(writes>0,"Installed module did not call gamma backend");
}
static std::unique_ptr<KCModule> load(const KPluginMetaData &metadata)
{
    auto result=KPluginFactory::instantiatePlugin<KCModule>(metadata);
    check(result.plugin!=nullptr,"Installed QWidget KCM did not load");
    return std::unique_ptr<KCModule>(result.plugin);
}
int main(int argc,char **argv)
{
    try {
        QApplication app(argc,argv);
        check(argc==2,"Provide installed KGamma plugin path");
        snapshot=reinterpret_cast<Snapshot>(dlsym(RTLD_DEFAULT,"supra_gamma_snapshot"));
        check(snapshot!=nullptr,"Private gamma protocol shim absent");
        KPluginMetaData metadata(QString::fromLocal8Bit(argv[1]));
        check(metadata.isValid(),"Installed KCM metadata invalid");
        check(metadata.value(QStringLiteral("X-KDE-OnlyShowOnQtPlatforms"),QStringList())==QStringList{QStringLiteral("xcb")},"X11-only upstream platform boundary changed");
        auto module=load(metadata);
        QWidget *widget=module->widget();
        check(widget!=nullptr,"Installed KCM widget absent");
        if(qEnvironmentVariableIsSet("SUPRA_GAMMA_UNSUPPORTED")) {
            check(widget->findChildren<QSlider *>().isEmpty(),"Unsupported backend exposes gamma controls");
            bool message=false;
            for(auto *label:widget->findChildren<QLabel *>())message|=label->text().contains(QStringLiteral("Gamma correction is not supported"));
            check(message,"Unsupported backend diagnostic absent");
            module->load();module->save();
            std::cout << "Unsupported controls: buttons=" << int(module->buttons()) << " defaults=" << module->representsDefaults() << " needsSave=" << module->needsSave() << std::endl;
            if ((module->buttons() & KAbstractConfigModule::Default) && !module->representsDefaults()) {
                std::cout << "Invoking exposed default action" << std::endl; module->defaults();
            }
            std::cout<<"Installed KGamma unsupported-backend UI, load and save: PASS\n";
            return 0;
        }
        auto sliders=widget->findChildren<QSlider *>();
        check(sliders.size()==4,"Four actual installed gamma sliders required");
        gamma(1.2f,1.3f,1.4f);
        sliders[1]->setValue(26);sliders[2]->setValue(20);sliders[3]->setValue(30);
        gamma(1.7f,1.4f,1.9f);
        sliders[0]->setValue(32);gamma(2.0f,2.0f,2.0f);
        module->defaults();gamma(1.0f,1.0f,1.0f);
        sliders[1]->setValue(0);gamma(0.4f,1.0f,1.0f);
        sliders[1]->setValue(sliders[1]->maximum());gamma(3.5f,1.0f,1.0f);
        sliders[1]->setValue(24);sliders[2]->setValue(26);sliders[3]->setValue(28);
        gamma(1.6f,1.7f,1.8f);
        for(auto *box:widget->findChildren<QCheckBox *>())check(!box->isChecked(),"Global Xorg writer or screen sync enabled in private fixture");
        module->save();
        {
            KConfig config(QStringLiteral("kgammarc"));KConfigGroup group(&config,QStringLiteral("Screen 0"));
            check(group.readEntry("rgamma",QString())==QStringLiteral("1.60"),"Saved red channel differs");
            check(group.readEntry("ggamma",QString())==QStringLiteral("1.70"),"Saved green channel differs");
            check(group.readEntry("bgamma",QString())==QStringLiteral("1.80"),"Saved blue channel differs");
            check(KConfigGroup(&config,QStringLiteral("ConfigFile")).readEntry("use",QString())==QStringLiteral("kgammarc"),"Private config destination differs");
        }
        sliders[0]->setValue(42);gamma(2.5f,2.5f,2.5f);
        module->load();gamma(1.6f,1.7f,1.8f);
        auto stacks=widget->findChildren<QStackedWidget *>();
        check(stacks.size()==1 && stacks[0]->count()==6,"Six installed calibration patterns required");
        auto combos=widget->findChildren<QComboBox *>();
        check(!combos.isEmpty() && combos[0]->count()==6,"Installed pattern selector absent");
        for(int i=0;i<6;++i){
            auto *pattern=qobject_cast<QLabel *>(stacks[0]->widget(i));
            check(pattern!=nullptr && !pattern->pixmap().isNull(),"Installed calibration image absent");
            check(QMetaObject::invokeMethod(combos[0],"activated",Qt::DirectConnection,Q_ARG(int,i)),"Pattern activation failed");
            check(stacks[0]->currentIndex()==i,"Installed calibration pattern did not change");
        }
        widget->resize(700,650);widget->show();app.processEvents();
        check(!widget->grab().isNull(),"Actual KCM rendering failed");
        module.reset();module=load(metadata);gamma(1.6f,1.7f,1.8f);
        std::cout<<"Installed KGamma sliders, RGB/master values, bounds, defaults, private save/load/reload, six patterns and QWidget rendering: PASS\n";
    }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
}
