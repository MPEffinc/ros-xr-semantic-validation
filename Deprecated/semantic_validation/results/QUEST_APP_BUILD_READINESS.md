# Quest App Build Readiness

Date: 2026-09-14

## Scope and safety boundary

This report records the current local source, editor, Android toolchain,
licensing, artifact, and ADB readiness for Quest-facing components. No Quest was
connected, no APK was installed, and no commercial license was bypassed. All
Unity execution used disposable project copies under `/tmp`.

## Installed toolchain

| Component | Observed current state |
| --- | --- |
| Unity Editor | `6000.1.6f1 (d64b1a599cad)` at `/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity` |
| Android Build Support | Present under `Editor/Data/PlaybackEngines/AndroidPlayer` |
| OpenJDK | Bundled Temurin `17.0.9+9`; `java` and `javac` both executable |
| Android SDK | Bundled platforms `android-34`, `android-35`, `android-36`; build-tools `34.0.0`; command-line tools `16.0` |
| Android NDK | Bundled `27.2.12479018` (`r27c`) |
| ADB | Bundled `34.0.5-10900879`; system `/usr/bin/adb` is Debian `34.0.4` |
| Unity license | Licensing client starts, but reports `Found 0 entitlement groups and 0 free entitlements` and `No valid Unity Editor license found` |

The installed Android modules are complete enough for Unity Android compilation
once an editor is licensed. An interactive Unity account/license activation is
the exact remaining manual requirement for `6000.1.6f1`. Editors `6000.2.10f1`
and `6000.3.9f1` are not installed.

The future device-side command surface is available without further host ADB
installation:

```bash
UNITY_ANDROID=/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Data/PlaybackEngines/AndroidPlayer
$UNITY_ANDROID/SDK/platform-tools/adb devices -l
$UNITY_ANDROID/SDK/platform-tools/adb install -r <artifact.apk>
$UNITY_ANDROID/SDK/platform-tools/adb logcat
```

These device commands were not executed in this Quest-free phase.

## Framework results

### Docker_Teleop

- Pinned revision: `64cbdde88bc52c6a80d37f994752e50f95ba537e`
- Quest source: complete Unity project at
  `semantic_validation/targets/docker_teleop/UnityApp`
- Requested editor: `6000.2.10f1 (d3d30d158480)`
- Installed exact editor: no
- Build entrypoint:
  `Assets/Editor/CommandLineQuestBuild.cs`, method
  `CommandLineQuestBuild.BuildQuestApk`
- Intended output: `App_Build/Ros_Unity_latest.apk`
- Enabled build scene: `Assets/Scenes/GazeboReplica_DualArm_MR.unity`
- Android configuration: ARM64, minimum API 32, IL2CPP,
  application ID `com.noahli.ROSUNITY`
- Local APK/AAB: official upstream release asset downloaded to the git-ignored local path
  `local_artifacts/quest_apps/docker_teleop/R.U_7.0.7.apk`
- Artifact verification: size `121245277` bytes; SHA-256
  `257828a6d2d9da1daf17692d68a69ddf12ec08f5df444e1feeeb5afff6084cf4`;
  ZIP integrity PASS; APK Signature Scheme v2 verifies with one Android debug signer;
  package `com.noahli.ROSUNITY`, versionName `1.0.1`, minimum API 32, target API 36
- License: upstream README explicitly says the project license is pending.

No source build was attributed to this project. The current machine has neither the
project-pinned editor nor a valid Unity entitlement. However, pinned upstream documentation
publishes release `unity-app-7.0.7` and its `R.U_7.0.7.apk`; that exact public asset is now locally
available and independently integrity/signature checked. Install and wired-development setup are:

```bash
ADB=/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Data/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb
$ADB devices -l
$ADB install -r -d local_artifacts/quest_apps/docker_teleop/R.U_7.0.7.apk
$ADB reverse tcp:5026 tcp:5026
$ADB reverse tcp:10001 tcp:10001
```

The published APK targets `127.0.0.1:5026` for controller TCP and `127.0.0.1:10001` for ROS,
so these reverse rules are part of the artifact contract. They were not executed because Quest is
forbidden in this phase. If rebuilding from source, once both editor and entitlement are supplied,
the repository-provided noninteractive build is:

```bash
Unity -batchmode -nographics -quit \
  -projectPath <UnityApp-copy> \
  -executeMethod CommandLineQuestBuild.BuildQuestApk \
  -apkPath <output.apk>
```

Readiness: `APK_ARTIFACT_READY`; source rebuild remains
`BLOCKED_EDITOR_VERSION_AND_LICENSE`. The artifact is local-only and is not committed.

### PickNik `meta_quest_teleoperation`

- Pinned revision: `bbaef0762fdb0b429b8ea12a4ca65040748b41dd`
- Quest source: complete Unity project at
  `semantic_validation/targets/meta_quest_teleoperation/UnityProject`
- Requested editor: `6000.1.6f1 (d64b1a599cad)`
- Installed exact editor: yes
- Enabled build scene: `Assets/Scenes/SampleScene.unity`
- Android configuration: ARM64, minimum API 32, IL2CPP,
  application ID `com.unity.template.vr`
- Packages include OpenXR `1.14.3`, XR Hands `1.5.0`, XRI `3.1.1`, and the
  Unity ROS-TCP Connector Git dependency.
- Repository-provided batch APK build method: none found
- Local APK/AAB: none
- License: BSD-3-Clause repository license; Unity Editor entitlement is
  separately required.

An actual batch import/compile was attempted on a disposable project copy:

```bash
/home/cclab/Unity/Hub/Editor/6000.1.6f1/Editor/Unity \
  -batchmode -nographics -quit \
  -projectPath /tmp/picknik_unity_readiness \
  -logFile /tmp/picknik_unity_readiness.log
```

The editor matched exactly, launched its licensing client, and exited `1`
before project import with:

```text
Found 0 entitlement groups and 0 free entitlements matching requested entitlement ids
No valid Unity Editor license found. Please activate your license.
```

Readiness: `BLOCKED_MANUAL_UNITY_LICENSE`. After legitimate activation, the
next machine-verifiable step is batch import/compile; APK construction still
needs either an explicitly selected build profile/scene in batch mode or a
clean-room editor build wrapper that does not change runtime behavior.

### Quest2ROS2

- Pinned revision: `07aaf65149c9e29103f1fc61deb466cef8a55cef`
- Repository content: ROS 2 host packages and message definitions only
- Quest Unity project, Android Gradle project, APK/AAB: none
- README requirement: install and configure the external `Quest2ROS` app from
  `quest2ros.github.io`
- Local repository contains 66 files; the only Unity-named match is Visual
  Studio metadata `.vs/ProjectSettings.json`, not frontend source.
- License: Apache-2.0 for the checked-out host repository

The ROS-side package is already runnable in the testbed, but no Quest app can be
built from this pinned repository. Readiness:
`EXTERNAL_BLACK_BOX_APP_REQUIRED`. A future hardware session must obtain the
external Quest2ROS application through its documented distribution path and
then use ADB or headset installation; source-level frontend build readiness
cannot be claimed here.

### Spes

- Pinned revision: `c5d808155a87b584d6147a5943d4b87c34c92db0`
- Frontend form: package-contained WebXR application, not a Quest APK
- Build system: PEP 517/setuptools, package `teleop==0.1.5`
- License: Apache-2.0

An actual network-isolated wheel build was completed from a disposable writable
copy of the pinned source after installing build-only tooling in the disposable
container:

```bash
python3 -m build --wheel --outdir /out
```

Result: `/tmp/spes_wheel_readiness/teleop-0.1.5-py3-none-any.whl`, 42,499 bytes.
Wheel inspection confirmed both Quest-facing web assets:

```text
teleop/index.html
teleop/assets/teleop-ui.js
```

Readiness: `WEBXR_BUILD_PASS`. No APK, Unity license, Android SDK, or ADB is
required for this frontend. A future Quest run requires only a compatible Quest
browser/WebXR session and the already documented WSS server URL/certificate
workflow. The temporary wheel was not added to Git.

### OpenVR UR5e

- Pinned revision: `170dad582d624f536359a3192a7f829669c2b031`
- Checked-in application: ROS 2 Jazzy/Python `quest_bridge`, not an Android or
  Unity Quest application
- Quest-side/runtime prerequisites in README: external ALVR client, Linux ALVR
  streamer, and SteamVR/OpenVR
- Local APK/AAB or Android build project: none
- Local ALVR/SteamVR executable: none found
- License: Apache-2.0

The fake-OpenVR ROS runtime is a separate Quest-less test path and does not
produce a Quest artifact. Readiness: `EXTERNAL_ALVR_AND_STEAMVR_REQUIRED`.
There is no app source in the pinned repository from which to produce an APK;
the future headset client must come from the ALVR distribution.

### Reachy VR Quest

- Pinned revision: `242120ee9e356e4a4f2117ee56c8b340c9b7ec64`
- Quest source: complete Unity project at
  `semantic_validation/targets/reachy_vr_quest`
- Requested editor: `6000.3.9f1 (7a9955a4f2fa)`
- Installed exact editor: no
- Enabled build scene: `Assets/Scenes/ReachyMiniTeleop.unity`
- Android configuration: ARM64, minimum API 32, target API 34,
  application ID `com.DefaultCompany.ReachyMiniTeleop`
- Packages include Meta XR SDK `201.0.0`, Unity OpenXR `1.16.1`, WebRTC
  `3.0.0`, NuGetForUnity, and the external Meta Movement Git package.
- Repository batch test method:
  `ReachyMiniTeleop.Tests.Editor.ReachyBatchTestRunner.RunEditMode`
- Local APK/AAB: none; README links to an externally hosted prebuilt APK
- License: MIT

No build was attributed to this project. Its pinned editor is absent, the only
installed Unity editor is unlicensed, and first import additionally requires
Unity package and NuGet restores. Readiness:
`BLOCKED_EDITOR_VERSION_LICENSE_AND_PACKAGE_RESTORE`. The externally hosted APK
was not downloaded or treated as a locally verified artifact.

## Consolidated status

| Framework | Quest artifact model | Actual build result | Current stop point |
| --- | --- | --- | --- |
| Docker_Teleop | source-visible Unity APK plus official release artifact | official APK downloaded and verified; no source build | **artifact ready**; source rebuild still needs exact editor + Unity license |
| PickNik | source-visible Unity APK | actual batch attempt, exit `1` | exact editor present; manual license activation required |
| Quest2ROS2 | external Quest2ROS app | not buildable from repository | black-box/external app distribution |
| Spes | WebXR assets inside Python wheel | `PASS` | Quest browser session only |
| OpenVR UR5e | external ALVR client | not buildable from repository | ALVR/SteamVR distribution and later Quest session |
| Reachy VR Quest | source-visible Unity APK | not run | exact editor, license, and package restore required |

No result in this report is native Quest execution evidence. `WEBXR_BUILD_PASS`
proves only package construction and asset inclusion. The Unity blockers are
tooling/authentication blockers, not negative semantic results.
