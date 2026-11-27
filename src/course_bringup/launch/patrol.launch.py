"""Launch the patrol system and optionally record its sensor stream."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Keep the simulator global while namespacing the course nodes."""
    namespace = LaunchConfiguration('namespace')
    record = LaunchConfiguration('record')
    bag_dir = LaunchConfiguration('bag_dir')
    reliability = LaunchConfiguration('subscriber_reliability')
    sensor_topic = PathJoinSubstitution(['/', namespace, 'sensor_pose'])
    return LaunchDescription([
        DeclareLaunchArgument(
            'namespace', default_value='robot_a', description='Namespace for patrol and QoS nodes',
        ),
        DeclareLaunchArgument(
            'record', default_value='false', choices=['true', 'false'],
            description='Start an MCAP recorder when true',
        ),
        DeclareLaunchArgument(
            'bag_dir', default_value='evidence/pr05/bag',
            description='New directory for the single sensor stream recording',
        ),
        DeclareLaunchArgument(
            'subscriber_reliability', default_value='best_effort',
            choices=['best_effort', 'reliable'],
            description='Subscriber reliability selected at startup',
        ),
        LogInfo(msg=['Patrol namespace: ', namespace, '; record: ', record]),
        Node(
            package='turtlesim', executable='turtlesim_node',
            name='turtlesim', namespace='/', output='screen',
            parameters=[{'use_sim_time': False}],
        ),
        Node(
            package='patrol', executable='patrol', namespace=namespace, output='screen',
            parameters=[{'use_sim_time': False}],
            remappings=[
                ('turtle1/pose', '/turtle1/pose'),
                ('cmd_vel', '/turtle1/cmd_vel'),
            ],
        ),
        Node(
            package='course_bringup', executable='pose_relay',
            namespace=namespace, output='screen',
            parameters=[{'use_sim_time': False}],
            remappings=[('pose', '/turtle1/pose')],
        ),
        Node(
            package='course_bringup', executable='pose_subscriber',
            namespace=namespace, output='screen',
            parameters=[{'reliability': reliability, 'use_sim_time': False}],
        ),
        ExecuteProcess(
            cmd=[
                'ros2', 'bag', 'record', '-s', 'mcap', '-o', bag_dir,
                '--topics', sensor_topic, '--disable-keyboard-controls',
            ],
            condition=IfCondition(record),
            output='screen',
        ),
    ])
