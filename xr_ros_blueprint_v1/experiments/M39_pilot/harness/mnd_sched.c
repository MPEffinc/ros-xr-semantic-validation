// F2 runtime-transition scheduler: one persistent libmonado connection; toggles IO of the named client at
// absolute CLOCK_REALTIME times read from argv (pairs "off_time,on_time"), logging call/return wall times.
// Usage: mnd_sched <client_substring> <t0_wall> <off1> <on1> [<off2> <on2> ...]   (times relative to t0)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <monado/monado.h>
static double wall(void){struct timespec t;clock_gettime(CLOCK_REALTIME,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static void sleep_until(double w){struct timespec t; t.tv_sec=(time_t)w; t.tv_nsec=(long)((w-(double)t.tv_sec)*1e9); clock_nanosleep(CLOCK_REALTIME,TIMER_ABSTIME,&t,NULL);}
int main(int argc,char**argv){ if(argc<5||(argc-3)%2){fprintf(stderr,"usage\n");return 1;}
  setvbuf(stdout,NULL,_IOLBF,0); double t0=atof(argv[2]);
  mnd_root_t*r=NULL; while(mnd_root_create(&r)!=MND_SUCCESS){struct timespec s={0,50000000};nanosleep(&s,NULL);}
  uint32_t id=0; int found=0;
  for(int tries=0;tries<200&&!found;tries++){ mnd_root_update_client_list(r); uint32_t n=0; mnd_root_get_number_clients(r,&n);
    for(uint32_t i=0;i<n;i++){uint32_t c; const char*nm; mnd_root_get_client_id_at_index(r,i,&c); mnd_root_get_client_name(r,c,&nm); if(strstr(nm,argv[1])){id=c;found=1;}}
    if(!found){struct timespec s={0,50000000};nanosleep(&s,NULL);} }
  if(!found){printf("{\"err\":\"client_not_found\"}\n");return 2;}
  for(int i=3;i<argc;i++){ double target=t0+atof(argv[i]); sleep_until(target); double c=wall();
    mnd_result_t res=mnd_root_toggle_client_io_active(r,id); double e=wall();
    printf("{\"kind\":\"%s\",\"target\":%.6f,\"call\":%.6f,\"ret\":%.6f,\"res\":%d}\n",((i-3)%2)?"on":"off",target,c,e,res); }
  mnd_root_destroy(&r); return 0; }
