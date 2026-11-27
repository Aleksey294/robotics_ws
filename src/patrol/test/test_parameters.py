"""Exercise the pure validator, including nonfinite values and boundaries."""

from patrol.parameters import validate_parameters
import pytest


@pytest.mark.parametrize('hz', [10.0, 5.0, 1.0, 30.0])
def test_valid_frequency(hz):
    assert validate_parameters(0.5, 0.3, hz) == ''


@pytest.mark.parametrize('name, lower, upper', [
    ('linear_speed', 0.0, 1.0),
    ('turn_rate', -1.0, 1.0),
    ('publish_hz', 1.0, 30.0),
])
def test_inclusive_bounds(name, lower, upper):
    for value in (lower, upper):
        settings = dict(linear_speed=0.5, turn_rate=0.3, publish_hz=10.0)
        settings[name] = value
        assert validate_parameters(**settings) == ''


@pytest.mark.parametrize('name, value', [
    ('publish_hz', 0.0), ('publish_hz', -1.0), ('publish_hz', 30.1),
    ('linear_speed', -0.1), ('linear_speed', 1.1),
    ('turn_rate', -1.1), ('turn_rate', 1.1),
])
def test_reject_out_of_range(name, value):
    settings = dict(linear_speed=0.5, turn_rate=0.3, publish_hz=10.0)
    settings[name] = value
    assert name in validate_parameters(**settings)


@pytest.mark.parametrize('name', ['linear_speed', 'turn_rate', 'publish_hz'])
@pytest.mark.parametrize('value', [
    float('nan'), float('inf'), -float('inf'), True, '5.0', None,
])
def test_reject_nonfinite_and_nonnumeric(name, value):
    settings = dict(linear_speed=0.5, turn_rate=0.3, publish_hz=10.0)
    settings[name] = value
    assert name in validate_parameters(**settings)
