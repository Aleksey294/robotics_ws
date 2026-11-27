# ПР05. Launch, QoS и повтор записи

Ветка `lab_5` содержит пакет `course_bringup`: launch для `patrol`,
`pose_relay`, подписчика с выбором QoS и записи сенсорного потока в MCAP.

## Сборка

Из корня репозитория:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
export ROS_DOMAIN_ID=196
ros2 launch course_bringup patrol.launch.py --show-args
```

В каждом терминале подключите ROS, workspace и тот же свободный домен.

| Аргумент | По умолчанию | Назначение |
| --- | --- | --- |
| `namespace` | `robot_a` | Пространство имён patrol, relay и подписчика |
| `record` | `false` | При `true` запускается recorder через `IfCondition` |
| `bag_dir` | `evidence/pr05/bag` | Новый каталог MCAP |
| `subscriber_reliability` | `best_effort` | Профиль подписчика: `best_effort` или `reliable` |

Один turtlesim запускается глобально. Внутри нод имена относительные.
Launch переназначает вход patrol и relay на `/turtle1/pose`, выход patrol —
на `/turtle1/cmd_vel`. Relay пересылает позу без изменений в
`/robot_a/sensor_pose` с `best_effort`. Подписчик раз в секунду выводит
число полученных сообщений. Профиль выбирается при запуске; для его изменения
перезапустите launch с другим аргументом. Используется реальное время.

## Несовместимый QoS

В первом терминале:

```bash
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=reliable record:=false
```

Во втором:

```bash
ros2 node list --no-daemon
ros2 topic list
ros2 node info /robot_a/patrol
ros2 topic info /robot_a/sensor_pose --verbose
timeout 3s ros2 topic echo /robot_a/sensor_pose \
  --qos-reliability reliable --once
```

Топик виден, но команда завершается с кодом `124` и без сообщения позы.
В диагностике у relay указан `BEST_EFFORT`, у подписчика — `RELIABLE`;
в логе подписчика счётчик остаётся нулевым. Recorder при `record:=false`
не запускается. Причина — несовместимость запрашиваемой и предлагаемой
надёжности: best effort-издатель не обслуживает reliable-подписчика.

## Исправление и одна запись

Остановите предыдущий launch через Ctrl+C и запустите:

```bash
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=best_effort \
  record:=true bag_dir:=/tmp/pr05-my-bag
```

Выберите новый `bag_dir`: rosbag2 не перезаписывает существующий каталог.
Recorder пишет только `/robot_a/sensor_pose` в MCAP. Во втором терминале:

```bash
timeout 3s ros2 topic echo /robot_a/sensor_pose \
  --qos-reliability best_effort --once
ros2 topic info /robot_a/sensor_pose --verbose
```

Теперь приходит поза и растёт счётчик подписчика. Через несколько секунд
остановите launch через Ctrl+C: recorder завершит запись и сохранит metadata.
Все процессы launch должны завершиться; перед replay живых издателей
`sensor_pose` оставаться не должно.

## Повтор того же MCAP

В первом терминале:

```bash
ros2 bag info /tmp/pr05-my-bag
ros2 bag play /tmp/pr05-my-bag --loop \
  --qos-profile-overrides-path config/qos-overrides.yaml
```

Во втором последовательно проверьте оба профиля:

```bash
ros2 topic info /robot_a/sensor_pose --verbose
timeout 3s ros2 topic echo /robot_a/sensor_pose \
  --qos-reliability reliable --once
timeout 3s ros2 topic echo /robot_a/sensor_pose \
  --qos-reliability best_effort --once
```

Первая команда echo снова завершается по timeout, вторая получает сообщение.
Единственный издатель при replay — `rosbag2_player`; живой relay остановлен.
Оба подписчика проверяются на одной записи. `--loop` даёт время выполнить
обе команды; завершите player через Ctrl+C.

В `config/qos-overrides.yaml` задан `best_effort`, `keep_last`, глубина 10
для `/robot_a/sensor_pose`. При выборе другого namespace обновите имя топика
в override перед replay.

## Проверки и материалы сдачи

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ROS_DOMAIN_ID=195 python3 -m pytest src/patrol/test src/course_bringup/test
ROS_DOMAIN_ID=195 colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
python3 .course-kit/v1/tools/check_practice.py PR05 --submission .
```

Тесты проверяют параметры patrol, совместимость профилей, реальные callbacks DDS,
сохранение содержимого сообщения при relay, namespace и remap.

Для полного повторения опыта в свободном домене:

```bash
ROS_DOMAIN_ID=196 python3 tools/record_pr05.py --output /tmp/pr05-new-experiment
```

Сценарий запускает launch без записи и с записью, проверяет несовместимый
и исправленный профиль, сохраняет MCAP, затем повторяет оба профиля на этом же
файле. Окно turtlesim отключено через `QT_QPA_PLATFORM=offscreen`.
Существующие записи не перезаписываются. Проверяется завершение процессов
и неизменность SHA-256 MCAP после replay.

Материалы: [до исправления](evidence/pr05/qos-before.txt),
[после исправления и replay](evidence/pr05/qos-after.txt),
[metadata](evidence/pr05/bag-metadata.yaml), [MCAP](evidence/pr05/bag/bag_0.mcap),
[тесты](evidence/pr05/tests.txt), [отчёт](evidence/pr05/report.json).

CI собирает три пакета, запускает тесты, повторяет live/replay-опыт в новом
каталоге и проверяет отчёт официальным checker. Используется зафиксированный
course kit `v1-w12` с манифестом ПР05; URL и SHA-256 указаны в workflow.
Коммит реализации и следующий коммит evidence разделены; `report.commit`
указывает на реализацию.
