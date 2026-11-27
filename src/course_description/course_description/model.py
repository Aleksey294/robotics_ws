"""Expand Xacro after validating the three configurable dimensions."""

import math

import xacro


def expand_model(path, wheelbase=0.8, track=0.62, wheel_radius=0.12):
    """Return URDF text for finite, positive dimensions in metres."""
    dimensions = dict(wheelbase=wheelbase, track=track, wheel_radius=wheel_radius)
    mappings = {}
    for name, value in dimensions.items():
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError(f'{name} must be finite and positive')
        mappings[name] = str(number)
    return xacro.process_file(str(path), mappings=mappings).toxml()
