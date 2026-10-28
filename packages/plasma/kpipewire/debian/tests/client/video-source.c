// SPDX-FileCopyrightText: 2026 SupraLINUX contributors
// SPDX-License-Identifier: CC0-1.0
#define _GNU_SOURCE
#include <pipewire/pipewire.h>
#include <spa/param/video/format-utils.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>
#define WIDTH 160
#define HEIGHT 120
struct Fixture {struct pw_main_loop *main;struct pw_stream *stream;struct spa_source *timer;unsigned sequence;int failed;};
struct Allocation {void *data;int fd;};
static void add_buffer(void *context,struct pw_buffer *buffer) {
 struct Fixture *f=context;struct spa_data *data=&buffer->buffer->datas[0];
 if(!(data->type&(1<<SPA_DATA_MemFd))){f->failed=1;pw_main_loop_quit(f->main);return;}
 struct Allocation *allocation=calloc(1,sizeof(*allocation));
 if(!allocation){f->failed=1;pw_main_loop_quit(f->main);return;}
 allocation->fd=memfd_create("supralinux-private-video",MFD_CLOEXEC);
 if(allocation->fd<0 || ftruncate(allocation->fd,WIDTH*HEIGHT*4)<0){if(allocation->fd>=0)close(allocation->fd);free(allocation);f->failed=1;pw_main_loop_quit(f->main);return;}
 allocation->data=mmap(NULL,WIDTH*HEIGHT*4,PROT_READ|PROT_WRITE,MAP_SHARED,allocation->fd,0);
 if(allocation->data==MAP_FAILED){close(allocation->fd);free(allocation);f->failed=1;pw_main_loop_quit(f->main);return;}
 data->type=SPA_DATA_MemFd;data->flags=SPA_DATA_FLAG_READWRITE|SPA_DATA_FLAG_MAPPABLE;
 data->fd=allocation->fd;data->mapoffset=0;data->maxsize=WIDTH*HEIGHT*4;data->data=allocation->data;
 buffer->user_data=allocation;
 fprintf(stderr,"Own MemFd buffer: fd=%d mapoffset=0 maxsize=%u\n",allocation->fd,data->maxsize);
}
static void remove_buffer(void *context,struct pw_buffer *buffer) {
 (void)context;struct Allocation *allocation=buffer->user_data;if(!allocation)return;
 munmap(allocation->data,WIDTH*HEIGHT*4);close(allocation->fd);free(allocation);buffer->user_data=NULL;
}
static void quit(void *context,int number) {struct Fixture *f=context;(void)number;pw_main_loop_quit(f->main);}
static void tick(void *context,uint64_t count) {struct Fixture *f=context;(void)count;pw_stream_trigger_process(f->stream);}
static void produce(void *context) {
 struct Fixture *f=context;struct pw_buffer *buffer=pw_stream_dequeue_buffer(f->stream);
 if(!buffer)return;
 struct spa_data *data=&buffer->buffer->datas[0];
 if(!data->data || data->maxsize<WIDTH*HEIGHT*4){f->failed=1;pw_stream_queue_buffer(f->stream,buffer);pw_main_loop_quit(f->main);return;}
 unsigned char *pixels=data->data;
 for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++) {
  unsigned char *pixel=pixels+4*(y*WIDTH+x);pixel[0]=(x*3)%256;pixel[1]=(y*5)%256;pixel[2]=f->sequence%256;pixel[3]=255;
 }
 struct spa_meta_header *header=spa_buffer_find_meta_data(buffer->buffer,SPA_META_Header,sizeof(struct spa_meta_header));
 if(header){memset(header,0,sizeof(*header));header->seq=f->sequence;header->pts=(int64_t)f->sequence*33333333;}
 f->sequence++;data->chunk->offset=0;data->chunk->size=WIDTH*HEIGHT*4;data->chunk->stride=WIDTH*4;
 pw_stream_queue_buffer(f->stream,buffer);
}
static void state(void *context,enum pw_stream_state old,enum pw_stream_state current,const char *error) {
 struct Fixture *f=context;(void)old;
 if(current==PW_STREAM_STATE_ERROR){fprintf(stderr,"Private source error: %s\n",error);f->failed=1;pw_main_loop_quit(f->main);}
 struct timespec initial={0,1},interval={0,33333333};
 pw_loop_update_timer(pw_main_loop_get_loop(f->main),f->timer,current==PW_STREAM_STATE_STREAMING?&initial:NULL,current==PW_STREAM_STATE_STREAMING?&interval:NULL,false);
}
static void format(void *context,uint32_t id,const struct spa_pod *parameter) {
 struct Fixture *f=context;if(id!=SPA_PARAM_Format || !parameter)return;
 struct spa_video_info_raw actual={0};
 if(spa_format_video_raw_parse(parameter,&actual)<0 || actual.format!=SPA_VIDEO_FORMAT_RGBA || actual.size.width!=WIDTH || actual.size.height!=HEIGHT){f->failed=1;pw_main_loop_quit(f->main);return;}
 unsigned char storage[1024];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(storage,sizeof(storage));
 const struct spa_pod *params[2];
 params[0]=spa_pod_builder_add_object(&builder,SPA_TYPE_OBJECT_ParamBuffers,SPA_PARAM_Buffers,
  SPA_PARAM_BUFFERS_buffers,SPA_POD_CHOICE_RANGE_Int(8,2,16),SPA_PARAM_BUFFERS_blocks,SPA_POD_Int(1),
  SPA_PARAM_BUFFERS_size,SPA_POD_Int(WIDTH*HEIGHT*4),SPA_PARAM_BUFFERS_stride,SPA_POD_Int(WIDTH*4),
  SPA_PARAM_BUFFERS_dataType,SPA_POD_CHOICE_FLAGS_Int(1<<SPA_DATA_MemFd));
 params[1]=spa_pod_builder_add_object(&builder,SPA_TYPE_OBJECT_ParamMeta,SPA_PARAM_Meta,SPA_PARAM_META_type,SPA_POD_Id(SPA_META_Header),SPA_PARAM_META_size,SPA_POD_Int(sizeof(struct spa_meta_header)));
 if(pw_stream_update_params(f->stream,params,2)<0){f->failed=1;pw_main_loop_quit(f->main);}
}
int main(int argc,char **argv) {
 pw_init(&argc,&argv);struct Fixture fixture={0};fixture.main=pw_main_loop_new(NULL);if(!fixture.main)return 1;
 struct pw_loop *loop=pw_main_loop_get_loop(fixture.main);
 fixture.timer=pw_loop_add_timer(loop,tick,&fixture);pw_loop_add_signal(loop,SIGTERM,quit,&fixture);pw_loop_add_signal(loop,SIGINT,quit,&fixture);
 const struct pw_stream_events events={.version=PW_VERSION_STREAM_EVENTS,.state_changed=state,.param_changed=format,.add_buffer=add_buffer,.remove_buffer=remove_buffer,.process=produce};
 fixture.stream=pw_stream_new_simple(loop,"supralinux-private-source",pw_properties_new(PW_KEY_NODE_NAME,"supralinux-private-source",PW_KEY_MEDIA_CLASS,"Video/Source",PW_KEY_MEDIA_ROLE,"Camera",NULL),&events,&fixture);
 if(!fixture.stream){pw_main_loop_destroy(fixture.main);pw_deinit();return 1;}
 unsigned char storage[1024];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(storage,sizeof(storage));
 const struct spa_pod *params[]={spa_pod_builder_add_object(&builder,SPA_TYPE_OBJECT_Format,SPA_PARAM_EnumFormat,
  SPA_FORMAT_mediaType,SPA_POD_Id(SPA_MEDIA_TYPE_video),SPA_FORMAT_mediaSubtype,SPA_POD_Id(SPA_MEDIA_SUBTYPE_raw),
  SPA_FORMAT_VIDEO_format,SPA_POD_Id(SPA_VIDEO_FORMAT_RGBA),SPA_FORMAT_VIDEO_size,SPA_POD_Rectangle(&SPA_RECTANGLE(WIDTH,HEIGHT)),
  SPA_FORMAT_VIDEO_framerate,SPA_POD_Fraction(&SPA_FRACTION(0,1)),SPA_FORMAT_VIDEO_maxFramerate,SPA_POD_Fraction(&SPA_FRACTION(30,1)))};
 if(pw_stream_connect(fixture.stream,PW_DIRECTION_OUTPUT,PW_ID_ANY,PW_STREAM_FLAG_DRIVER|PW_STREAM_FLAG_ALLOC_BUFFERS,params,1)<0)fixture.failed=1;
 else pw_main_loop_run(fixture.main);
 pw_stream_destroy(fixture.stream);pw_main_loop_destroy(fixture.main);pw_deinit();
 fprintf(stderr,"Private source frames: %u\n",fixture.sequence);return fixture.failed;
}
