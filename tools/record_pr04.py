#!/usr/bin/env python3
"""Record a repeatable PR04 experiment using real ROS CLI processes."""

import argparse
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess

import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect-broken', action='store_true')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault('ROS_DOMAIN_ID', '184')
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['PYTHONUNBUFFERED'] = '1'
    env['ROS_LOG_DIR'] = str(args.output.parent.resolve() / 'ros-logs')
    source_path = str(args.source.resolve() / 'src' / 'patrol')
    env['PYTHONPATH'] = source_path + os.pathsep + env.get('PYTHONPATH', '')
    processes = []
    handles = []
    transcript = []

    def record(command, output, code):
        transcript.append(
            '```console\n$ ' + shlex.join(command) + '\n'
            + output.rstrip() + f'\n[exit {code}]\n```\n'
        )
        args.output.write_text('\n'.join(transcript), encoding='utf-8')
        print(shlex.join(command), f'-> exit {code}', flush=True)

    def cli(*arguments, timeout=15):
        command = ['ros2', *arguments]
        result = subprocess.run(
            command, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=timeout, check=False,
        )
        record(command, result.stdout, result.returncode)
        assert result.returncode == 0, result.stdout
        return result.stdout

    def start(name, command):
        handle = args.output.with_name(args.output.stem + f'-{name}.txt').open('w')
        handles.append(handle)
        record(command, '(output saved in ' + Path(handle.name).name + ')', 'running')
        process = subprocess.Popen(
            command, env=env, stdout=handle, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        processes.append(process)
        return process

    def measure_rate(expected):
        command = ['ros2', 'topic', 'hz', '/turtle1/cmd_vel', '--window', '30']
        process = subprocess.Popen(
            command, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            output, _ = process.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)
            output, _ = process.communicate(timeout=5)
        record(command, output + '\n(stopped after 6 s)', process.returncode)
        rates = re.findall(r'average rate:\s*([0-9.]+)', output)
        assert rates, 'No rate measurements received'
        assert abs(float(rates[-1]) - expected) < expected * 0.2, output

    try:
        transcript.append(
            f'ROS_DOMAIN_ID={env["ROS_DOMAIN_ID"]}; QT_QPA_PLATFORM=offscreen.\n'
            'Source: `' + str(args.source.resolve()) + '`.\n'
            'Commands run after sourcing ROS and install/setup.bash.\n'
        )
        nodes = cli('node', 'list', '--no-daemon', '--spin-time', '1')
        assert not nodes.strip(), 'Use an unused ROS_DOMAIN_ID'
        start('turtlesim', ['ros2', 'run', 'turtlesim', 'turtlesim_node'])
        patrol = start('patrol', [
            'ros2', 'run', 'patrol', 'patrol', '--ros-args',
            '-r', 'cmd_vel:=/turtle1/cmd_vel',
        ])
        assert '10.0' in cli('param', 'get', '/patrol', 'publish_hz')
        assert 'Pose' in cli('topic', 'type', '/turtle1/pose')
        measure_rate(10.0)
        assert 'successful' in cli('param', 'set', '/patrol', 'publish_hz', '5.0')
        assert '5.0' in cli('param', 'get', '/patrol', 'publish_hz')
        measure_rate(5.0)

        zero = ['ros2', 'param', 'set', '/patrol', 'publish_hz', '0.0']
        if args.expect_broken:
            client = subprocess.Popen(
                zero, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                assert patrol.wait(timeout=15) != 0
            finally:
                if client.poll() is None:
                    os.killpg(client.pid, signal.SIGINT)
                output, _ = client.communicate(timeout=5)
                record(zero, output + '\n(client interrupted after patrol exited)',
                       client.returncode)
            for handle in handles:
                handle.flush()
            failure = args.output.with_name(args.output.stem + '-patrol.txt').read_text()
            assert 'ZeroDivisionError' in failure, failure
            transcript.append('Observed: patrol exited with ZeroDivisionError.\n')
        else:
            output = cli(*zero[1:])
            assert 'failed' in output and 'publish_hz' in output, output
            assert '5.0' in cli('param', 'get', '/patrol', 'publish_hz')
            measure_rate(5.0)
            for value in ('-1.0', '.nan'):
                output = cli('param', 'set', '/patrol', 'publish_hz', value)
                assert 'failed' in output and 'publish_hz' in output, output
                assert '5.0' in cli('param', 'get', '/patrol', 'publish_hz')
            assert 'successful' in cli('param', 'set', '/patrol', 'linear_speed', '0.8')
            assert 'successful' in cli('param', 'set', '/patrol', 'turn_rate', '-0.5')
            output = cli('topic', 'echo', '/turtle1/cmd_vel', '--once')
            command = next(yaml.safe_load_all(output))
            assert command['linear']['x'] == 0.8
            assert command['angular']['z'] == -0.5
            output = cli('service', 'call', '/clear', 'std_srvs/srv/Empty', '{}')
            assert 'Empty_Response' in output
            output = cli('action', 'list', '-t')
            assert '/turtle1/rotate_absolute' in output
            assert 'RotateAbsolute' in output
            assert patrol.poll() is None
            transcript.append('All live parameter, stream, service and action checks passed.\n')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=5)
        for handle in handles:
            handle.close()
        args.output.write_text('\n'.join(transcript), encoding='utf-8')


if __name__ == '__main__':
    main()
