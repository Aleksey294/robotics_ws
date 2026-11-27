ROS_DOMAIN_ID=184; QT_QPA_PLATFORM=offscreen.
Source: `/home/alexai/robotics_ws`.
Commands run after sourcing ROS and install/setup.bash.

```console
$ ros2 node list --no-daemon --spin-time 1

[exit 0]
```

```console
$ ros2 run turtlesim turtlesim_node
(output saved in fixed-commands-turtlesim.txt)
[exit running]
```

```console
$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
(output saved in fixed-commands-patrol.txt)
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
average rate: 9.997
	min: 0.100s max: 0.101s std dev: 0.00040s window: 12
average rate: 9.998
	min: 0.099s max: 0.101s std dev: 0.00035s window: 22
average rate: 10.000
	min: 0.099s max: 0.101s std dev: 0.00029s window: 30
average rate: 10.000
	min: 0.099s max: 0.101s std dev: 0.00029s window: 30

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
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00055s window: 7
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00044s window: 13
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00037s window: 19
average rate: 5.000
	min: 0.199s max: 0.201s std dev: 0.00036s window: 24

(stopped after 6 s)
[exit 2]
```

```console
$ ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz must be a finite number in [1.0, 30.0]
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ ros2 topic hz /turtle1/cmd_vel --window 30
average rate: 4.998
	min: 0.200s max: 0.200s std dev: 0.00008s window: 6
average rate: 5.001
	min: 0.200s max: 0.200s std dev: 0.00014s window: 12
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00012s window: 17
average rate: 5.000
	min: 0.200s max: 0.200s std dev: 0.00012s window: 23

(stopped after 6 s)
[exit 2]
```

```console
$ ros2 param set /patrol publish_hz -1.0
Setting parameter failed: publish_hz must be a finite number in [1.0, 30.0]
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ ros2 param set /patrol publish_hz .nan
Setting parameter failed: publish_hz must be a finite number in [1.0, 30.0]
[exit 0]
```

```console
$ ros2 param get /patrol publish_hz
Double value is: 5.0
[exit 0]
```

```console
$ ros2 param set /patrol linear_speed 0.8
Set parameter successful
[exit 0]
```

```console
$ ros2 param set /patrol turn_rate -0.5
Set parameter successful
[exit 0]
```

```console
$ ros2 topic echo /turtle1/cmd_vel --once
linear:
  x: 0.8
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: -0.5
---
[exit 0]
```

```console
$ ros2 service call /clear std_srvs/srv/Empty '{}'
waiting for service to become available...
requester: making request: std_srvs.srv.Empty_Request()

response:
std_srvs.srv.Empty_Response()
[exit 0]
```

```console
$ ros2 action list -t
/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]
[exit 0]
```

All live parameter, stream, service and action checks passed.
