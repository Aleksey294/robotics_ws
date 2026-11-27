#!/usr/bin/env python3
"""Verify live and replay QoS with one MCAP and save the actual CLI output."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import time

import yaml

from course_bringup.common import Pose


class Experiment:
    """Manage ROS processes and append commands and output to evidence."""

    def __init__(self, output):
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        if (self.output / 'bag').exists():
            raise ValueError('Choose a fresh --output directory; existing evidence is preserved')
        self.before = self.output / 'qos-before.txt'
        self.after = self.output / 'qos-after.txt'
        self.before.write_text('')
        self.after.write_text('')
        self.env = os.environ.copy()
        self.env.setdefault('ROS_DOMAIN_ID', '196')
        self.env.setdefault('ROS_LOG_DIR', '/tmp/pr05-ros-logs')
        self.env['QT_QPA_PLATFORM'] = 'offscreen'
        self.env['PYTHONUNBUFFERED'] = '1'
        self.processes = []

    def record(self, destination, command, output, code):
        with destination.open('a') as log:
            log.write('$ ' + shlex.join(command) + '\n')
            log.write(output.rstrip() + f'\n[exit {code}]\n\n')
        print(shlex.join(command), f'-> {code}', flush=True)

    def cli(self, destination, command, expected=0, timeout=20):
        result = subprocess.run(
            command, env=self.env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False,
        )
        self.record(destination, command, result.stdout, result.returncode)
        assert result.returncode == expected, result.stdout
        return result.stdout

    def graph_query(self, destination, arguments, ready):
        """Retry each independent CLI discovery until its own result is ready."""
        command = ['ros2', *arguments, '--no-daemon', '--spin-time', '2']
        deadline = time.monotonic() + 30
        output = ''
        while time.monotonic() < deadline:
            result = subprocess.run(
                command, env=self.env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=8, check=False,
            )
            output = result.stdout
            if destination is not None:
                self.record(destination, command, output, result.returncode)
            if result.returncode == 0 and ready(output):
                return output
            for process, _, path, _ in self.processes:
                assert process.poll() is None, path.read_text()
            time.sleep(0.2)
        raise AssertionError(shlex.join(command) + '\nGraph discovery timed out:\n' + output)

    def start(self, destination, name, command):
        path = self.output / (name + '.log')
        handle = path.open('w')
        process = subprocess.Popen(
            command, env=self.env, stdout=handle,
            stderr=subprocess.STDOUT, start_new_session=True,
        )
        item = (process, handle, path, command)
        self.processes.append(item)
        self.record(destination, command, '(output: ' + path.name + ')', 'running')
        return item

    def stop(self, item, destination):
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
        output = path.read_text()
        with destination.open('a') as log:
            log.write('--- ' + path.name + ' ---\n' + output + '\n')
        return output

    def wait_for_nodes(self, required, forbidden=(), destination=None):
        def ready(output):
            nodes = set(output.splitlines())
            return set(required) <= nodes and not set(forbidden) & nodes

        return self.graph_query(destination, ['node', 'list'], ready)

    def topic_info(self, destination, publisher, subscribers):
        """Wait for endpoints directly instead of using a warming daemon cache."""
        names = [publisher, *subscribers]
        return self.graph_query(
            destination, ['topic', 'info', '/robot_a/sensor_pose', '--verbose'],
            lambda output: ('Publisher count: 1' in output
                            and all('Node name: ' + name + '\n' in output for name in names)),
        )

    def echo(self, destination, reliability):
        command = [
            'timeout', '3s', 'ros2', 'topic', 'echo', '/robot_a/sensor_pose',
            Pose.__module__.split('.')[0] + '/msg/Pose',
            '--qos-reliability', reliability, '--once', '--no-daemon', '--spin-time', '0.1',
        ]
        expected = 124 if reliability == 'reliable' else 0
        for attempt in range(3):
            result = subprocess.run(
                command, env=self.env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=8, check=False,
            )
            output = result.stdout
            self.record(destination, command, output, result.returncode)
            if result.returncode == expected:
                break
            if expected != 0 or result.returncode != 124 or attempt == 2:
                raise AssertionError('Unexpected echo result:\n' + output)
        if expected == 124:
            assert re.search(r'^x:', output, flags=re.MULTILINE) is None
        else:
            pose = next(yaml.safe_load_all(output))
            assert {'x', 'y', 'theta', 'linear_velocity', 'angular_velocity'} <= pose.keys()

    def launch(self, destination, reliability, record):
        return self.start(destination, 'live-' + reliability, [
            'ros2', 'launch', 'course_bringup', 'patrol.launch.py',
            'namespace:=robot_a', 'subscriber_reliability:=' + reliability,
            'record:=' + str(record).lower(), 'bag_dir:=' + str(self.output / 'bag'),
        ])

    def run(self, overrides):
        bag = self.output / 'bag'
        assert not bag.exists(), 'Choose a fresh --output directory; the bag must be recorded once'
        output = self.cli(self.before, [
            'ros2', 'node', 'list', '--no-daemon', '--spin-time', '2',
        ])
        assert not output.strip(), 'Use an unused ROS_DOMAIN_ID'
        self.cli(self.before, ['ros2', 'launch', 'course_bringup', 'patrol.launch.py', '--show-args'])
        system_nodes = [
            '/turtlesim', '/robot_a/patrol', '/robot_a/pose_relay',
            '/robot_a/pose_subscriber',
        ]
        broken = self.launch(self.before, 'reliable', False)
        self.wait_for_nodes(
            system_nodes, forbidden=['/rosbag2_recorder'], destination=self.before,
        )
        assert not bag.exists(), 'record=false started a recorder'
        self.topic_info(self.before, 'pose_relay', ['pose_subscriber'])
        output = self.graph_query(
            self.before, ['topic', 'list'],
            lambda text: '/robot_a/sensor_pose' in text.splitlines(),
        )
        assert '/sensor_pose' not in output.splitlines()
        self.graph_query(
            self.before, ['node', 'info', '/robot_a/patrol'],
            lambda text: '/turtle1/pose' in text and '/turtle1/cmd_vel' in text,
        )
        self.echo(self.before, 'reliable')
        output = self.stop(broken, self.before)
        counts = re.findall(r'reliability=reliable received=(\d+)', output)
        assert counts and all(int(count) == 0 for count in counts)
        self.wait_for_nodes([], forbidden=system_nodes)

        fixed = self.launch(self.after, 'best_effort', True)
        self.wait_for_nodes([*system_nodes, '/rosbag2_recorder'], destination=self.after)
        self.topic_info(self.after, 'pose_relay', ['pose_subscriber', 'rosbag2_recorder'])
        self.echo(self.after, 'best_effort')
        # Allow the recorder to retain several seconds even on a fast runner.
        time.sleep(3)
        output = self.stop(fixed, self.after)
        counts = re.findall(r'reliability=best_effort received=(\d+)', output)
        assert counts and max(map(int, counts)) > 0
        self.wait_for_nodes([], forbidden=[*system_nodes, '/rosbag2_recorder'])

        self.cli(self.after, ['ros2', 'bag', 'info', str(bag)])
        metadata = yaml.safe_load((bag / 'metadata.yaml').read_text())['rosbag2_bagfile_information']
        assert metadata['storage_identifier'] == 'mcap'
        topics = metadata['topics_with_message_count']
        assert len(topics) == 1
        assert topics[0]['topic_metadata']['name'] == '/robot_a/sensor_pose'
        assert topics[0]['message_count'] == metadata['message_count'] > 0
        shutil.copyfile(bag / 'metadata.yaml', self.output / 'bag-metadata.yaml')
        hashes = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in bag.glob('*.mcap')
        }
        assert len(hashes) == 1
        (self.output / 'bag-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')

        # Both observers and both echo commands use this single unchanged bag.
        observers = []
        for reliability, destination in [('reliable', self.before), ('best_effort', self.after)]:
            observers.append((reliability, destination, self.start(
                destination, 'replay-' + reliability, [
                    'ros2', 'run', 'course_bringup', 'pose_subscriber', '--ros-args',
                    '-r', '__ns:=/robot_a', '-r', '__node:=replay_' + reliability,
                    '-p', 'reliability:=' + reliability,
                ],
            )))
        self.wait_for_nodes(['/robot_a/replay_reliable', '/robot_a/replay_best_effort'])
        player = self.start(self.after, 'replay-player', [
            'ros2', 'bag', 'play', str(bag), '--loop',
            '--qos-profile-overrides-path', str(overrides.resolve()),
            '--disable-keyboard-controls',
        ])
        self.wait_for_nodes(
            ['/rosbag2_player', '/robot_a/replay_reliable', '/robot_a/replay_best_effort'],
            forbidden=system_nodes, destination=self.after,
        )
        self.topic_info(self.before, 'rosbag2_player', ['replay_reliable', 'replay_best_effort'])
        self.echo(self.before, 'reliable')
        self.echo(self.after, 'best_effort')
        for reliability, destination, item in observers:
            output = self.stop(item, destination)
            counts = re.findall(r'reliability=' + reliability + r' received=(\d+)', output)
            assert counts
            if reliability == 'reliable':
                assert all(int(count) == 0 for count in counts)
            else:
                assert max(map(int, counts)) > 0
        self.stop(player, self.after)
        self.wait_for_nodes([], forbidden=[*system_nodes, '/rosbag2_player'])
        assert hashes == {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in bag.glob('*.mcap')
        }
        with self.after.open('a') as log:
            log.write('Single MCAP SHA-256 before and after replay:\n')
            log.write(json.dumps(hashes, indent=2) + '\n')
        print('Live and replay QoS verified against one unchanged MCAP.', flush=True)

    def close(self):
        for item in list(reversed(self.processes)):
            self.stop(item, self.after)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overrides', type=Path, default=Path('config/qos-overrides.yaml'))
    args = parser.parse_args()
    experiment = Experiment(args.output)
    try:
        experiment.run(args.overrides)
    finally:
        experiment.close()


if __name__ == '__main__':
    main()
