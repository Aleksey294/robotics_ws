ROS_DOMAIN_ID=185; QT_QPA_PLATFORM=offscreen.
Source: `/tmp/pr04-frequency-defect`.
Commands run after sourcing ROS and install/setup.bash.

```console
$ ros2 node list --no-daemon --spin-time 1

[exit 0]
```

```console
$ ros2 run turtlesim turtlesim_node
(output saved in broken-commands-turtlesim.txt)
[exit running]
```

```console
$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
(output saved in broken-commands-patrol.txt)
[exit running]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 10.0
[exit 0]
```

```console
$ ros2 topic type /turtle1/pose
turtlesim/msg/Pose
[exit 0]
```

```console
$ ros2 topic hz /turtle1/cmd_vel --window 30
average rate: 10.001
	min: 0.100s max: 0.100s std dev: 0.00014s window: 12
average rate: 10.000
	min: 0.100s max: 0.100s std dev: 0.00013s window: 23
average rate: 10.000
	min: 0.100s max: 0.100s std dev: 0.00015s window: 30
average rate: 9.999
	min: 0.100s max: 0.100s std dev: 0.00014s window: 30

(stopped after 6 s)
[exit 2]
```

```console
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ ros2 topic hz /turtle1/cmd_vel --window 30
average rate: 4.999
	min: 0.200s max: 0.200s std dev: 0.00031s window: 6
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00024s window: 12
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00022s window: 17
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00022s window: 23

(stopped after 6 s)
[exit 2]
```

```console
$ ros2 param set /patrol publish_hz 0.0

(client interrupted after patrol exited)
[exit 2]
```

Observed: patrol exited with ZeroDivisionError.
