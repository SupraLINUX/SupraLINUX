#include <dlfcn.h>
#include <cstdio>
int main() {
    void *handle = dlopen("libKF6Plotting.so.6", RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        std::fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }
    dlclose(handle);
    return 0;
}
