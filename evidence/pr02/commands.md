# ПР02 — команды и наблюдения

Дата выполнения: 29 сентября 2026 года. Среда: Ubuntu 24.04.5 LTS, ROS 2 Jazzy, `ROS_DOMAIN_ID=16`.

## 1. Команды терминала

### `pwd`

Точная команда:

```bash
pwd
```

Назначение: вывести полный путь текущего каталога и убедиться, что команды выполняются из корня workspace.

Результат:

```text
/home/alexai/robotics_ws
```

### `ls -a`

Точная команда:

```bash
ls -a
```

Назначение: показать обычные и скрытые элементы каталога, включая `.git`, `.gitignore` и `.github`.

Результат: подтверждено, что текущий каталог является корнем Git-репозитория.

### `mkdir -p`

Точная команда:

```bash
mkdir -p src evidence/pr02
```

Назначение: создать вложенные каталоги, не считая ошибкой уже существующий `src`.

Результат: подготовлены каталог исходников пакета и каталог evidence ПР02.

### Операторы и окружение

`>` перенаправляет вывод команды в файл и заменяет его прежнее содержимое. Оператор `|` передаёт stdout одной команды на stdin следующей. В конструкции сборки `2>&1 | tee evidence/pr02/build.txt` stderr сначала объединяется со stdout, затем `tee` одновременно показывает поток в терминале и сохраняет его в файл.

`source /opt/ros/jazzy/setup.bash` выполняет команды setup-файла в текущей оболочке, поэтому изменённые переменные окружения остаются доступны следующим командам. Обычный запуск нового процесса не может изменить окружение родительской оболочки после завершения.

## 2. Создание и сборка пакета

Каркас создан командой:

```bash
ros2 pkg create turtle_bringup \
  --destination-directory src \
  --build-type ament_python \
  --license Apache-2.0 \
  --description 'Launch package for the turtlesim simulator.' \
  --maintainer-name 'AlexAI' \
  --maintainer-email 'zavrazin2006@mail.ru' \
  --dependencies launch launch_ros turtlesim
```

Первоначальная сборка до добавления launch-файла:

```bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup \
  2>&1 | tee evidence/pr02/build-empty.txt
```

Результат: `1 package finished`, ошибок нет. После подключения overlay:

```console
$ source install/setup.bash
$ ros2 pkg prefix turtle_bringup
/home/alexai/robotics_ws/install/turtle_bringup
```

Пакет обнаруживается в workspace, но на этой стадии никакой процесс не запускается.

После добавления `launch/sim.launch.py` и его установки через `setup.py` пакет собран повторно:

```bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup \
  2>&1 | tee evidence/pr02/build.txt
```

Результат: `1 package finished`. Проверка установленного ресурса:

```console
$ ls "$(ros2 pkg prefix turtle_bringup)/share/turtle_bringup/launch"
sim.launch.py
```

## 3. Запуск и остановка launch

Команда запуска:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 launch turtle_bringup sim.launch.py
```

Проверка графа во время работы:

```console
$ ros2 node list --no-daemon --spin-time 2
/turtlesim
```

После `Ctrl+C` launch сообщил о завершении `turtlesim_node` с кодом `0`. Повторная команда `ros2 node list --no-daemon --spin-time 2` не вывела нод. Это подтверждает, что процесс был создан launch-системой и завершился вместе с ней.

## 4. Доставка правильной команды

Начальная поза:

```yaml
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
```

Команда:

```bash
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Поза после одной публикации:

```yaml
x: 6.509308815002441
y: 5.796990871429443
theta: 0.5040000081062317
linear_velocity: 0.0
angular_velocity: 0.0
```

Координаты и угол изменились: черепаха двигалась вперёд с одновременным поворотом против часовой стрелки. После обработки единственной команды скорости снова стали нулевыми.

## 5. Ошибка в имени топика

Для воспроизведения ошибки тот же тип и те же значения отправлялись в `/cmd_vel`:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Проверка конечных точек:

```text
/cmd_vel:
  Type: geometry_msgs/msg/Twist
  Publisher count: 1
  Subscription count: 0

/turtle1/cmd_vel:
  Type: geometry_msgs/msg/Twist
  Publisher count: 0
  Subscription count: 1
  Subscriber node: /turtlesim
```

Поза во время публикации в неправильный топик осталась прежней:

```yaml
x: 6.509308815002441
y: 5.796990871429443
theta: 0.5040000081062317
linear_velocity: 0.0
angular_velocity: 0.0
```

Издатель был обнаружен, но сообщения не доставлялись `turtlesim`: правильный тип не компенсирует несовпадение полного имени топика.

## 6. Исправление

Изменено только имя `/cmd_vel` на `/turtle1/cmd_vel`; тип, значения скорости и домен оставлены прежними:

```bash
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

`ros2 topic info /turtle1/cmd_vel --verbose` показала:

```text
Type: geometry_msgs/msg/Twist
Publisher count: 1
Subscription count: 1
Publisher node: /_ros2cli_132522
Subscriber node: /turtlesim
```

Во время исправленной публикации получена поза:

```yaml
x: 6.661816120147705
y: 5.891085624694824
theta: 0.5936294198036194
linear_velocity: 1.0
angular_velocity: 0.5
```

Движение возобновилось. После остановки издателя новые команды перестали поступать, и черепаха остановилась.

## 7. До, сбой и после

| Состояние | Топик издателя | Издатели | Подписчики | Наблюдение |
| --- | --- | ---: | ---: | --- |
| До сбоя | `/turtle1/cmd_vel` | 1 | 1 | поза изменилась |
| Сбой | `/cmd_vel` | 1 | 0 | поза не изменилась |
| После исправления | `/turtle1/cmd_vel` | 1 | 1 | движение возобновилось |

Файл `src/turtle_bringup/launch/sim.launch.py` является описанием действий на диске. После сборки его копия или symlink устанавливается в `install/`, откуда `ros2 launch` может найти ресурс пакета. Запуск файла создаёт процесс с нодой `/turtlesim`. Сообщение `Twist` — отдельный объект данных, который доставляется между конечными точками графа только при совпадающих настройках связи.
