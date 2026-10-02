// Enumerate the OpenXR instance extensions offered by the active runtime.
#include <stdio.h>
#include <stdlib.h>
#include <openxr/openxr.h>
int main(void){uint32_t n=0; XrResult r=xrEnumerateInstanceExtensionProperties(NULL,0,&n,NULL); if(XR_FAILED(r)){printf("ERR %d\n",r);return 1;}
XrExtensionProperties*p=calloc(n,sizeof *p); for(uint32_t i=0;i<n;i++)p[i].type=XR_TYPE_EXTENSION_PROPERTIES;
xrEnumerateInstanceExtensionProperties(NULL,n,&n,p); for(uint32_t i=0;i<n;i++)printf("%s %u\n",p[i].extensionName,p[i].extensionVersion); return 0;}
