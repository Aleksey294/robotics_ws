# ROS 2 Robotics Course — ПР04

Ветка `lab_4` продолжает `patrol` из ПР03: подписка сохраняет последнюю позу,
а один таймер публикует `Twist`. Параметры работающей ноды задают скорость,
поворот и частоту публикации. Среда проверки — Ubuntu 24.04, ROS 2 Jazzy.

| Параметр | По умолчанию | Допустимые конечные значения |
| --- | --- | --- |
| `linear_speed` | `0.5` м/с | `[0, 1]` |
| `turn_rate` | `0.3` рад/с | `[-1, 1]` |
| `publish_hz` | `10.0` Гц | `[1, 30]` |

Все три ROS-параметра имеют тип `double`: в CLI используйте `5.0`, а не `5`.
NaN и бесконечности отклоняются. До первой позы публикуется нулевая команда.

## Сборка и запуск

Из корня репозитория:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
export ROS_DOMAIN_ID=184
```

Подключите ROS, workspace и одинаковый свободный домен в каждом терминале.
В первом запустите симулятор, во втором — ноду с remap из ПР03:

```bash
ros2 launch turtle_bringup sim.launch.py
```

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В третьем терминале:

```bash
ros2 topic type /turtle1/pose
ros2 param list /patrol
ros2 param get /patrol publish_hz
ros2 topic hz /turtle1/cmd_vel --window 30
# Завершите измерение Ctrl+C через 6 секунд: около 10 Гц.
ros2 param set /patrol publish_hz 5.0
ros2 topic hz /turtle1/cmd_vel --window 30
# Около 5 Гц; завершите измерение Ctrl+C.
ros2 param set /patrol publish_hz 0.0
ros2 param get /patrol publish_hz
ros2 topic hz /turtle1/cmd_vel --window 30
# Ноль отклонён, параметр 5.0, поток около 5 Гц.
ros2 param set /patrol publish_hz -1.0
ros2 param set /patrol publish_hz .nan
ros2 param set /patrol linear_speed 0.8
ros2 param set /patrol turn_rate -0.5
ros2 topic echo /turtle1/cmd_vel --once
ros2 service call /clear std_srvs/srv/Empty '{}'
ros2 action list -t
```

В Jazzy тип позы — `turtlesim/msg/Pose`; код также поддерживает импорт
`turtlesim_msgs/msg/Pose` для дистрибутивов с выделенным пакетом интерфейсов.
Зависимость `turtlesim` в `package.xml` соответствует проверенному Jazzy.

## Как применяются параметры

Чистая функция в `patrol/parameters.py` проверяет все предложенные значения.
`on_set` выполняет только проверку: отказ любого валидатора оставляет параметры,
активные поля и таймер прежними. После успешного принятия `post_set` применяет
настройки. При смене частоты создаётся остановленный таймер с периодом `1/hz`,
старый отменяется и удаляется, затем новый запускается. Два активных таймера
одновременно не работают; изменение только скоростей таймер не заменяет.
Начальные переопределения тоже проверяются до создания таймера.

Для единого принятия нескольких параметров используйте сервис
`/patrol/set_parameters_atomically`: обычный `set_parameters` обрабатывает их
по одному. Нода работает с обычным однопоточным executor.

## Проверки и воспроизведение дефекта

```bash
python3 -m pytest src/patrol/test
colcon test --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
```

Сценарий ниже сам запускает настоящие turtlesim и patrol в свободном домене,
выполняет команды CLI, проверяет частоту и сохраняет фактический вывод.
`QT_QPA_PLATFORM=offscreen` позволяет обойтись без окна при автоматической проверке.

```bash
ROS_DOMAIN_ID=184 python3 tools/record_pr04.py --output /tmp/pr04-check/commands.md
```

В отдельной локальной ветке `lab_4_defect` сохранён коммит с отключённой проверкой
`publish_hz`. Ноль проходит проверку, затем вычисление периода вызывает
`ZeroDivisionError` и процесс завершается. В основной ветке восстановлена проверка.
SHA дефекта и его патч находятся в `evidence/pr04/`; патч позволяет повторить опыт
даже без опубликованной ветки дефекта:

```bash
git worktree add --detach /tmp/pr04-defect HEAD
git -C /tmp/pr04-defect apply "$PWD/evidence/pr04/defect.patch"
PYTHONPATH=/tmp/pr04-defect/src/patrol python3 -m pytest \
  'src/patrol/test/test_node_parameters.py::test_invalid_frequency_keeps_active_state[0.0]' -q
ROS_DOMAIN_ID=185 python3 tools/record_pr04.py --source /tmp/pr04-defect \
  --expect-broken --output /tmp/pr04-defect-check/commands.md
# Версия с проверкой: тот же регрессионный тест проходит.
python3 -m pytest \
  'src/patrol/test/test_node_parameters.py::test_invalid_frequency_keeps_active_state[0.0]' -q
```

Для официального checker скачайте зафиксированный комплект:

```bash
mkdir -p .course-kit
curl -fsS https://ros.lms.ci.nsu.ru/downloads/robotics-course-kit-v1-w12-525e86f818ff.tar.gz \
  -o /tmp/pr04-course-kit.tar.gz
printf '%s\n' '525e86f818ffed166e7f7b67cc87fdd3f3ea840d13aa90e76bde9fda0f3c9c5a  /tmp/pr04-course-kit.tar.gz' | sha256sum -c -
tar -xzf /tmp/pr04-course-kit.tar.gz -C .course-kit
python3 .course-kit/v1/tools/check_practice.py PR04 --submission .
```

Course kit `v1-w12` — текущая накопительная ревизия при выполнении работы;
она содержит официальный манифест ПР04. CI использует тот же URL и SHA-256,
собирает пакеты, выполняет тесты и реальный опыт, затем запускает checker.

Результаты: [параметры и объяснение](evidence/pr04/parameters.md),
[вывод проверок](evidence/pr04/tests.txt), [отчёт](evidence/pr04/report.json).
`report.commit` указывает на коммит реализации; evidence и `AI_USAGE.md`
добавлены следующим коммитом по [runbook курса](https://ros.lms.ci.nsu.ru/practices/runbook#two-commits).
