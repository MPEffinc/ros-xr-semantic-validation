from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


MONITORS = ['d3_full_guard', 'd3_native_guard']


def _truthy(value):
    return str(value).lower() in ('1', 'true', 'yes', 'on')


def _launch_setup(context, *args, **kwargs):
    dashboard = _truthy(LaunchConfiguration('dashboard').perform(context))
    dashboard_monitor = LaunchConfiguration('dashboard_monitor').perform(context)
    dashboard_host = LaunchConfiguration('dashboard_host').perform(context)
    dashboard_port = LaunchConfiguration('dashboard_port').perform(context)
    fresh_session = _truthy(LaunchConfiguration('fresh_session').perform(context))
    session_id = LaunchConfiguration('session_id').perform(context)
    nodes = []
    for index, monitor_id in enumerate(MONITORS):
        arguments = []
        wants_dashboard = dashboard and (
            dashboard_monitor == monitor_id
            or (dashboard_monitor == 'first' and index == 0)
        )
        if wants_dashboard:
            arguments.extend(['--dashboard', '--dashboard-host', dashboard_host, '--dashboard-port', dashboard_port])
            if fresh_session:
                arguments.append('--fresh-session')
            if session_id:
                arguments.extend(['--session-id', session_id])
        nodes.append(Node(package='monitor', executable=monitor_id, name=monitor_id, output='screen', arguments=arguments))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('dashboard', default_value='false'),
        DeclareLaunchArgument('dashboard_monitor', default_value='first'),
        DeclareLaunchArgument('dashboard_host', default_value='127.0.0.1'),
        DeclareLaunchArgument('dashboard_port', default_value='8765'),
        DeclareLaunchArgument('fresh_session', default_value='false'),
        DeclareLaunchArgument('session_id', default_value=''),
        OpaqueFunction(function=_launch_setup),
    ])
