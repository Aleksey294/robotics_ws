"""Tests for the patrol command selection logic."""

from patrol.patrol import command_for_pose
from turtlesim.msg import Pose


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
