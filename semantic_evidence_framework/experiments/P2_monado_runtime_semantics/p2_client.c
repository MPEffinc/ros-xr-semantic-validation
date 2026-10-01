// P2 OpenXR probe client (headless, XR_MND_headless). Logs, every ~10 ms, what the RUNTIME reports:
// session state, xrSyncActions result, boolean action state {isActive, currentState,
// changedSinceLastSync, lastChangeTime}, grip-space location flags, and events.
// Build: gcc -O2 -o p2_client p2_client.c -lopenxr_loader
// Run:   ./p2_client <seconds>   (JSON lines on stdout)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define XR_USE_PLATFORM_EGL 0
#include <openxr/openxr.h>

static double wall(void) { struct timespec t; clock_gettime(CLOCK_REALTIME, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
#define CHK(x) do { XrResult r_ = (x); if (XR_FAILED(r_)) { printf("{\"fatal\":\"%s\",\"res\":%d}\n", #x, r_); fflush(stdout); exit(2);} } while (0)

int main(int argc, char **argv) {
    double dur = argc > 1 ? atof(argv[1]) : 20.0;
    setvbuf(stdout, NULL, _IOLBF, 0);
    const char *ext[] = {XR_MND_HEADLESS_EXTENSION_NAME};
    XrInstanceCreateInfo ici = {XR_TYPE_INSTANCE_CREATE_INFO};
    strcpy(ici.applicationInfo.applicationName, "p2_probe");
    ici.applicationInfo.apiVersion = XR_MAKE_VERSION(1, 0, 0);
    ici.enabledExtensionCount = 1; ici.enabledExtensionNames = ext;
    XrInstance inst; CHK(xrCreateInstance(&ici, &inst));
    XrSystemGetInfo sgi = {XR_TYPE_SYSTEM_GET_INFO}; sgi.formFactor = XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
    XrSystemId sys; CHK(xrGetSystem(inst, &sgi, &sys));
    XrSessionCreateInfo sci = {XR_TYPE_SESSION_CREATE_INFO}; sci.systemId = sys;   // headless: no graphics binding
    XrSession s; CHK(xrCreateSession(inst, &sci, &s));

    XrActionSetCreateInfo asci = {XR_TYPE_ACTION_SET_CREATE_INFO};
    strcpy(asci.actionSetName, "p2"); strcpy(asci.localizedActionSetName, "p2");
    XrActionSet as; CHK(xrCreateActionSet(inst, &asci, &as));
    XrPath right; CHK(xrStringToPath(inst, "/user/hand/right", &right));
    XrActionCreateInfo aci = {XR_TYPE_ACTION_CREATE_INFO};
    aci.actionType = XR_ACTION_TYPE_BOOLEAN_INPUT; strcpy(aci.actionName, "deadman"); strcpy(aci.localizedActionName, "deadman");
    XrAction dead; CHK(xrCreateAction(as, &aci, &dead));
    aci.actionType = XR_ACTION_TYPE_POSE_INPUT; strcpy(aci.actionName, "grip"); strcpy(aci.localizedActionName, "grip");
    XrAction grip; CHK(xrCreateAction(as, &aci, &grip));
    XrPath prof, b_dead, b_grip;
    CHK(xrStringToPath(inst, "/interaction_profiles/valve/index_controller", &prof));
    CHK(xrStringToPath(inst, "/user/hand/right/input/a/click", &b_dead));
    CHK(xrStringToPath(inst, "/user/hand/right/input/grip/pose", &b_grip));
    XrActionSuggestedBinding sb[2] = {{dead, b_dead}, {grip, b_grip}};
    XrInteractionProfileSuggestedBinding ipsb = {XR_TYPE_INTERACTION_PROFILE_SUGGESTED_BINDING};
    ipsb.interactionProfile = prof; ipsb.countSuggestedBindings = 2; ipsb.suggestedBindings = sb;
    CHK(xrSuggestInteractionProfileBindings(inst, &ipsb));
    XrSessionActionSetsAttachInfo att = {XR_TYPE_SESSION_ACTION_SETS_ATTACH_INFO}; att.countActionSets = 1; att.actionSets = &as;
    CHK(xrAttachSessionActionSets(s, &att));
    XrReferenceSpaceCreateInfo rsci = {XR_TYPE_REFERENCE_SPACE_CREATE_INFO};
    rsci.referenceSpaceType = XR_REFERENCE_SPACE_TYPE_LOCAL; rsci.poseInReferenceSpace.orientation.w = 1;
    XrSpace local; CHK(xrCreateReferenceSpace(s, &rsci, &local));
    XrActionSpaceCreateInfo asc = {XR_TYPE_ACTION_SPACE_CREATE_INFO}; asc.action = grip; asc.poseInActionSpace.orientation.w = 1;
    XrSpace gsp; CHK(xrCreateActionSpace(s, &asc, &gsp));

    XrSessionState st = XR_SESSION_STATE_UNKNOWN; int running = 0;
    double t0 = wall(); XrTime last_xr = 0;
    while (wall() - t0 < dur) {
        XrEventDataBuffer ev = {XR_TYPE_EVENT_DATA_BUFFER};
        while (xrPollEvent(inst, &ev) == XR_SUCCESS) {
            if (ev.type == XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED) {
                XrEventDataSessionStateChanged *e = (XrEventDataSessionStateChanged *)&ev; st = e->state;
                printf("{\"wall\":%.6f,\"event\":\"state\",\"state\":%d,\"time\":%lld}\n", wall(), st, (long long)e->time);
                if (st == XR_SESSION_STATE_READY && !running) {
                    XrSessionBeginInfo bi = {XR_TYPE_SESSION_BEGIN_INFO}; bi.primaryViewConfigurationType = XR_VIEW_CONFIGURATION_TYPE_PRIMARY_STEREO;
                    XrResult r = xrBeginSession(s, &bi); printf("{\"wall\":%.6f,\"event\":\"begin\",\"res\":%d}\n", wall(), r); running = XR_SUCCEEDED(r);
                }
            } else if (ev.type == XR_TYPE_EVENT_DATA_INTERACTION_PROFILE_CHANGED) {
                printf("{\"wall\":%.6f,\"event\":\"profile_changed\"}\n", wall());
            } else if (ev.type == XR_TYPE_EVENT_DATA_REFERENCE_SPACE_CHANGE_PENDING) {
                XrEventDataReferenceSpaceChangePending *e = (XrEventDataReferenceSpaceChangePending *)&ev;
                printf("{\"wall\":%.6f,\"event\":\"ref_space_change\",\"changeTime\":%lld,\"poseValid\":%d}\n", wall(), (long long)e->changeTime, e->poseValid);
            } else {
                printf("{\"wall\":%.6f,\"event\":\"other\",\"type\":%d}\n", wall(), ev.type);
            }
            ev.type = XR_TYPE_EVENT_DATA_BUFFER;
        }
        if (running) {
            XrActiveActionSet aas = {as, XR_NULL_PATH};
            XrActionsSyncInfo si = {XR_TYPE_ACTIONS_SYNC_INFO}; si.countActiveActionSets = 1; si.activeActionSets = &aas;
            XrResult rs = xrSyncActions(s, &si);
            XrActionStateGetInfo gi = {XR_TYPE_ACTION_STATE_GET_INFO}; gi.action = dead;
            XrActionStateBoolean b = {XR_TYPE_ACTION_STATE_BOOLEAN}; XrResult rb = xrGetActionStateBoolean(s, &gi, &b);
            gi.action = grip; XrActionStatePose ps = {XR_TYPE_ACTION_STATE_POSE}; xrGetActionStatePose(s, &gi, &ps);
            // time for locate: use lastChangeTime-independent "now" estimate from the previous xrLocate result
            XrSpaceLocation loc = {XR_TYPE_SPACE_LOCATION};
            XrTime t = last_xr ? last_xr + 10000000 : 1;
            XrResult rl = xrLocateSpace(gsp, local, t, &loc);
            if (b.lastChangeTime > last_xr) last_xr = b.lastChangeTime;
            printf("{\"wall\":%.6f,\"state\":%d,\"sync\":%d,\"get\":%d,\"isActive\":%d,\"current\":%d,\"changed\":%d,\"lastChangeTime\":%lld,"
                   "\"poseActive\":%d,\"loc\":%d,\"flags\":%llu}\n",
                   wall(), st, rs, rb, b.isActive, b.currentState, b.changedSinceLastSync, (long long)b.lastChangeTime,
                   ps.isActive, rl, (unsigned long long)loc.locationFlags);
        }
        struct timespec sl = {0, 10000000}; nanosleep(&sl, NULL);
    }
    if (running) xrEndSession(s);
    xrDestroySession(s); xrDestroyInstance(inst);
    return 0;
}
