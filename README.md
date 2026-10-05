# ROS 2 Robotics Course — PR02

ПР02 посвящена созданию пакета `turtle_bringup`, его сборке и запуску готовой ноды `turtlesim` через launch-файл. В работе также проверяется доставка сообщения `Twist` и воспроизводится ошибка с неправильным именем топика. Проверено на Ubuntu 24.04 и ROS 2 Jazzy.

## Подготовка и сборка

Из корня репозитория подключите ROS 2 и задайте домен:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
```

Соберите пакет:

```bash
colcon build --symlink-install --packages-select turtle_bringup
source install/setup.bash
ros2 pkg prefix turtle_bringup
```

Путь пакета должен находиться внутри `install/turtle_bringup`. Сборка и команда `source` делают пакет доступным для ROS 2, но сами по себе не запускают ноду.

## Запуск симулятора

Терминал A:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 launch turtle_bringup sim.launch.py
```

В другом терминале проверьте граф:

```bash
ros2 node list --no-daemon --spin-time 2
```

Ожидается нода `/turtlesim`. После `Ctrl+C` в терминале A она должна исчезнуть.

## Проверка движения

При запущенном launch-файле получите начальную позу и отправьте одну команду:

```bash
ros2 topic echo /turtle1/pose --once
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
ros2 topic echo /turtle1/pose --once
```

Положительная линейная скорость перемещает черепаху вперёд, а положительная угловая скорость одновременно поворачивает её против часовой стрелки.

## Разрыв и восстановление

Опубликуйте тот же `Twist` в топик с неправильным полным именем:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Пока издатель работает, сравните конечные точки:

```bash
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
```

У `/cmd_vel` есть издатель, но нет подписчиков, поэтому черепаха не движется. Остановите издателя и исправьте только имя топика:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Теперь у топика есть издатель и подписчик `/turtlesim`, а движение возобновляется. Совпадение типа сообщения недостаточно: для доставки должны совпадать домен, полное имя топика, совместимые тип и QoS.

## Проверка сдачи

```bash
python3 -m py_compile src/turtle_bringup/launch/sim.launch.py
python3 -m json.tool evidence/pr02/report.json > /dev/null
test -f install/turtle_bringup/share/turtle_bringup/launch/sim.launch.py
```

Если course kit распакован в `.course-kit/`, дополнительно выполните:

```bash
python3 .course-kit/v1/tools/check_practice.py PR02 --submission .
```

Подробные команды и фактические наблюдения находятся в `evidence/pr02/commands.md`, описание сообщений — в `evidence/pr02/types.md`.
