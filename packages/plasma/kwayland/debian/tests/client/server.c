#include <wayland-server.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "plasma-server.h"
#define U(x) (void)(x)
struct surface_data { struct wl_resource *frame; int scale, region, damage; };
static void resource_destroy(struct wl_client *c, struct wl_resource *r) { U(c); wl_resource_destroy(r); }
static void free_resource(struct wl_resource *r) { free(wl_resource_get_user_data(r)); }
static void region_add(struct wl_client *c, struct wl_resource *r, int32_t x, int32_t y, int32_t w, int32_t h) {
 U(c); *(int *)wl_resource_get_user_data(r) = (x==1 && y==2 && w==10 && h==20);
}
static void region_subtract(struct wl_client *c, struct wl_resource *r, int32_t x, int32_t y, int32_t w, int32_t h) {
 U(c); U(x); U(y); U(w); U(h); wl_resource_post_error(r,0,"Unexpected region subtraction");
}
static const struct wl_region_interface region_impl = { .destroy=resource_destroy, .add=region_add, .subtract=region_subtract };
static void surface_attach(struct wl_client *c, struct wl_resource *r, struct wl_resource *b, int32_t x, int32_t y) {
 U(c); U(b); U(x); U(y); wl_resource_post_error(r,0,"Buffers are outside this protocol fixture");
}
static void surface_damage(struct wl_client *c, struct wl_resource *r, int32_t x, int32_t y, int32_t w, int32_t h) {
 U(c); ((struct surface_data *)wl_resource_get_user_data(r))->damage=(x==3 && y==4 && w==5 && h==6);
}
static void surface_frame(struct wl_client *c, struct wl_resource *r, uint32_t id) {
 struct surface_data *s=wl_resource_get_user_data(r); s->frame=wl_resource_create(c,&wl_callback_interface,1,id);
}
static void surface_opaque(struct wl_client *c, struct wl_resource *r, struct wl_resource *region) { U(c); U(r); U(region); }
static void surface_region(struct wl_client *c, struct wl_resource *r, struct wl_resource *region) {
 U(c); ((struct surface_data *)wl_resource_get_user_data(r))->region=region && *(int *)wl_resource_get_user_data(region);
}
static void surface_transform(struct wl_client *c, struct wl_resource *r, int32_t transform) { U(c); U(r); U(transform); }
static void surface_scale(struct wl_client *c, struct wl_resource *r, int32_t scale) { U(c); ((struct surface_data *)wl_resource_get_user_data(r))->scale=scale; }
static void surface_commit(struct wl_client *c, struct wl_resource *r) {
 U(c); struct surface_data *s=wl_resource_get_user_data(r);
 if (s->scale!=2 || !s->region || !s->damage || !s->frame) { wl_resource_post_error(r,0,"Surface request mismatch"); return; }
 wl_callback_send_done(s->frame,1234);wl_resource_destroy(s->frame);s->frame=NULL;
 puts("Native surface scale/region/damage/commit/frame verified");fflush(stdout);
}
static void surface_free(struct wl_resource *r) {
 struct surface_data *s=wl_resource_get_user_data(r);if(s->frame)wl_resource_destroy(s->frame);free(s);
 puts("Native surface resource destroyed");fflush(stdout);
}
static const struct wl_surface_interface surface_impl = { .destroy=resource_destroy,.attach=surface_attach,.damage=surface_damage,
 .frame=surface_frame,.set_opaque_region=surface_opaque,.set_input_region=surface_region,.commit=surface_commit,
 .set_buffer_transform=surface_transform,.set_buffer_scale=surface_scale,.damage_buffer=surface_damage };
static void create_surface(struct wl_client *c, struct wl_resource *r, uint32_t id) {
 struct wl_resource *s=wl_resource_create(c,&wl_surface_interface,wl_resource_get_version(r),id);
 struct surface_data *data=calloc(1,sizeof(*data));if(!s || !data){wl_client_post_no_memory(c);return;}
 wl_resource_set_implementation(s,&surface_impl,data,surface_free);
}
static void create_region(struct wl_client *c, struct wl_resource *r, uint32_t id) {
 U(r);struct wl_resource *s=wl_resource_create(c,&wl_region_interface,1,id);int *data=calloc(1,sizeof(*data));
 if(!s || !data){wl_client_post_no_memory(c);return;}wl_resource_set_implementation(s,&region_impl,data,free_resource);
}
static const struct wl_compositor_interface compositor_impl = {.create_surface=create_surface,.create_region=create_region};
static void bind_compositor(struct wl_client *c, void *data, uint32_t version, uint32_t id) {
 U(data);struct wl_resource *r=wl_resource_create(c,&wl_compositor_interface,(int)version,id);
 wl_resource_set_implementation(r,&compositor_impl,NULL,NULL);
}
static void window_state(struct wl_client *c, struct wl_resource *r, uint32_t flags, uint32_t state) {
 U(c);uint32_t *current=wl_resource_get_user_data(r);*current=(*current & ~flags)|(state & flags);
 org_kde_plasma_window_send_state_changed(r,*current);org_kde_plasma_window_send_title_changed(r,"Supra updated");
 puts("Native window state request verified");fflush(stdout);
}
static void window_close(struct wl_client *c, struct wl_resource *r) {
 U(c);org_kde_plasma_window_send_unmapped(r);puts("Native window close request verified");fflush(stdout);
}
static const struct org_kde_plasma_window_interface window_impl = {.set_state=window_state,.close=window_close,.destroy=resource_destroy};
static void create_window(struct wl_client *c, struct wl_resource *wm, uint32_t id) {
 struct wl_resource *r=wl_resource_create(c,&org_kde_plasma_window_interface,wl_resource_get_version(wm),id);
 uint32_t *state=calloc(1,sizeof(*state));if(!r || !state){wl_client_post_no_memory(c);return;}
 *state=ORG_KDE_PLASMA_WINDOW_MANAGEMENT_STATE_ACTIVE|ORG_KDE_PLASMA_WINDOW_MANAGEMENT_STATE_MINIMIZABLE|ORG_KDE_PLASMA_WINDOW_MANAGEMENT_STATE_CLOSEABLE;
 wl_resource_set_implementation(r,&window_impl,state,free_resource);
 org_kde_plasma_window_send_title_changed(r,"Supra initial");org_kde_plasma_window_send_app_id_changed(r,"org.supralinux.compat");
 org_kde_plasma_window_send_pid_changed(r,4242);org_kde_plasma_window_send_state_changed(r,*state);
 org_kde_plasma_window_send_initial_state(r);
}
static void get_window(struct wl_client *c, struct wl_resource *r, uint32_t id, uint32_t internal_id) {
 if(internal_id!=1){wl_resource_post_error(r,0,"Wrong window ID");return;}create_window(c,r,id);
}
static void get_uuid(struct wl_client *c, struct wl_resource *r, uint32_t id, const char *uuid) {
 if(strcmp(uuid,"supra-window")){wl_resource_post_error(r,0,"Wrong window UUID");return;}create_window(c,r,id);
}
static void show_desktop(struct wl_client *c, struct wl_resource *r, uint32_t state) {
 U(c);org_kde_plasma_window_management_send_show_desktop_changed(r,state);
}
static const struct org_kde_plasma_window_management_interface management_impl = {.show_desktop=show_desktop,.get_window=get_window,.get_window_by_uuid=get_uuid};
static void bind_management(struct wl_client *c, void *data, uint32_t version, uint32_t id) {
 U(data);struct wl_resource *r=wl_resource_create(c,&org_kde_plasma_window_management_interface,(int)version,id);
 wl_resource_set_implementation(r,&management_impl,NULL,NULL);
 org_kde_plasma_window_management_send_show_desktop_changed(r,0);
 org_kde_plasma_window_management_send_window_with_uuid(r,1,"supra-window");
 org_kde_plasma_window_management_send_stacking_order_uuid_changed(r,"supra-window");
}
int main(void) {
 struct wl_display *display=wl_display_create();if(!display || wl_display_add_socket(display,"supra-compat")!=0)return 2;
 if(!wl_global_create(display,&wl_compositor_interface,4,NULL,bind_compositor) ||
    !wl_global_create(display,&org_kde_plasma_window_management_interface,16,NULL,bind_management))return 3;
 wl_display_run(display);wl_display_destroy_clients(display);wl_display_destroy(display);return 0;
}
