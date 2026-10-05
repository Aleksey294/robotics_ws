# Демонстрация PR03

## Подготовка

Все терминалы используют один ROS domain:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
```

Пакет собирается и тестируется из корня workspace:

```bash
colcon build --symlink-install --packages-select patrol
source install/setup.bash
python3 -m pytest src/patrol/test
```

В терминале A запускается симулятор:

```bash
ros2 launch turtle_bringup sim.launch.py
```

## Роли частей ноды

`rclpy.init()` инициализирует клиентскую библиотеку ROS 2 для процесса. Затем
создаётся объект `Patrol`, вместе с которым создаются publisher, subscription и
timer. `rclpy.spin()` передаёт управление executor и позволяет ему вызывать
готовые callbacks. Callback подписки только сохраняет последнюю позу, а callback
таймера раз в 0,1 секунды выбирает и публикует команду.

`Ctrl+C` прерывает `spin`; блок `finally` уничтожает ноду и завершает rclpy.
Исчезновение publisher из графа не является мгновенной командой торможения:
нода не публикует нулевой `Twist` при завершении. Нужно дождаться, пока turtlesim
перестанет применять последнюю команду, и проверить нулевые скорости в позе.

## Воспроизведение разрыва

В терминале B нода запускается без remap:

```bash
ros2 run patrol patrol
```

Относительное имя `cmd_vel` разрешается как `/cmd_vel`. Проверка графа показала:

```text
/cmd_vel:         Publisher count: 1, Subscription count: 0
/turtle1/cmd_vel: Publisher count: 0, Subscription count: 1
/turtle1/pose:    Publisher count: 1, Subscription count: 1 (patrol)
```

Из `/cmd_vel` получен ожидаемый `Twist` с `linear.x: 0.5` и
`angular.z: 0.3`, но две последовательные проверки позы дали одинаковый
результат:

```text
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
```

Это подтверждает, что поза поступает в `patrol`, команда публикуется, но до
подписчика turtlesim не доходит.

## Исправление через remap

После остановки прежнего процесса в терминале B выполнено:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

Теперь `/turtle1/cmd_vel` имеет одного publisher (`patrol`) и одного subscriber
(`turtlesim`). Поза во время движения стала:

```text
x: 4.326399803161621
y: 8.352982521057129
theta: -2.327970504760742
linear_velocity: 0.5
angular_velocity: 0.30000001192092896
```

Частота измерялась около 10 секунд:

```bash
timeout --signal=INT 11s ros2 topic hz /turtle1/cmd_vel --window 100
```

Итоговое окно содержало 97 интервалов: средняя частота `9.999 Hz`, минимум
`0.099 s`, максимум `0.101 s`, стандартное отклонение `0.00023 s`.

После `Ctrl+C` у `patrol` и ожидания 2 секунд `/turtle1/pose` показал
`linear_velocity: 0.0` и `angular_velocity: 0.0`. После этого был остановлен
turtlesim.
