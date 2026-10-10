#include <wayland-client.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "old.h"
static int wanted;
static uint32_t observed;
static struct org_kde_plasma_window *window;
static void pid_changed(void *data,struct org_kde_plasma_window *object,uint32_t pid) {
 (void)data; (void)object; observed=pid;
}
static const struct org_kde_plasma_window_listener listener={.pid_changed=pid_changed};
static void global(void *data,struct wl_registry *registry,uint32_t id,const char *interface,uint32_t version) {
 (void)data;
 if (strcmp(interface,"org_kde_plasma_window")==0 && version>=(uint32_t)wanted) {
  window=wl_registry_bind(registry,id,&org_kde_plasma_window_interface,(uint32_t)wanted);
  org_kde_plasma_window_add_listener(window,&listener,NULL);
 }
}
static void removed(void *data,struct wl_registry *registry,uint32_t id) { (void)data;(void)registry;(void)id; }
static const struct wl_registry_listener registry_listener={global,removed};
int main(int argc,char **argv) {
 if(argc!=2) return 2;
 wanted=atoi(argv[1]);
 struct wl_display *display=wl_display_connect("supra-wire");
 if(!display)return 3;
 struct wl_registry *registry=wl_display_get_registry(display);
 wl_registry_add_listener(registry,&registry_listener,NULL);
 if(wl_display_roundtrip(display)<0 || !window || wl_display_roundtrip(display)<0 || observed!=4242) return 4;
 printf("Unchanged Ubuntu protocol client, negotiated version %d, candidate server PID event %u: PASS\n",wanted,observed);
 org_kde_plasma_window_destroy(window);wl_registry_destroy(registry);wl_display_disconnect(display);return 0;
}
