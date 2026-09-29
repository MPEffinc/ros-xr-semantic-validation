# Citation Graph

Only edges **seen in the citing paper's bibliography** (local arXiv HTML) are recorded. Topical similarity
is never recorded as an edge. Bracketed numbers are the reference numbers in the citing paper.

## A. Citation-edge matrix (listed papers → listed papers / keywords; only edges seen in bibliographies)

| Citing ↓ / Cited → | BadVLA | State Backdoor | SoK 2606 | XRoboToolkit | Isaac Lab (/Orbit) | TrojanRobot | BadRobot | LeRobot | robomimic | DROID | OXE | ALOHA | Open-TeleVision | AnyTeleop | GELLO | Bunny-VisionPro |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2505.16640 BadVLA | – | | | | | ✓ | | | | | ✓ | | | | | |
| 2601.04266 State Backdoor | ✓ [15] | – | | | | ✓ [14] | ✓ [11] | ✓ [20] | | | | ✓ [17] | | | | |
| 2609.26868 Industrial | | | | | | | | | | | | ✓ [5] | | | | |
| 2602.18742 RoboCurate | | | | | | | | | | ✓ | ✓ | | | | | |
| 2606.16788 SoK | ✓ [35] | ✓ [38] | – | | | ✓ [9] | ✓ [11] | | | | | | | | | |
| 2608.16843 Survey | ✓ [18] | ✓ [32] | ✓ [1] | | | ✓ [13] | ✓ [9] | | | | | | | | | |
| 2508.00097 XRoboToolkit | | | | – | | | | | | | | ✓ [11] | ✓ [14] | ✓ [12] | | |
| 2511.04831 Isaac Lab | | | | | (Orbit [63], Isaac Gym) | | | ✓ [11] | ✓ [59] | | | | ✓ [18] | | | |
| 2609.16437 XRoboToolKit-T | | | | ✓ [2] | ✓ [16] | | | | | | | ✓ [12] | ✓ [14] | ✓ [10] | | |

- Nobody in this set cites 2609.26868 (Industrial), RoboCurate or the 2608 survey.
- GELLO and Bunny-VisionPro are cited by no paper in this set.
- The security papers and the XR/teleop/sim papers form **two disconnected clusters**: no security paper cites XRoboToolkit, Isaac Lab or any XR teleop system, and no teleop paper cites any security paper.
- LIBERO (body or bibliography): BadVLA, State Backdoor; also the SoK (body only, §VII-B).

## B. Broader-search papers

- `2511.20992` (BC dataset poisoning) cites BAFFLE (Gong et al. 2024, offline-RL dataset poisoning), TrojDRL
  (Kiourti et al. 2020) and Turner et al. clean-label backdoors. **Bibliographies of the other Part B papers
  were not checked**; no edges are claimed for them.

## C. Edges relevant to the candidate question

| Question | Answer from the checked bibliographies |
|---|---|
| Does any demonstration-poisoning paper cite an XR teleop system (XRoboToolkit, Open-TeleVision, AnyTeleop, Bunny-VisionPro, GELLO)? | No (checked: BadVLA, State Backdoor, 2609.26868, SoK, 2608 survey). |
| Does any XR teleop / simulation framework paper cite a security paper? | No (checked: XRoboToolkit, XRoboToolKit-T, Isaac Lab). |
| Do the surveys cite the poisoning papers? | Yes: SoK → BadVLA [35], State Backdoor [38]; 2608 survey → BadVLA [18], State Backdoor [32], SoK [1]. |
| Is 2609.26868 (teleop-demo backdoors) cited by anyone in the set? | No (it is dated 2026-09-22). |

Not checked (NOT_VERIFIED): forward citations of any paper (who cites them) beyond the set above.
