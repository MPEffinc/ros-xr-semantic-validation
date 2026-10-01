# Audit method (applies to every implementation)

## Path traced per implementation

source API → XR app → transport/bridge → ROS receiver → mapper → command generation → final consumer

## Items checked at every hop

| # | Item | Questions |
|---|---|---|
| A1 | focus/session, action active | Is `isActive` / session state read? Is it forwarded? Does anyone consume it? |
| A2 | valid vs tracked | Are the `*_VALID_BIT` and `*_TRACKED_BIT` flags (or the SDK equivalent) distinguished? Are they forwarded? |
| A3 | buttons/toggle/clutch/deadman | Where is the state latched or cached? Is it reset on deactivate/disconnect? |
| A4 | device / interaction-profile change | Is `XrEventDataInteractionProfileChanged` or a hand/controller swap handled? |
| A5 | origin-change event and effective time | Is `XrEventDataReferenceSpaceChangePending` (`changeTime`, `poseValid`) or a recenter equivalent handled? |
| A6 | calibration/anchor update and the transform used | Which transform multiplies which sample? Is it "latest" or "at the sample time"? |
| A7 | disconnect/reconnect, pause/resume | What state persists? Does the consumer time out? |
| A8 | pending commands, previous goal, resume | Is there a stale target, a queued command or an auto-resume? |
| A9 | source→command→consumer linkage | Can one consumed command be traced to its source sample (id, stamp)? |

## Recording rules

- Every judgment cites: upstream URL, commit, file, function, line range, message field.
- **SDK wrappers.** If a wrapper (e.g., Unity `InputDevice`, Meta OVR, OpenVR) hides the source fields,
  trace up to the wrapper boundary. Mark what lies beyond it NOT_VERIFIED, and do not record it as
  absent.
- **Search misses.** A failed search is not proof of absence. Record the queries used and label the
  result `NOT_FOUND_IN_SEARCH`, not "missing".
- **Kinds of evidence.** Keep README claims (AUTHOR_CLAIM), code reading (SOURCE_CONFIRMED) and runtime
  observation (EXPERIMENT_CONFIRMED / PRIOR_INTERNAL) apart.
- **Forks.** A fork of the same code is not an independent implementation. Record the lineage.
- **Closed or commercial parts.** Where part of the path is closed-source or commercial (e.g., PickNik
  host side, MoveIt Pro), state the frontend scope that was checked and the host scope that was not.
