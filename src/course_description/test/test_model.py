"""Check model topology, semantic sensor placement and physical dimensions."""

import math
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from course_description.model import expand_model
import numpy as np
import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODEL = Path(os.environ.get('PR06_MODEL', PACKAGE / 'urdf/vehicle.urdf.xacro'))


@pytest.fixture(scope='module')
def robot():
    return ET.fromstring(expand_model(MODEL))


def vector(element, attribute, default='0 0 0'):
    return np.array([float(v) for v in element.get(attribute, default).split()])


def origin_matrix(joint):
    origin = joint.find('origin')
    roll, pitch, yaw = vector(origin, 'rpy')
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    result = np.eye(4)
    result[:3, :3] = np.array([
        [cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
        [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
        [-sp, cp*sr, cp*cr],
    ])
    result[:3, 3] = vector(origin, 'xyz')
    return result


def pose_in_base(robot, child):
    joints = {j.find('child').get('link'): j for j in robot.findall('joint')}
    result = np.eye(4)
    while child != 'base_link':
        joint = joints[child]
        result = origin_matrix(joint) @ result
        child = joint.find('parent').get('link')
    return result


def test_connected_acyclic_single_parent_tree(robot):
    links = [link.get('name') for link in robot.findall('link')]
    assert len(links) == len(set(links)) == 12
    joints = robot.findall('joint')
    children = [joint.find('child').get('link') for joint in joints]
    assert len(children) == len(set(children)) == len(links) - 1
    assert set(links) - set(children) == {'base_footprint'}
    parents = {j.find('child').get('link'): j.find('parent').get('link') for j in joints}
    for child in children:
        visited = set()
        while child in parents:
            assert child not in visited
            visited.add(child)
            child = parents[child]
        assert child == 'base_footprint'
    assert not robot.findall('.//plugin')
    assert not robot.findall('.//gazebo')


def test_lidar_parent(robot):
    joint = robot.find("joint[@name='lidar_joint']")
    assert joint.find('parent').get('link') == 'base_link'
    assert joint.find('child').get('link') == 'lidar_link'
    assert joint.get('type') == 'fixed'


@pytest.mark.parametrize('sensor', ['camera_link', 'lidar_link', 'imu_link'])
def test_sensor_pose_in_base(robot, sensor):
    transform = pose_in_base(robot, sensor)
    assert transform[:3, 3] == pytest.approx([0.28, 0.0, 0.38])
    assert transform[:3, :3] == pytest.approx(np.eye(3))


def test_optical_axes_follow_rep103(robot):
    optical = origin_matrix(robot.find("joint[@name='camera_optical_joint']"))
    assert optical[:3, :3] @ [0, 0, 1] == pytest.approx([1, 0, 0])
    assert optical[:3, :3] @ [1, 0, 0] == pytest.approx([0, -1, 0])
    assert optical[:3, :3] @ [0, 1, 0] == pytest.approx([0, 0, -1])


def test_physical_links_have_visual_collision_and_valid_inertia(robot):
    for link in robot.findall('link'):
        if link.get('name') in ('base_footprint', 'camera_optical_frame'):
            continue
        assert link.find('visual/geometry') is not None
        assert link.find('collision/geometry') is not None
        assert float(link.find('inertial/mass').get('value')) > 0
        inertia = link.find('inertial/inertia')
        values = {key: float(value) for key, value in inertia.attrib.items()}
        matrix = np.array([
            [values['ixx'], values['ixy'], values['ixz']],
            [values['ixy'], values['iyy'], values['iyz']],
            [values['ixz'], values['iyz'], values['izz']],
        ])
        moments = np.linalg.eigvalsh(matrix)
        assert np.isfinite(moments).all() and (moments > 0).all()
        assert moments[-1] <= moments[0] + moments[1] + 1e-12


def test_all_geometry_numbers_are_finite_and_dimensions_positive(robot):
    numeric = {'xyz', 'rpy', 'size', 'radius', 'length', 'rgba', 'value',
               'ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz', 'lower', 'upper', 'effort', 'velocity'}
    for element in robot.iter():
        for key, text in element.attrib.items():
            if key in numeric:
                assert all(math.isfinite(float(v)) for v in text.split())
        if element.tag in ('box', 'cylinder'):
            assert all(float(v) > 0 for text in element.attrib.values() for v in text.split())


@pytest.mark.parametrize('wheelbase, track, radius', [(0.8, 0.62, 0.12), (1.0, 0.7, 0.15)])
def test_dimensions_reposition_both_axles_and_resize_wheels(wheelbase, track, radius):
    robot = ET.fromstring(expand_model(MODEL, wheelbase, track, radius))
    for side, sign in [('left', 1), ('right', -1)]:
        steering = robot.find(f"joint[@name='front_{side}_steering_joint']")
        assert vector(steering.find('origin'), 'xyz') == pytest.approx([wheelbase/2, sign*track/2, 0])
        assert vector(steering.find('axis'), 'xyz') == pytest.approx([0, 0, 1])
        for axle, x in [('front', wheelbase/2), ('rear', -wheelbase/2)]:
            name = f'{axle}_{side}_wheel'
            joint = robot.find(f"joint[@name='{name}_joint']")
            assert joint.get('type') == 'continuous'
            assert vector(joint.find('axis'), 'xyz') == pytest.approx([0, 1, 0])
            assert pose_in_base(robot, name)[:3, 3] == pytest.approx([x, sign*track/2, 0])
            for geometry in ['visual', 'collision']:
                cylinder = robot.find(f"link[@name='{name}']/{geometry}/geometry/cylinder")
                assert float(cylinder.get('radius')) == pytest.approx(radius)
    footprint = robot.find("joint[@name='base_joint']/origin")
    assert vector(footprint, 'xyz') == pytest.approx([0, 0, radius])


@pytest.mark.parametrize('name', ['wheelbase', 'track', 'wheel_radius'])
@pytest.mark.parametrize('value', [0, -0.1, float('nan'), float('inf')])
def test_invalid_launch_dimensions_are_rejected(name, value):
    with pytest.raises(ValueError, match=name):
        expand_model(MODEL, **{name: value})


def test_default_dimensions_match_course_kit(robot):
    path = PACKAGE.parents[1] / '.course-kit/v1/models/course_ackermann/model.sdf'
    assert path.is_file(), 'Download the pinned course kit before running model tests'
    source = ET.parse(path).getroot().find('model')
    for name in ['front_left_wheel', 'front_right_wheel', 'rear_left_wheel', 'rear_right_wheel']:
        expected = [float(v) for v in source.find(f"link[@name='{name}']/pose").text.split()[:3]]
        assert pose_in_base(robot, name)[:3, 3] == pytest.approx(expected)
        source_radius = float(source.find(f"link[@name='{name}']/collision/geometry/cylinder/radius").text)
        actual = robot.find(f"link[@name='{name}']/collision/geometry/cylinder")
        assert float(actual.get('radius')) == source_radius
        assert float(actual.get('length')) == float(source.find(f"link[@name='{name}']/collision/geometry/cylinder/length").text)
    body = robot.find("link[@name='base_link']/collision/geometry/box")
    expected = source.find("link[@name='base_link']/collision/geometry/box/size").text
    assert [float(v) for v in body.get('size').split()] == [float(v) for v in expected.split()]


def test_check_urdf_accepts_expanded_description(tmp_path):
    path = tmp_path / 'vehicle.urdf'
    path.write_text(expand_model(MODEL))
    result = subprocess.run(['check_urdf', str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
