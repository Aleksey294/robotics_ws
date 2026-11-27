# ПР06. Дерево фреймов

Система правосторонняя: x вперёд, y влево, z вверх. В таблице xyz заданы
в метрах в родительской системе, rpy — в радианах. Значения приведены для
wheelbase=0.8, track=0.62, wheel_radius=0.12 и нулевых состояний сочленений.
RSP в колонке владельца означает единственную ноду `/robot_state_publisher`.

| Parent | Child | xyz | rpy / движение | Канал | Владелец |
| --- | --- | --- | --- | --- | --- |
| base_footprint | base_link | 0 0 0.12 | 0 0 0, fixed | /tf_static | RSP |
| base_link | camera_link | 0.28 0 0.38 | 0 0 0, fixed | /tf_static | RSP |
| camera_link | camera_optical_frame | 0.08 0 0 | −π/2 0 −π/2, fixed | /tf_static | RSP |
| base_link | lidar_link | 0.28 0 0.38 | 0 0 0, fixed | /tf_static | RSP |
| base_link | imu_link | 0.28 0 0.38 | 0 0 0, fixed | /tf_static | RSP |
| base_link | front_left_knuckle | 0.4 0.31 0 | поворот вокруг z, ±0.55 | /tf | RSP |
| base_link | front_right_knuckle | 0.4 −0.31 0 | поворот вокруг z, ±0.55 | /tf | RSP |
| front_left_knuckle | front_left_wheel | 0 0 0 | вращение вокруг y | /tf | RSP |
| front_right_knuckle | front_right_wheel | 0 0 0 | вращение вокруг y | /tf | RSP |
| base_link | rear_left_wheel | −0.4 0.31 0 | вращение вокруг y | /tf | RSP |
| base_link | rear_right_wheel | −0.4 −0.31 0 | вращение вокруг y | /tf | RSP |

В optical frame z направлена вперёд, x вправо, y вниз. База отсчитывается
между осями; колея — между центрами левого и правого колеса. Корень
`base_footprint` находится на уровне земли, `base_link` — на высоте осей колёс.
Рамки трёх сенсоров имеют общую точку крепления; простые visual/collision
геометрии модулей смещены внутри звеньев и не меняют эти преобразования.

## Владельцы и обновления

В [tf-qos.txt](tf-qos.txt) у `/tf` и `/tf_static` ровно один publisher:
`robot_state_publisher`. CLI-публикатор `/joint_states` передаёт только
шесть положений сочленений и не публикует tf. Он запущен после опыта
с поздними подписчиками, чтобы показать колёса и полное дерево в RViz.
`map` и `odom` в этой работе отсутствуют.

Фиксированные связи появляются сразу, подвижные — после `joint_states`.
Для динамических состояний используется `header: auto`, а в выводе
`view_frames` сохранены времена буфера. Начальное сообщение Waiting for
transform до завершения discovery сменяется устойчивым правильным ответом.

## Доказательство до и после

Минимальный запуск корпуса и лидара: [команды и tf2_echo](minimal.txt),
[развёрнутый URDF](minimal.urdf). Полная модель содержит 12 звеньев и
11 сочленений, одно дерево без циклов и без повторных родителей.

Коммит реализации: `19c9b472c1f74c9d77c73b37dd5e153e34e31c04`.

Дефект сохранён в локальной ветке `lab_6_defect`, коммит `166efc9dac2de50aff02e4bafb8b1384e49af4f0`.
Изменён только parent `lidar_joint`: `base_link` → `camera_link`,
прежний offset `0.28 0 0.38` оставлен. Из-за сложения двух смещений
лидар оказывается в `0.56 0 0.76` относительно `base_link`.
`check_urdf` принимает обе модели: дерево остаётся связным и ацикличным.

| Проверка | Дефект | Исправленная модель |
| --- | --- | --- |
| check_urdf | exit 0 | exit 0 |
| tf2_echo base_link lidar_link | [0.560, 0.000, 0.760] | [0.280, 0.000, 0.380] |
| test_lidar_parent | 1 failed, exit 1 | 1 passed, exit 0 |
| parent lidar_link | camera_link | base_link |

Фактический вывод: [дефектная модель](defect/model-check.txt),
[исправленная модель](model-check.txt), [тест до](regression-before.txt),
[тот же тест после](regression-after.txt). Патч: [defect.patch](defect.patch).
Графы `view_frames`: [до](defect/frames.pdf), [после](frames.pdf).

## RViz и QoS

В [снимке RViz](rviz.png) Fixed Frame=`base_link`, Global Status и
RobotModel — Ok. Модель отображается с корпусом, колёсами и сенсорами.
Перед снимком опубликованы нулевые состояния всех шести подвижных суставов.

Позднее чтение `/tf_static` выполнено до публикации `/joint_states`:
reliable/transient_local получает сохранённые 5 фиксированных преобразований,
reliable/volatile не получает старый пакет и завершается с exit 124.
Профили и два-три предложения о различии каналов сохранены в
[tf-qos.txt](tf-qos.txt). Для обоих опытов использован один RSP на домен;
после проверки процессы завершены.
