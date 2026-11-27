"""Forward turtlesim poses to a relative sensor topic using best effort."""

from course_bringup.common import Pose, pose_qos, run_node
from rclpy.node import Node


class PoseRelay(Node):
    """Subscribe to remappable pose and forward each message unchanged."""

    def __init__(self, **kwargs):
        super().__init__('pose_relay', **kwargs)
        self.publisher = self.create_publisher(Pose, 'sensor_pose', pose_qos('best_effort'))
        self.subscription = self.create_subscription(
            Pose, 'pose', self.publisher.publish, pose_qos('reliable'),
        )


def main(args=None):
    """Run the relay."""
    run_node(PoseRelay, args)


if __name__ == '__main__':
    main()
