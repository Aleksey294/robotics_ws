"""Exercise relative names, remapping and delivery through real DDS nodes."""

import time

from course_bringup.common import Pose
from course_bringup.pose_relay import PoseRelay
from course_bringup.pose_subscriber import PoseSubscriber
import pytest
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.serialization import serialize_message


@pytest.fixture
def context():
    ctx = Context()
    rclpy.init(context=ctx)
    yield ctx
    ctx.try_shutdown()


def test_live_relay_delivers_only_to_compatible_subscriber(context):
    source = Node('pose_source', context=context)
    relay = PoseRelay(
        context=context, namespace='/robot_test',
        cli_args=['--ros-args', '-r', 'pose:=/source_pose'],
    )
    subscribers = [
        PoseSubscriber(
            context=context, namespace='/robot_test',
            cli_args=['--ros-args', '-r', '__node:=observer_' + reliability],
            parameter_overrides=[Parameter('reliability', value=reliability)],
        )
        for reliability in ('reliable', 'best_effort')
    ]
    executor = SingleThreadedExecutor(context=context)
    nodes = [source, relay, *subscribers]
    try:
        for node in nodes:
            executor.add_node(node)
        assert relay.subscription.topic_name == '/source_pose'
        assert relay.publisher.topic_name == '/robot_test/sensor_pose'
        assert all(s.subscription.topic_name == '/robot_test/sensor_pose' for s in subscribers)
        publisher = source.create_publisher(Pose, '/source_pose', 10)
        pose = Pose(x=2.5, y=3.0, theta=-0.25, linear_velocity=0.5, angular_velocity=0.3)
        source.create_timer(0.02, lambda: publisher.publish(pose))
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline and subscribers[1].received_count < 10:
            executor.spin_once(timeout_sec=0.05)
        assert subscribers[1].received_count >= 10
        assert serialize_message(subscribers[1].last_pose) == serialize_message(pose)
        assert subscribers[0].received_count == 0
        assert subscribers[0].last_pose is None
    finally:
        executor.shutdown()
        for node in reversed(nodes):
            node.destroy_node()


def test_reliability_is_read_only_after_endpoint_creation(context):
    subscriber = PoseSubscriber(context=context)
    try:
        result = subscriber.set_parameters_atomically([
            Parameter('reliability', value='reliable'),
        ])
        assert not result.successful
        assert subscriber.get_parameter('reliability').value == 'best_effort'
    finally:
        subscriber.destroy_node()


def test_invalid_startup_reliability(context):
    with pytest.raises(ValueError, match='reliability'):
        PoseSubscriber(context=context, parameter_overrides=[
            Parameter('reliability', value='unknown'),
        ])
