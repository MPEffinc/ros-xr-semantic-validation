// PickNik Quest semantic-validation side-band logger.
//
// This file intentionally has no ROS client or ROS message dependency. It
// reads the same controller GameObject Transforms as
// RosPublishers and writes independent JSONL under persistentDataPath. The
// production Odometry/TF schemas and calls are not touched.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.XR;

[DefaultExecutionOrder(32000)]
public sealed class PickNikTrackingSidebandLogger : MonoBehaviour
{
    [Serializable]
    private sealed class Sample
    {
        public string event_type;
        public string wall_utc;
        public long wall_unix_ms;
        public double unity_realtime_s;
        public int unity_frame;
        public string unity_phase;
        public bool application_focused;
        public bool application_paused;
        public bool xr_display_running;
        public string side;
        public bool input_present;
        public int input_device_id;
        public string input_device_name;
        public bool is_tracked;
        public int tracking_state;
        public bool game_object_present;
        public bool active_self;
        public bool active_in_hierarchy;
        public float position_x;
        public float position_y;
        public float position_z;
        public float orientation_x;
        public float orientation_y;
        public float orientation_z;
        public float orientation_w;
        public string detail;
    }

    private const double SamplePeriodSeconds = 1.0 / 60.0;
    private const double FlushPeriodSeconds = 1.0;
    private static PickNikTrackingSidebandLogger _instance;

    private readonly List<XRDisplaySubsystem> _displaySubsystems = new List<XRDisplaySubsystem>();
    private readonly StringBuilder _pending = new StringBuilder(64 * 1024);
    private StreamWriter _writer;
    private RosPublishers _publishers;
    private InputAction _leftIsTracked;
    private InputAction _leftTrackingState;
    private InputAction _rightIsTracked;
    private InputAction _rightTrackingState;
    private double _nextSampleTime;
    private double _nextFlushTime;
    private bool _applicationPaused;
    private int _lastLeftTrackingState = Int32.MinValue;
    private int _lastRightTrackingState = Int32.MinValue;
    private bool _lastLeftIsTracked;
    private bool _lastRightIsTracked;
    private bool _haveLeftState;
    private bool _haveRightState;

    public string LogPath { get; private set; }

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    private static void Bootstrap()
    {
        if (_instance != null)
        {
            return;
        }

        GameObject loggerObject = new GameObject("PICKNIK_SEMANTIC_SIDEBAND");
        DontDestroyOnLoad(loggerObject);
        _instance = loggerObject.AddComponent<PickNikTrackingSidebandLogger>();
    }

    private void Awake()
    {
        if (_instance != null && _instance != this)
        {
            Destroy(gameObject);
            return;
        }
        _instance = this;

        string runId = DateTime.UtcNow.ToString("yyyyMMddTHHmmssZ", CultureInfo.InvariantCulture);
        LogPath = Path.Combine(Application.persistentDataPath, "picknik_semantic_validation_" + runId + ".jsonl");
        _writer = new StreamWriter(LogPath, false, new UTF8Encoding(false), 64 * 1024);

        _leftIsTracked = MakeAction("left_is_tracked", "<XRController>{LeftHand}/isTracked", "Button");
        _leftTrackingState = MakeAction("left_tracking_state", "<XRController>{LeftHand}/trackingState", "Integer");
        _rightIsTracked = MakeAction("right_is_tracked", "<XRController>{RightHand}/isTracked", "Button");
        _rightTrackingState = MakeAction("right_tracking_state", "<XRController>{RightHand}/trackingState", "Integer");

        InputSystem.onDeviceChange += OnDeviceChange;
        ResolvePublishers();
        WriteEvent("logger_started", "none", "path=" + LogPath);
        Debug.Log("PICKNIK_SEMANTIC_LOG=" + LogPath);
    }

    private static InputAction MakeAction(string name, string binding, string expectedControlType)
    {
        InputAction action = new InputAction(
            name: name,
            type: InputActionType.PassThrough,
            binding: binding,
            expectedControlType: expectedControlType);
        action.Enable();
        return action;
    }

    private void ResolvePublishers()
    {
        _publishers = FindFirstObjectByType<RosPublishers>();
        if (_publishers == null)
        {
            WriteEvent("publisher_not_found", "none", "RosPublishers is absent from current scene");
        }
        else
        {
            WriteEvent("publisher_resolved", "none", _publishers.gameObject.name);
        }
    }

    private void LateUpdate()
    {
        double now = Time.realtimeSinceStartupAsDouble;
        if (_publishers == null)
        {
            ResolvePublishers();
        }

        if (now < _nextSampleTime)
        {
            return;
        }
        _nextSampleTime = now + SamplePeriodSeconds;

        CaptureSide("left", _publishers != null ? _publishers.leftController : null,
            _leftIsTracked, _leftTrackingState, ref _haveLeftState,
            ref _lastLeftIsTracked, ref _lastLeftTrackingState);
        CaptureSide("right", _publishers != null ? _publishers.rightController : null,
            _rightIsTracked, _rightTrackingState, ref _haveRightState,
            ref _lastRightIsTracked, ref _lastRightTrackingState);

        if (now >= _nextFlushTime)
        {
            FlushPending();
            _nextFlushTime = now + FlushPeriodSeconds;
        }
    }

    private void CaptureSide(
        string side,
        GameObject controller,
        InputAction isTrackedAction,
        InputAction trackingStateAction,
        ref bool havePrevious,
        ref bool lastIsTracked,
        ref int lastTrackingState)
    {
        bool isTracked = ReadTracked(isTrackedAction);
        int trackingState = ReadTrackingState(trackingStateAction);
        UnityEngine.InputSystem.InputDevice device = trackingStateAction != null && trackingStateAction.activeControl != null
            ? trackingStateAction.activeControl.device
            : (isTrackedAction != null && isTrackedAction.activeControl != null
                ? isTrackedAction.activeControl.device
                : null);

        Sample sample = NewSample("raw_sample", side, "late_update");
        sample.input_present = device != null && device.added;
        sample.input_device_id = device != null ? device.deviceId : -1;
        sample.input_device_name = device != null ? device.displayName : "";
        sample.is_tracked = isTracked;
        sample.tracking_state = trackingState;
        PopulateTransform(sample, controller);
        Append(sample);

        if (!havePrevious || isTracked != lastIsTracked || trackingState != lastTrackingState)
        {
            Sample transition = NewSample("tracking_transition", side, "late_update");
            transition.input_present = sample.input_present;
            transition.input_device_id = sample.input_device_id;
            transition.input_device_name = sample.input_device_name;
            transition.is_tracked = isTracked;
            transition.tracking_state = trackingState;
            transition.detail = havePrevious
                ? "is_tracked=" + lastIsTracked + "->" + isTracked
                    + ",tracking_state=" + lastTrackingState + "->" + trackingState
                : "initial_tracking_state";
            PopulateTransform(transition, controller);
            Append(transition);
        }

        havePrevious = true;
        lastIsTracked = isTracked;
        lastTrackingState = trackingState;
    }

    private static bool ReadTracked(InputAction action)
    {
        if (action == null || !action.enabled || action.activeControl == null)
        {
            return false;
        }
        return action.ReadValue<float>() >= 0.5f;
    }

    private static int ReadTrackingState(InputAction action)
    {
        if (action == null || !action.enabled || action.activeControl == null)
        {
            return 0;
        }
        return action.ReadValue<int>();
    }

    private static void PopulateTransform(Sample sample, GameObject controller)
    {
        sample.game_object_present = controller != null;
        if (controller == null)
        {
            return;
        }

        sample.active_self = controller.activeSelf;
        sample.active_in_hierarchy = controller.activeInHierarchy;
        Vector3 position = controller.transform.position;
        Quaternion orientation = controller.transform.rotation;
        sample.position_x = position.x;
        sample.position_y = position.y;
        sample.position_z = position.z;
        sample.orientation_x = orientation.x;
        sample.orientation_y = orientation.y;
        sample.orientation_z = orientation.z;
        sample.orientation_w = orientation.w;
    }

    private Sample NewSample(string eventType, string side, string phase)
    {
        DateTime now = DateTime.UtcNow;
        SubsystemManager.GetSubsystems(_displaySubsystems);
        bool xrRunning = false;
        for (int index = 0; index < _displaySubsystems.Count; ++index)
        {
            if (_displaySubsystems[index] != null && _displaySubsystems[index].running)
            {
                xrRunning = true;
                break;
            }
        }

        return new Sample
        {
            event_type = eventType,
            wall_utc = now.ToString("O", CultureInfo.InvariantCulture),
            wall_unix_ms = new DateTimeOffset(now).ToUnixTimeMilliseconds(),
            unity_realtime_s = Time.realtimeSinceStartupAsDouble,
            unity_frame = Time.frameCount,
            unity_phase = phase,
            application_focused = Application.isFocused,
            application_paused = _applicationPaused,
            xr_display_running = xrRunning,
            side = side,
            input_device_id = -1,
            input_device_name = "",
            detail = "",
        };
    }

    private void WriteEvent(string eventType, string side, string detail)
    {
        Sample sample = NewSample(eventType, side, "event");
        sample.detail = detail;
        Append(sample);
    }

    private void Append(Sample sample)
    {
        _pending.Append(JsonUtility.ToJson(sample));
        _pending.Append('\n');
    }

    private void FlushPending()
    {
        if (_writer == null || _pending.Length == 0)
        {
            return;
        }
        _writer.Write(_pending.ToString());
        _pending.Clear();
        _writer.Flush();
    }

    private void OnApplicationFocus(bool hasFocus)
    {
        WriteEvent("application_focus", "none", "focused=" + hasFocus);
        FlushPending();
    }

    private void OnApplicationPause(bool paused)
    {
        _applicationPaused = paused;
        WriteEvent("application_pause", "none", "paused=" + paused);
        FlushPending();
    }

    private void OnDeviceChange(UnityEngine.InputSystem.InputDevice device, InputDeviceChange change)
    {
        string detail = "change=" + change
            + ",device_id=" + (device != null ? device.deviceId : -1)
            + ",device=" + (device != null ? device.displayName : "");
        WriteEvent("input_device_change", "none", detail);
    }

    private void OnDestroy()
    {
        InputSystem.onDeviceChange -= OnDeviceChange;
        WriteEvent("logger_stopped", "none", "destroyed");
        FlushPending();
        if (_writer != null)
        {
            _writer.Dispose();
            _writer = null;
        }
        _leftIsTracked?.Dispose();
        _leftTrackingState?.Dispose();
        _rightIsTracked?.Dispose();
        _rightTrackingState?.Dispose();
        if (_instance == this)
        {
            _instance = null;
        }
    }
}
