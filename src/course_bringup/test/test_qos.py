"""Check offered/requested QoS compatibility and accepted settings."""

from course_bringup.common import pose_qos
import pytest
from rclpy.qos import QoSCompatibility, qos_check_compatible


@pytest.mark.parametrize('publisher, subscriber, expected', [
    ('best_effort', 'reliable', QoSCompatibility.ERROR),
    ('best_effort', 'best_effort', QoSCompatibility.OK),
    ('reliable', 'best_effort', QoSCompatibility.OK),
    ('reliable', 'reliable', QoSCompatibility.OK),
])
def test_offered_and_requested_reliability(publisher, subscriber, expected):
    compatibility, _ = qos_check_compatible(pose_qos(publisher), pose_qos(subscriber))
    assert compatibility == expected


@pytest.mark.parametrize('value', ['', 'BEST_EFFORT', 'unknown'])
def test_invalid_reliability(value):
    with pytest.raises(ValueError, match='reliability'):
        pose_qos(value)
