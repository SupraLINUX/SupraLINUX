#include <wayland-server.h>
#include <stdio.h>
#include "new.h"
static void bind_window(struct wl_client *client, void *data, uint32_t version, uint32_t id) {
 (void)data;
 struct wl_resource *window=wl_resource_create(client,&org_kde_plasma_window_interface,(int)version,id);
 if (!window) { wl_client_post_no_memory(client); return; }
 org_kde_plasma_window_send_pid_changed(window,4242);
 wl_client_flush(client);
}
int main(void) {
 struct wl_display *display=wl_display_create();
 if (!display || wl_display_add_socket(display,"supra-wire")!=0) return 2;
 if (!wl_global_create(display,&org_kde_plasma_window_interface,20,NULL,bind_window)) return 3;
 wl_display_run(display);
 wl_display_destroy(display);
 return 0;
}
