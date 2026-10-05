"""Publish a simple velocity command after receiving a turtlesim pose."""

from typing import Optional

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


def command_for_pose(last_pose: Optional[Pose]) -> Twist:
    """Choose a velocity command from the most recently received pose."""
    command = Twist()
    if last_pose is not None:
        command.linear.x = 0.5
        command.angular.z = 0.3
    return command


class Patrol(Node):
    """Store the latest turtle pose and publish commands at 10 Hz."""

    def __init__(self) -> None:
        super().__init__('patrol')
        self.last_pose: Optional[Pose] = None
        self.command_publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.pose_subscription = self.create_subscription(
            Pose,
            '/turtle1/pose',
            self.pose_callback,
            10,
        )
        self.command_timer = self.create_timer(0.1, self.timer_callback)

    def pose_callback(self, message: Pose) -> None:
        """Remember the newest pose without doing control work here."""
        self.last_pose = message

    def timer_callback(self) -> None:
        """Publish one command based on the stored pose."""
        self.command_publisher.publish(command_for_pose(self.last_pose))


def main(args=None) -> None:
    """Run the patrol node until ROS shuts down or the user presses Ctrl+C."""
    rclpy.init(args=args)
    node = Patrol()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
