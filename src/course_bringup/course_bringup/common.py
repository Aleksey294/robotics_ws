"""Shared pose type, explicit QoS profiles and node lifecycle."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.qos import (
    DurabilityPolicy, HistoryPolicy, LivelinessPolicy, QoSProfile, ReliabilityPolicy,
)
try:
    from turtlesim_msgs.msg import Pose
except ModuleNotFoundError:
    from turtlesim.msg import Pose


def pose_qos(reliability):
    """Build a volatile depth-10 profile with a validated reliability."""
    policies = {
        'best_effort': ReliabilityPolicy.BEST_EFFORT,
        'reliable': ReliabilityPolicy.RELIABLE,
    }
    if reliability not in policies:
        raise ValueError('reliability must be best_effort or reliable')
    return QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        reliability=policies[reliability],
        durability=DurabilityPolicy.VOLATILE,
        liveliness=LivelinessPolicy.AUTOMATIC,
    )


def run_node(factory, args=None):
    """Spin one node and release it on normal or external shutdown."""
    rclpy.init(args=args)
    node = None
    try:
        node = factory()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
