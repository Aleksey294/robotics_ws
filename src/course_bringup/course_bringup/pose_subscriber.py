"""Observe pose delivery using a reliability selected at startup."""

from course_bringup.common import Pose, pose_qos, run_node
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node


class PoseSubscriber(Node):
    """Count received poses and report the count once per second."""

    def __init__(self, **kwargs):
        super().__init__('pose_subscriber', **kwargs)
        self.reliability = self.declare_parameter(
            'reliability', 'best_effort',
            ParameterDescriptor(read_only=True, description='Subscription QoS at startup'),
        ).value
        try:
            qos = pose_qos(self.reliability)
        except ValueError:
            self.destroy_node()
            raise
        self.received_count = 0
        self.last_pose = None
        self.subscription = self.create_subscription(
            Pose, 'sensor_pose', self.pose_callback, qos,
        )
        self.status_timer = self.create_timer(1.0, self.report_count)

    def pose_callback(self, message):
        """Remember the message and count actual subscription callbacks."""
        self.last_pose = message
        self.received_count += 1

    def report_count(self):
        """Make delivery, including a zero count, visible in launch logs."""
        self.get_logger().info(
            f'reliability={self.reliability} received={self.received_count}',
        )


def main(args=None):
    """Run the configurable subscriber."""
    run_node(PoseSubscriber, args)


if __name__ == '__main__':
    main()
