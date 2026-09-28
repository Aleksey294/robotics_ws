# ПР01 — исследование графа ROS 2

Дата выполнения: 29 сентября 2026 года.

Среда: нативная Ubuntu 24.04.5 LTS, ROS 2 Jazzy, RMW `rmw_fastrtps_cpp`. Для опыта использованы домены 16 и 17.

## 1. Исправный граф

Симулятор и управление были запущены в разных терминалах одного домена:

```bash
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtlesim_node
```

```bash
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtle_teleop_key
```

После нажатий стрелок координата черепахи изменилась с начальной `x=5.544445, y=5.544445` до `x=7.623413, y=5.608945`. Это подтверждает доставку команд движения.

### Ноды

Команда:

```bash
ros2 node list --no-daemon --spin-time 2
```

Вывод:

```text
/teleop_turtle
/turtlesim
```

- `/turtlesim` — симулятор: принимает команды скорости, обновляет состояние и публикует позу и цвет датчика.
- `/teleop_turtle` — клавиатурное управление: публикует команды движения для черепахи.

### Топики и типы

Команда `ros2 topic list -t` вернула:

```text
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/rosout [rcl_interfaces/msg/Log]
/turtle1/cmd_vel [geometry_msgs/msg/Twist]
/turtle1/color_sensor [turtlesim/msg/Color]
/turtle1/pose [turtlesim/msg/Pose]
```

Назначение прикладных топиков:

| Топик | Тип | Назначение |
| --- | --- | --- |
| `/turtle1/cmd_vel` | `geometry_msgs/msg/Twist` | команды линейной и угловой скорости от teleop |
| `/turtle1/pose` | `turtlesim/msg/Pose` | координаты, ориентация и текущие скорости черепахи |
| `/turtle1/color_sensor` | `turtlesim/msg/Color` | цвет фона под черепахой |

Команды и результаты проверки типа и одного сообщения:

```console
$ ros2 topic type /turtle1/pose
turtlesim/msg/Pose

$ ros2 topic echo /turtle1/pose --once
x: 7.623412609100342
y: 5.608945369720459
theta: 0.03200000151991844
linear_velocity: 0.0
angular_velocity: 0.0
---
```

`ros2 node info /turtlesim` показала подписку `/turtle1/cmd_vel` типа `geometry_msgs/msg/Twist` и публикации `/turtle1/pose` типа `turtlesim/msg/Pose`, `/turtle1/color_sensor` типа `turtlesim/msg/Color`, `/rosout` и `/parameter_events`.

### Частота позы

Команда `timeout 12s ros2 topic hz /turtle1/pose` работала 12 секунд. Последнее измерение:

```text
average rate: 62.498
    min: 0.015s max: 0.017s std dev: 0.00054s window: 631
```

Измеренная частота — примерно `62.5 Гц`, что соответствует таймеру turtlesim около 16 мс.

## 2. Разрыв связи доменами

Симулятор продолжал работать в домене 16. Teleop был остановлен сочетанием `Ctrl+C` и запущен заново в домене 17:

```bash
export ROS_DOMAIN_ID=17
ros2 run turtlesim turtle_teleop_key
```

Наблюдатель также был переведён в домен 17:

```console
$ export ROS_DOMAIN_ID=17
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle

$ timeout 5s ros2 topic echo /turtle1/pose turtlesim/msg/Pose --once \
    > evidence/pr01/pose-broken.txt 2>&1
$ printf 'exit=%s\n' "$?"
exit=124
```

За 5 секунд ни одного сообщения позы не поступило, поэтому `pose-broken.txt` пуст, а `timeout` вернул код `124`. Нода `/turtlesim`, работающая в домене 16, из домена 17 не обнаруживается. Стрелки teleop из домена 17 не перемещали черепаху.

## 3. Восстановление

Teleop снова был остановлен и запущен в исходном домене 16. Наблюдатель переведён в тот же домен:

```console
$ export ROS_DOMAIN_ID=16
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle
/turtlesim

$ timeout 5s ros2 topic echo /turtle1/pose turtlesim/msg/Pose --once \
    > evidence/pr01/pose-fixed.txt 2>&1
$ printf 'exit=%s\n' "$?"
exit=0
```

Полученная поза сохранена в `pose-fixed.txt`. Управление стрелками снова доставлялось симулятору.

## 4. Сравнение

| Состояние | Домен simulator | Домен teleop | Домен наблюдателя | Видимые ноды | Поза | Код |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| До сбоя | 16 | 16 | 16 | `/turtlesim`, `/teleop_turtle` | получена | 0 |
| Сбой | 16 | 17 | 17 | `/teleop_turtle` | не получена за 5 с | 124 |
| После исправления | 16 | 16 | 16 | `/turtlesim`, `/teleop_turtle` | получена | 0 |

## 5. Причина

`ROS_DOMAIN_ID` разделяет DDS-обнаружение и обмен сообщениями: участники разных доменов не видят друг друга. Значение переменной среды читается при создании ROS-участника, поэтому изменение `export ROS_DOMAIN_ID=...` в оболочке не перенастраивает уже работающий процесс. По этой причине teleop пришлось остановить и запустить заново. Симулятор всё время оставался в домене 16, а установка ROS 2 от номера домена не зависит, поэтому переустанавливать или перезапускать их не требовалось.
