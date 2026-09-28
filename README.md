# ROS 2 Robotics Course — PR01

ПР01 исследует граф готовых нод `turtlesim` и проверяет изоляцию через `ROS_DOMAIN_ID`. Проверено на Ubuntu 24.04 и ROS 2 Jazzy. В этой работе ROS-пакет и собственная нода не создаются.

## Локальный опыт

Откройте три Bash-терминала в одной среде. В каждом выполните:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
```

Если в аудитории выделена другая пара доменов, используйте её во всех шагах.

**Терминал A — симулятор:**

```bash
ros2 run turtlesim turtlesim_node
```

**Терминал B — управление:**

```bash
ros2 run turtlesim turtle_teleop_key
```

Нажимайте стрелки при фокусе на терминале B.

**Терминал C — наблюдение** (из корня репозитория):

```bash
mkdir -p evidence/pr01
ros2 doctor --report > evidence/pr01/doctor.txt 2>&1
ros2 node list --no-daemon --spin-time 2
ros2 topic list -t
ros2 node info /turtlesim
POSE_TYPE=$(ros2 topic type /turtle1/pose)
ros2 topic echo /turtle1/pose --once
ros2 topic hz /turtle1/pose
```

Оставьте `ros2 topic hz` работать не менее 10 секунд и завершите `Ctrl+C`. Запишите выводы в `evidence/pr01/graph.md`.

## Разрыв и восстановление

Симулятор в A остаётся в исходном домене. Остановите управление в B через `Ctrl+C`, затем запустите его в другом домене:

```bash
export ROS_DOMAIN_ID=17
ros2 run turtlesim turtle_teleop_key
```

В C, где уже задан `POSE_TYPE`, выполните:

```bash
export ROS_DOMAIN_ID=17
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-broken.txt 2>&1
printf 'exit=%s\n' "$?"
```

Ожидается только `/teleop_turtle` и `exit=124`. Пустой `pose-broken.txt` допустим: сообщений нет.

Остановите управление в B и запустите его снова после `export ROS_DOMAIN_ID=16`. В C повторите:

```bash
export ROS_DOMAIN_ID=16
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once \
  > evidence/pr01/pose-fixed.txt 2>&1
printf 'exit=%s\n' "$?"
```

Ожидаются обе ноды, сообщение позы и `exit=0`. Внесите фактические наблюдения и объяснение в `graph.md`. Изменение `ROS_DOMAIN_ID` влияет только на новые процессы, поэтому управление нужно запускать заново.

## Проверка сдачи

После распаковки course kit в `.course-kit/` выполните:

```bash
python3 -m json.tool evidence/pr01/environment.json > /dev/null
python3 .course-kit/v1/tools/check_practice.py PR01 --submission .
```

CI проверяет JSON и комплектность evidence. Поведение GUI и доставку сообщений подтверждают локальные наблюдения и демонстрация на защите.
