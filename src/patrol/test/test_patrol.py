"""Tests for the patrol command selection logic."""

from patrol.patrol import command_for_pose
from patrol.patrol import Pose


def test_command_is_zero_without_pose():
    command = command_for_pose(None)

    assert command.linear.x == 0.0
    assert command.linear.y == 0.0
    assert command.linear.z == 0.0
    assert command.angular.x == 0.0
    assert command.angular.y == 0.0
    assert command.angular.z == 0.0


def test_command_moves_after_pose_arrives():
    command = command_for_pose(Pose(x=5.5, y=5.5, theta=0.0))

    assert command.linear.x == 0.5
    assert command.linear.y == 0.0
    assert command.linear.z == 0.0
    assert command.angular.x == 0.0
    assert command.angular.y == 0.0
    assert command.angular.z == 0.3


def test_command_uses_accepted_speeds():
    command = command_for_pose(Pose(), linear_speed=0.8, turn_rate=-0.5)
    assert command.linear.x == 0.8
    assert command.angular.z == -0.5


def test_nondefault_speeds_still_require_pose():
    command = command_for_pose(None, linear_speed=0.8, turn_rate=-0.5)
    assert command.linear.x == command.angular.z == 0.0
