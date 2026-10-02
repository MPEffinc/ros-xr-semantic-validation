// F1 runtime-side evidence collector: polls monado-service through libmonado (out of the app's
// process) and emits one JSON line per client per poll: flags + session running state.
// Build: gcc -O2 -I/opt/monado/include -o mnd_collector mnd_collector.c -L/opt/monado/lib -lmonado
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <monado/monado.h>
static double wall(void){struct timespec t;clock_gettime(CLOCK_REALTIME,&t);return t.tv_sec+t.tv_nsec*1e-9;}
static double mono(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
int main(int argc,char**argv){
  double period = argc>1 ? atof(argv[1]) : 0.01, dur = argc>2 ? atof(argv[2]) : 1e9;
  setvbuf(stdout,NULL,_IOLBF,0);
  mnd_root_t *root=NULL; mnd_result_t r;
  double t0=mono();
  while((r=mnd_root_create(&root))!=MND_SUCCESS){ if(mono()-t0>10){printf("{\"fatal\":\"mnd_root_create\",\"res\":%d}\n",r);return 2;} struct timespec s={0,100000000};nanosleep(&s,NULL);}
  unsigned long seq=0;
  while(mono()-t0<dur){
    r=mnd_root_update_client_list(root);
    if(r!=MND_SUCCESS){printf("{\"wall\":%.6f,\"mono\":%.6f,\"err\":\"update_client_list\",\"res\":%d}\n",wall(),mono(),r); break;}
    uint32_t n=0; mnd_root_get_number_clients(root,&n);
    for(uint32_t i=0;i<n;i++){
      uint32_t id=0,flags=0; const char*name="?"; mnd_session_state_t ss={0};
      mnd_root_get_client_id_at_index(root,i,&id); mnd_root_get_client_name(root,id,&name);
      mnd_root_get_client_state(root,id,&flags); /* session_running_state NOT queried: at Monado 045931d it kills monado-service for a client without a session (F1 smoke, 2026-10-02) */ (void)ss;
      printf("{\"seq\":%lu,\"wall\":%.6f,\"mono\":%.6f,\"client\":%u,\"name\":\"%s\",\"flags\":%u,\"focused\":%d,\"visible\":%d,\"active\":%d,\"io\":%d,\"inputs_blocked\":%d}\n",
        seq,wall(),mono(),id,name,flags,!!(flags&MND_CLIENT_SESSION_FOCUSED),!!(flags&MND_CLIENT_SESSION_VISIBLE),!!(flags&MND_CLIENT_SESSION_ACTIVE),!!(flags&MND_CLIENT_IO_ACTIVE),!!(flags&MND_CLIENT_INPUTS_BLOCKED));
    }
    if(n==0) printf("{\"seq\":%lu,\"wall\":%.6f,\"mono\":%.6f,\"clients\":0}\n",seq,wall(),mono());
    seq++; struct timespec s={(time_t)period,(long)((period-(long)period)*1e9)}; nanosleep(&s,NULL);
  }
  mnd_root_destroy(&root); return 0;
}
