"""Validate motion settings without ROS or changes to active state."""

import math


def validate_parameters(linear_speed, turn_rate, publish_hz):
    """Return an error for invalid settings, or an empty string if valid."""
    limits = (
        ('linear_speed', linear_speed, 0.0, 1.0),
        ('turn_rate', turn_rate, -1.0, 1.0),
        ('publish_hz', publish_hz, 1.0, 30.0),
    )
    for name, value, lower, upper in limits:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f'{name} must be a finite number in [{lower}, {upper}]'
        if not math.isfinite(value) or not lower <= value <= upper:
            return f'{name} must be a finite number in [{lower}, {upper}]'
    return ''
