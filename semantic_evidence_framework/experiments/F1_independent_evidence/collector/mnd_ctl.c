// Tiny libmonado control client: mnd_ctl <focus|io|block_inputs|unblock> <client_name_substring>
// Used (a) by the experimenter to drive runtime transitions, (b) to test whether an APP-side
// process can change its own runtime-reported state (forgery test).
#include <stdio.h>
#include <string.h>
#include <monado/monado.h>
int main(int argc,char**argv){ if(argc<3){fprintf(stderr,"usage\n");return 1;}
  mnd_root_t*r=NULL; if(mnd_root_create(&r)!=MND_SUCCESS){printf("{\"ctl\":\"create_failed\"}\n");return 2;}
  mnd_root_update_client_list(r); uint32_t n=0; mnd_root_get_number_clients(r,&n);
  for(uint32_t i=0;i<n;i++){uint32_t id; const char*nm; mnd_root_get_client_id_at_index(r,i,&id); mnd_root_get_client_name(r,id,&nm);
    if(!strstr(nm,argv[2])) continue; mnd_result_t res=-99;
    if(!strcmp(argv[1],"focus")) res=mnd_root_set_client_focused(r,id);
    else if(!strcmp(argv[1],"io")) res=mnd_root_toggle_client_io_active(r,id);
    else if(!strcmp(argv[1],"block_inputs")) res=mnd_root_set_client_io_blocks(r,id,MND_IO_BLOCK_INPUTS);
    else if(!strcmp(argv[1],"unblock")) res=mnd_root_set_client_io_blocks(r,id,0);
    printf("{\"ctl\":\"%s\",\"client\":%u,\"name\":\"%s\",\"res\":%d}\n",argv[1],id,nm,res); }
  mnd_root_destroy(&r); return 0; }
