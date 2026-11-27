#!/usr/bin/env python3
"""Record URDF, live tf2 durability, geometry and optional RViz checks."""

import argparse
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time

from ament_index_python.packages import get_package_share_directory
import yaml


class Experiment:
    """Keep ROS processes isolated and save real command output."""

    def __init__(self, output, model, broken=False):
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.model = model.resolve()
        self.broken = broken
        self.env = os.environ.copy()
        self.env.setdefault('ROS_DOMAIN_ID', '201')
        self.env.setdefault('ROS_LOG_DIR', '/tmp/pr06-ros-logs')
        self.env['PYTHONUNBUFFERED'] = '1'
        self.env.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
        self.processes = []
        self.model_log = self.output / 'model-check.txt'
        self.qos_log = self.output / 'tf-qos.txt'
        self.model_log.write_text('')
        self.qos_log.write_text('')

    def record(self, log, command, output, code):
        with log.open('a') as stream:
            stream.write('$ ' + shlex.join(command) + '\n' + output.rstrip())
            stream.write(f'\n[exit {code}]\n\n')
        print(shlex.join(command), f'-> {code}', flush=True)

    def cli(self, log, command, expected=0, timeout=20):
        result = subprocess.run(
            command, env=self.env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=timeout, check=False,
        )
        self.record(log, command, result.stdout, result.returncode)
        assert result.returncode == expected, result.stdout
        return result.stdout

    def start(self, name, command):
        path = self.output / (name + '.log')
        handle = path.open('w')
        process = subprocess.Popen(
            command, env=self.env, stdout=handle, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        item = (process, handle, path, command)
        self.processes.append(item)
        self.record(self.model_log, command, '(output: ' + path.name + ')', 'running')
        return item

    def stop(self, item):
        process, handle, path, command = item
        if process.poll() is None:
            if command[:2] == ['ros2', 'launch']:
                process.send_signal(signal.SIGINT)
            else:
                os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
        handle.close()
        self.processes.remove(item)
        return path.read_text()

    def graph(self, command, ready, log):
        command = ['ros2', *command, '--no-daemon', '--spin-time', '2']
        deadline = time.monotonic() + 30
        output = ''
        while time.monotonic() < deadline:
            result = subprocess.run(
                command, env=self.env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=8, check=False,
            )
            output = result.stdout
            self.record(log, command, output, result.returncode)
            if result.returncode == 0 and ready(output):
                return output
            for process, _, path, _ in self.processes:
                assert process.poll() is None, path.read_text()
        raise AssertionError('Graph discovery timed out:\n' + output)

    def late_echo(self, durability):
        command = [
            'timeout', '4s', 'ros2', 'topic', 'echo', '/tf_static',
            'tf2_msgs/msg/TFMessage', '--once', '--no-daemon', '--spin-time', '0.1',
            '--qos-durability', durability, '--qos-reliability', 'reliable',
        ]
        for attempt in range(3 if durability == 'transient_local' else 1):
            result = subprocess.run(
                command, env=self.env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=8, check=False,
            )
            self.record(self.qos_log, command, result.stdout, result.returncode)
            if durability == 'volatile':
                assert result.returncode == 124
                assert 'child_frame_id:' not in result.stdout
                return
            if result.returncode == 0:
                data = next(yaml.safe_load_all(result.stdout))
                transforms = {t['child_frame_id']: t for t in data['transforms']}
                assert set(transforms) == {
                    'base_link', 'camera_link', 'camera_optical_frame', 'lidar_link', 'imu_link',
                }
                parent = 'camera_link' if self.broken else 'base_link'
                assert transforms['lidar_link']['header']['frame_id'] == parent
                return
            assert result.returncode == 124 and attempt < 2, result.stdout

    def screenshot(self):
        from PyQt5.QtGui import QGuiApplication, QWindow

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            result = subprocess.run(
                ['xwininfo', '-name', 'PR06-RViz'], env=self.env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            match = re.search(r'Window id:\s*(0x[0-9a-fA-F]+)', result.stdout)
            if result.returncode == 0 and match:
                break
            time.sleep(0.5)
        else:
            raise AssertionError('RViz window did not appear')
        app = QGuiApplication.instance() or QGuiApplication([])
        window = QWindow.fromWinId(int(match.group(1), 16))
        window.raise_()
        app.processEvents()
        time.sleep(3)
        pixmap = app.primaryScreen().grabWindow(int(match.group(1), 16))
        assert not pixmap.isNull()
        path = self.output / 'rviz.png'
        assert pixmap.save(str(path))
        self.record(self.model_log, ['xwininfo', '-name', 'PR06-RViz'],
                    result.stdout + '\nRViz window captured in rviz.png', result.returncode)

    def run(self, show_rviz):
        output = self.cli(self.model_log, [
            'ros2', 'node', 'list', '--no-daemon', '--spin-time', '2',
        ])
        assert not output.strip(), 'Use an unused ROS_DOMAIN_ID'
        expanded = self.output / 'vehicle.urdf'
        self.cli(self.model_log, ['xacro', str(self.model), '-o', str(expanded)])
        self.cli(self.model_log, ['check_urdf', str(expanded)])
        self.start('state-publisher', [
            'ros2', 'launch', 'course_description', 'description.launch.py',
            'rviz:=false', 'model:=' + str(self.model),
        ])
        ready = lambda text: ('Publisher count: 1' in text
                              and 'Node name: robot_state_publisher\n' in text)
        output = self.graph(['topic', 'info', '/tf_static', '--verbose'], ready, self.qos_log)
        assert 'Reliability: RELIABLE' in output and 'Durability: TRANSIENT_LOCAL' in output
        output = self.graph(['topic', 'info', '/tf', '--verbose'], ready, self.qos_log)
        assert 'Durability: VOLATILE' in output
        # The fixed transforms were published once before these late subscribers exist.
        self.late_echo('transient_local')
        self.late_echo('volatile')
        with self.qos_log.open('a') as log:
            log.write('/tf_static публикует фиксированные связи один раз с reliable/transient_local; '
                      'поздний transient_local-подписчик получает сохранённое сообщение.\n')
            log.write('Поздний volatile-подписчик совместим по QoS, но истории не получает, '
                      'поэтому без новой публикации завершается по timeout.\n')
            log.write('/tf использует volatile для меняющихся связей: новые значения приходят '
                      'после joint_states, а прошлое новому подписчику не выдаётся.\n')
        output = self.cli(self.model_log, [
            'timeout', '5s', 'ros2', 'run', 'tf2_ros', 'tf2_echo', 'base_link', 'lidar_link',
        ], expected=124, timeout=10)
        expected = '[0.560, 0.000, 0.760]' if self.broken else '[0.280, 0.000, 0.380]'
        assert 'Translation: ' + expected in output
        joints = [
            'front_left_steering_joint', 'front_right_steering_joint',
            'front_left_wheel_joint', 'front_right_wheel_joint',
            'rear_left_wheel_joint', 'rear_right_wheel_joint',
        ]
        message = '{header: auto, name: [' + ', '.join(joints) + '], position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'
        self.start('joint-states', [
            'ros2', 'topic', 'pub', '-r', '10', '/joint_states',
            'sensor_msgs/msg/JointState', message,
        ])
        output = self.cli(self.model_log, [
            'timeout', '8s', 'ros2', 'topic', 'echo', '/tf', 'tf2_msgs/msg/TFMessage',
            '--once', '--no-daemon', '--spin-time', '0.1',
            '--qos-durability', 'volatile', '--qos-reliability', 'reliable',
        ], timeout=12)
        assert 'front_left_wheel' in output and 'rear_right_wheel' in output
        self.cli(self.model_log, [
            'ros2', 'run', 'tf2_tools', 'view_frames', '--wait-time', '3',
            '--output', str(self.output / 'frames'),
        ])
        graph = (self.output / 'frames.gv').read_text()
        parent = 'camera_link' if self.broken else 'base_link'
        assert f'"{parent}" -> "lidar_link"' in graph
        assert 'front_left_wheel' in graph and 'rear_right_wheel' in graph
        if show_rviz:
            share = Path(get_package_share_directory('course_description'))
            rviz = self.start('rviz', [
                'ros2', 'run', 'rviz2', 'rviz2', '-d', str(share / 'rviz/vehicle.rviz'),
                '--display-title-format', 'PR06-RViz',
            ])
            self.screenshot()
            assert rviz[0].poll() is None, rviz[2].read_text()
        print('URDF, static durability, sensor geometry and tf tree verified.', flush=True)

    def close(self):
        for item in list(reversed(self.processes)):
            self.stop(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path, default=Path('src/course_description/urdf/vehicle.urdf.xacro'))
    parser.add_argument('--expect-broken', action='store_true')
    parser.add_argument('--rviz', action='store_true')
    args = parser.parse_args()
    experiment = Experiment(args.output, args.model, args.expect_broken)
    try:
        experiment.run(args.rviz)
    finally:
        experiment.close()


if __name__ == '__main__':
    main()
