"""Expand the model and run its single transform publisher and optional RViz."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from course_description.model import expand_model
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def launch_nodes(context):
    """Validate dimensions and expand the selected Xacro before starting ROS."""
    model = LaunchConfiguration('model').perform(context)
    dimensions = {
        name: LaunchConfiguration(name).perform(context)
        for name in ('wheelbase', 'track', 'wheel_radius')
    }
    description = expand_model(model, **dimensions)
    share = Path(get_package_share_directory('course_description'))
    return [
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            name='robot_state_publisher', output='screen',
            parameters=[{
                'robot_description': ParameterValue(description, value_type=str),
                'use_sim_time': False,
            }],
        ),
        Node(
            package='rviz2', executable='rviz2', output='screen',
            arguments=['-d', str(share / 'rviz/vehicle.rviz'),
                       '--display-title-format', 'PR06-RViz'],
            condition=IfCondition(LaunchConfiguration('rviz')),
        ),
    ]


def generate_launch_description():
    share = Path(get_package_share_directory('course_description'))
    return LaunchDescription([
        DeclareLaunchArgument('model', default_value=str(share / 'urdf/vehicle.urdf.xacro')),
        DeclareLaunchArgument('wheelbase', default_value='0.8'),
        DeclareLaunchArgument('track', default_value='0.62'),
        DeclareLaunchArgument('wheel_radius', default_value='0.12'),
        DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false']),
        OpaqueFunction(function=launch_nodes),
    ])
