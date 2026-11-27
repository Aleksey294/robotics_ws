# ПР06. Модель робота, tf2 и QoS преобразований

Ветка `lab_6` содержит пакет `course_description`: параметризованный
Ackermann-робот, запуск `robot_state_publisher`, конфигурацию RViz и проверки
геометрии, дерева и durability преобразований.

## Сборка и запуск

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
export ROS_DOMAIN_ID=201
xacro src/course_description/urdf/vehicle.urdf.xacro > /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
ros2 launch course_description description.launch.py
```

RViz открывается с Fixed Frame=`base_link`. У RobotModel должен быть Status: Ok.
Описание модели читается из `/robot_description` с transient local.

| Аргумент | Значение по умолчанию | Назначение |
| --- | --- | --- |
| `wheelbase` | `0.8` | Расстояние между осями, м |
| `track` | `0.62` | Колея, м |
| `wheel_radius` | `0.12` | Радиус колёс, м |
| `model` | установленный `vehicle.urdf.xacro` | Файл описания |
| `rviz` | `true` | Запуск RViz; `false` для CLI-опыта |

Размеры должны быть конечными положительными числами. Например:

```bash
ros2 launch course_description description.launch.py \
  wheelbase:=1.0 track:=0.7 wheel_radius:=0.15
```

Имена и оси: x вперёд, y влево, z вверх; углы в радианах, размеры в метрах,
массы в килограммах. У камеры есть отдельный optical frame:
z вперёд, x вправо, y вниз. Пустой `base_footprint` задаёт уровень земли,
а `base_link` расположен на высоте радиуса колеса.

Корпус, колёса и сенсоры имеют отдельные `visual`, `collision` и допустимую
инерцию. Передние кулаки поворачиваются вокруг z, колёса вращаются вокруг y.
Поворот цилиндров на 90° находится в геометрии, оси сочленений остаются
в согласованной системе координат. Плагинов Gazebo в URDF нет.

## Фиксированные и подвижные звенья

Камера, лидар, IMU и optical frame доступны сразу в `/tf_static`.
Колёса и кулаки появляются в `/tf` после получения `joint_states`.
Для отображения всех колёс можно запустить во втором терминале:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=201
ros2 topic pub -r 10 /joint_states sensor_msgs/msg/JointState \
  '{header: auto, name: [front_left_steering_joint, front_right_steering_joint, front_left_wheel_joint, front_right_wheel_joint, rear_left_wheel_joint, rear_right_wheel_joint], position: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}'
```

Это обычная публикация состояний; все преобразования по-прежнему публикует
один `robot_state_publisher`. Пакет `joint_state_publisher` не используется.

## Поздний подписчик и durability

Пока launch работает, в другом терминале выполните:

```bash
ros2 topic info /tf_static --verbose --no-daemon --spin-time 2
ros2 topic info /tf --verbose --no-daemon --spin-time 2
timeout 4 ros2 topic echo /tf_static tf2_msgs/msg/TFMessage --once \
  --qos-durability transient_local --qos-reliability reliable
timeout 4 ros2 topic echo /tf_static tf2_msgs/msg/TFMessage --once \
  --qos-durability volatile --qos-reliability reliable
```

У `/tf_static` профиль reliable/transient_local. Первый поздний подписчик
получает сохранённые фиксированные преобразования и завершается с кодом 0.
Второй совместим с издателем, но не получает историю: новых статических
публикаций нет, поэтому timeout завершается с кодом 124.
У `/tf` durability volatile: меняющиеся преобразования приходят после
новых `joint_states`.

Проверка одной связи и полного дерева:

```bash
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_tools view_frames
```

Для лидара ожидается `[0.280, 0.000, 0.380]` м относительно `base_link`.
Завершите непрерывный `tf2_echo` через Ctrl+C. `map` и `odom` здесь
не публикуются: выбор одного из них в качестве Fixed Frame даст ожидаемую
ошибку. При диагностике сначала прочитайте Global Status и статус Display,
затем проверяйте связь и дерево; offset вручную не меняйте.
Перед новым запуском остановите прежний launch.

## Проверки и воспроизведение дефекта

```bash
python3 -m pytest src/course_description/test
colcon test --packages-select course_description --event-handlers console_direct+
colcon test-result --verbose --test-result-base build/course_description
python3 .course-kit/v1/tools/check_practice.py PR06 --submission .
```

Тесты проверяют связность и отсутствие циклов, единственного parent,
положение сенсоров, единицы и размеры, ориентацию optical frame,
положительность и физическую допустимость инерции, изменение параметров
и согласованность размеров с моделью из kit.

В локальной ветке `lab_6_defect` родитель `lidar_link` заменён на
`camera_link`, offset сохранён. Дерево остаётся допустимым для `check_urdf`,
но позиция лидара становится `[0.560, 0.000, 0.760]` м.
Тест ожидаемого parent падает; с правильной связью тот же тест проходит.
Для повторения без отдельной ветки:

```bash
git worktree add --detach /tmp/pr06-parent-defect HEAD
git -C /tmp/pr06-parent-defect apply "$PWD/evidence/pr06/defect.patch"
PR06_MODEL=/tmp/pr06-parent-defect/src/course_description/urdf/vehicle.urdf.xacro \
  python3 -m pytest src/course_description/test/test_model.py::test_lidar_parent -q
ROS_DOMAIN_ID=202 python3 tools/record_pr06.py \
  --model /tmp/pr06-parent-defect/src/course_description/urdf/vehicle.urdf.xacro \
  --expect-broken --output /tmp/pr06-broken-check
python3 -m pytest src/course_description/test/test_model.py::test_lidar_parent -q
```

Полный исправный опыт с проверкой QoS, дерева и открытием RViz:

```bash
ROS_DOMAIN_ID=201 python3 tools/record_pr06.py --output /tmp/pr06-new-check --rviz
```

Сценарий ждёт обнаружения endpoints для каждого запроса CLI, явно задаёт
тип сообщения и QoS, проверяет единственного издателя tf и останавливает
свои процессы. Позднее чтение проверяется до публикации состояний колёс.
Для работы без окна опустите `--rviz`.

Материалы: [таблица фреймов](evidence/pr06/frames.md),
[проверка модели](evidence/pr06/model-check.txt),
[QoS](evidence/pr06/tf-qos.txt), [дерево tf2](evidence/pr06/frames.pdf),
[RViz](evidence/pr06/rviz.png), [отчёт](evidence/pr06/report.json).

CI выполняет сборку, тесты, live-опыт tf2 и запуск RViz в Xvfb, затем
проверяет отчёт официальным checker из зафиксированного course kit `v1-w12`.
Реализация и evidence фиксируются двумя коммитами; `report.commit`
указывает на коммит реализации.
