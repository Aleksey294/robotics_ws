"""Verify parameter transactions with real ROS nodes and timers."""

from patrol.patrol import Patrol
from rcl_interfaces.msg import SetParametersResult
import pytest
import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter


@pytest.fixture
def context():
    ctx = Context()
    rclpy.init(context=ctx)
    yield ctx
    ctx.try_shutdown()


@pytest.fixture
def node(context):
    patrol = Patrol(context=context)
    yield patrol
    patrol.destroy_node()


def test_frequency_replaces_one_timer(node, monkeypatch):
    old_timer = node.command_timer
    canceled = []
    original_cancel = old_timer.cancel

    def record_cancel():
        canceled.append(True)
        original_cancel()

    monkeypatch.setattr(old_timer, 'cancel', record_cancel)
    assert old_timer.timer_period_ns == 100_000_000
    result = node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])
    assert result.successful
    assert canceled == [True]
    assert node.publish_hz == node.get_parameter('publish_hz').value == 5.0
    assert node.command_timer is not old_timer
    assert node.command_timer.timer_period_ns == 200_000_000
    assert list(node.timers) == [node.command_timer]
    assert not node.command_timer.is_canceled()


@pytest.mark.parametrize('hz', [0.0, -1.0, float('nan'), float('inf'), 31.0])
def test_invalid_frequency_keeps_active_state(node, hz):
    assert node.set_parameters_atomically([
        Parameter('publish_hz', value=5.0),
    ]).successful
    old_timer = node.command_timer
    result = node.set_parameters_atomically([Parameter('publish_hz', value=hz)])
    assert not result.successful
    assert 'publish_hz' in result.reason
    assert node.publish_hz == node.get_parameter('publish_hz').value == 5.0
    assert node.command_timer is old_timer
    assert old_timer.timer_period_ns == 200_000_000
    assert not old_timer.is_canceled()
    assert list(node.timers) == [old_timer]


def test_speed_update_keeps_timer(node):
    old_timer = node.command_timer
    assert node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8),
        Parameter('turn_rate', value=-0.5),
    ]).successful
    assert node.linear_speed == 0.8
    assert node.turn_rate == -0.5
    assert node.command_timer is old_timer


def test_invalid_atomic_batch_has_no_partial_effect(node):
    old_timer = node.command_timer
    result = node.set_parameters_atomically([
        Parameter('linear_speed', value=0.8),
        Parameter('publish_hz', value=0.0),
    ])
    assert not result.successful
    assert node.linear_speed == node.get_parameter('linear_speed').value == 0.5
    assert node.publish_hz == node.get_parameter('publish_hz').value == 10.0
    assert node.command_timer is old_timer
    assert not old_timer.is_canceled()


def test_later_validator_can_reject_without_side_effects(node):
    def reject(_):
        return SetParametersResult(successful=False, reason='another validator')

    node.add_on_set_parameters_callback(reject)
    # Validators are called newest first: patrol validates, then reject vetoes.
    node.remove_on_set_parameters_callback(node.validate_parameter_update)
    node.add_on_set_parameters_callback(node.validate_parameter_update)
    old_timer = node.command_timer
    result = node.set_parameters_atomically([Parameter('publish_hz', value=5.0)])
    assert not result.successful
    assert node.publish_hz == node.get_parameter('publish_hz').value == 10.0
    assert node.command_timer is old_timer
    assert not old_timer.is_canceled()


@pytest.mark.parametrize('name, value', [
    ('linear_speed', -0.1), ('turn_rate', 1.1), ('publish_hz', 0.0),
])
def test_invalid_startup_override(context, name, value):
    with pytest.raises(ValueError, match=name):
        Patrol(context=context, parameter_overrides=[Parameter(name, value=value)])


def test_valid_startup_overrides(context):
    patrol = Patrol(context=context, parameter_overrides=[
        Parameter('linear_speed', value=0.8),
        Parameter('turn_rate', value=-0.5),
        Parameter('publish_hz', value=5.0),
    ])
    try:
        assert patrol.linear_speed == 0.8
        assert patrol.turn_rate == -0.5
        assert patrol.publish_hz == 5.0
        assert patrol.command_timer.timer_period_ns == 200_000_000
        assert list(patrol.timers) == [patrol.command_timer]
    finally:
        patrol.destroy_node()
