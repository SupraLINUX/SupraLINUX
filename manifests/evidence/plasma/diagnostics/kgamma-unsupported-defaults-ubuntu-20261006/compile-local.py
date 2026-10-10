from pathlib import Path
import subprocess
src=Path(__file__).resolve().parent
sdk=src.parents[1]/'.work/ubuntu-client-sdk/extracted/usr'
includes=[sdk/'include/KF6',sdk/'include/x86_64-linux-gnu/qt6']
includes += [sdk/'include/x86_64-linux-gnu/qt6'/n for n in ['QtCore','QtGui','QtWidgets']]
includes += [sdk/'include/KF6'/n for n in ['KCoreAddons','KCMUtils','KCMUtilsCore','KConfig','KConfigCore']]
args=['-I'+str(p) for p in includes]
subprocess.run(['g++','-std=c++20','-fPIC','-shared',str(src/'gamma-shim.cpp'),'-o',str(src/'gamma-shim.so')],check=True)
subprocess.run(['g++','-std=c++20','-fPIC',*args,str(src/'main.cpp'),'-l:libQt6Core.so.6','-l:libQt6Gui.so.6','-l:libQt6Widgets.so.6','-l:libKF6CoreAddons.so.6','-l:libKF6KCMUtils.so.6','-l:libKF6KCMUtilsCore.so.6','-l:libKF6ConfigCore.so.6','-ldl','-o',str(src/'ubuntu-kgamma-client')],check=True)
