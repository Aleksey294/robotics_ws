# ПР04. Изменение параметров работающего patrol

## Реализация

Параметры `linear_speed=0.5`, `turn_rate=0.3`, `publish_hz=10.0`
объявлены как double. Диапазоны включают границы: скорость 0–1 м/с,
поворот −1–1 рад/с, частота 1–30 Гц; NaN и бесконечности запрещены.
Чистая функция `validate_parameters` не использует ROS и не меняет состояние.
Проверка выполняется в on-set, применение — в post-set после всех валидаторов.
При смене частоты новый таймер создаётся остановленным, затем прежний отменяется
и удаляется, и только после этого запускается новый с периодом `1/publish_hz`.
Подписка, сохранение последней позы и публикация `Twist` сохранены из ПР03.
До первой позы команда нулевая; для движения используется remap из ПР03.

## Повторение опыта

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
ROS_DOMAIN_ID=184 python3 tools/record_pr04.py --output /tmp/pr04-check/commands.md
```

Сценарий запускает ноды и CLI, проверяет вывод и останавливает свои процессы.
Для запуска с окном и ручного выполнения команд см. README.
Частота измеряется по сообщениям настоящего `/turtle1/cmd_vel` в течение 6 с
на каждом этапе. Код выхода 2 у `topic hz` означает завершение измерения SIGINT,
а код выхода 0 у `ros2 param set` сам по себе не означает принятие: смотрим
на `Set parameter successful` или `Setting parameter failed`.

## Дефект и тот же тест после восстановления проверки

Коммит реализации: `39e59112bf2518d9f6f9ee187d790976619a3663`.

Локальная ветка дефекта: `lab_4_defect`, коммит `1da177d4248cbc2fc2f318a55d3f742d7a00f96f`.
В ней удалена только строка ограничения `publish_hz` из чистого валидатора;
скорости продолжают проверяться. Изменение сохранено в [defect.patch](defect.patch).
В основной ветке `lab_4` эта проверка присутствует.

После перехода 10→5 Гц нулевая частота проходит on-set и записывается в ROS,
но post-set падает на `1.0 / 0.0`. Необработанное исключение завершает процесс,
и клиент параметров не получает ответ; сценарий прерывает его после выхода ноды.
Это воспроизводимый отказ, а не допустимый способ изменения частоты.
Полный traceback: [broken-commands-patrol.txt](broken-commands-patrol.txt).

Тот же тест `test_invalid_frequency_keeps_active_state[0.0]` выполнялся
с исходниками обеих версий через `PYTHONPATH`: [до](regression-before.txt)
и [после](regression-after.txt). Дефектная версия: `ZeroDivisionError`, exit 1;
исправленная: `1 passed`, exit 0. Тест проверяет прежнее значение 5.0,
идентичность таймера, период 200000000 нс, отсутствие отмены и единственный таймер.

С восстановленной проверкой CLI отклоняет 0, −1 и NaN; `get` продолжает
возвращать 5.0. Измерение после нуля подтверждает поток около 5 Гц.
Обновление скоростей подтверждено сообщением `Twist`: `linear.x=0.8`,
`angular.z=-0.5`. Полный набор: 49 тестов patrol; `colcon` для двух пакетов —
52 проверки, 0 ошибок, 0 провалов, 1 существующий пропуск copyright-теста
в `turtle_bringup`. Фактический вывод сохранён в [tests.txt](tests.txt).

## Сервис и действие — два предложения

Запрос сервиса `/clear` задаёт короткую операцию очистки и получает один ответ `Empty_Response`.
Цель действия `/turtle1/rotate_absolute` описывает длительный поворот, для которого доступны feedback, результат и отмена.

## Фактические команды и вывод исправленной версии

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

## Фактические команды и вывод версии с дефектом

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
