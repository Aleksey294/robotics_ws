"""Publish parameter-controlled commands after receiving a turtlesim pose."""

from typing import Optional

from geometry_msgs.msg import Twist
from patrol.parameters import validate_parameters
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.node import Node
try:
    from turtlesim_msgs.msg import Pose
except ModuleNotFoundError:
    from turtlesim.msg import Pose


def command_for_pose(
    last_pose: Optional[Pose], linear_speed: float = 0.5, turn_rate: float = 0.3,
) -> Twist:
    """Choose a velocity command from the most recently received pose."""
    command = Twist()
    if last_pose is not None:
        command.linear.x = linear_speed
        command.angular.z = turn_rate
    return command


class Patrol(Node):
    """Validate proposals, then apply accepted settings to a single timer."""

    def __init__(self, **kwargs) -> None:
        super().__init__('patrol', **kwargs)
        self.linear_speed = self.declare_parameter('linear_speed', 0.5).value
        self.turn_rate = self.declare_parameter('turn_rate', 0.3).value
        self.publish_hz = self.declare_parameter('publish_hz', 10.0).value
        reason = validate_parameters(
            self.linear_speed, self.turn_rate, self.publish_hz,
        )
        if reason:
            self.destroy_node()
            raise ValueError(reason)

        self.last_pose: Optional[Pose] = None
        self.command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.pose_subscription = self.create_subscription(
            Pose,
            'turtle1/pose',
            self.pose_callback,
            10,
        )
        self.command_timer = self.create_timer(
            1.0 / self.publish_hz, self.timer_callback,
        )
        self.add_on_set_parameters_callback(self.validate_parameter_update)
        self.add_post_set_parameters_callback(self.apply_parameter_update)

    def proposed_settings(self, parameters):
        """Merge one proposal with the currently active motion settings."""
        settings = {
            'linear_speed': self.linear_speed,
            'turn_rate': self.turn_rate,
            'publish_hz': self.publish_hz,
        }
        for parameter in parameters:
            if parameter.name in settings:
                settings[parameter.name] = parameter.value
        return settings

    def validate_parameter_update(self, parameters):
        """Reject invalid proposals without touching fields or the timer."""
        reason = validate_parameters(**self.proposed_settings(parameters))
        return SetParametersResult(successful=not reason, reason=reason)

    def apply_parameter_update(self, parameters):
        """Apply a committed proposal after all validators have accepted it."""
        settings = self.proposed_settings(parameters)
        if settings['publish_hz'] != self.publish_hz:
            period = 1.0 / settings['publish_hz']
            replacement = self.create_timer(
                period, self.timer_callback, autostart=False,
            )
            self.command_timer.cancel()
            self.destroy_timer(self.command_timer)
            self.command_timer = replacement
            self.command_timer.reset()
        self.linear_speed = settings['linear_speed']
        self.turn_rate = settings['turn_rate']
        self.publish_hz = settings['publish_hz']

    def pose_callback(self, message: Pose) -> None:
        """Remember the newest pose without doing control work here."""
        self.last_pose = message

    def timer_callback(self) -> None:
        """Publish one command based on the stored pose."""
        self.command_publisher.publish(command_for_pose(
            self.last_pose, self.linear_speed, self.turn_rate,
        ))


def main(args=None) -> None:
    """Run the patrol node until ROS shuts down or the user presses Ctrl+C."""
    rclpy.init(args=args)
    node = None
    try:
        node = Patrol()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
