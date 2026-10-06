// SPDX-License-Identifier: CC0-1.0
#include <cstdlib>
#include <cstring>

struct Gamma { float red, green, blue; };
static Gamma current{1.2f,1.3f,1.4f};
static unsigned writes=0;
extern "C" int XF86VidModeGetGamma(void *,int screen,Gamma *gamma)
{
    if(screen!=0 || std::getenv("SUPRA_GAMMA_UNSUPPORTED")) return 0;
    *gamma=current;
    return 1;
}
extern "C" int XF86VidModeSetGamma(void *,int screen,Gamma *gamma)
{
    if(screen!=0 || std::getenv("SUPRA_GAMMA_UNSUPPORTED")) return 0;
    current=*gamma;
    ++writes;
    return 1;
}
extern "C" void supra_gamma_snapshot(float *values,unsigned *count)
{
    values[0]=current.red;values[1]=current.green;values[2]=current.blue;
    *count=writes;
}
