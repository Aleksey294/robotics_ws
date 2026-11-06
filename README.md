# ROS 2 Robotics Course — PR03

ПР03 посвящена собственной Python-ноде `patrol`: подписке на позу черепахи, обработке callback и публикации команд по таймеру. В работе воспроизводится ошибка относительного имени `cmd_vel` и проверяется её исправление через remap. Среда — Ubuntu 24.04 и ROS 2 Jazzy.

## Подготовка и сборка

Из корня репозитория подключите ROS 2 и соберите оба пакета:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
ros2 pkg prefix patrol
ros2 pkg executables patrol
```

Ожидаются путь внутри `install/patrol` и исполняемый файл `patrol patrol`. Пакет `turtle_bringup` из предыдущей работы используется для запуска симулятора.

## Локальный опыт

Откройте три Bash-терминала из корня репозитория. В каждом выполните:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
```

Если выделен другой домен, используйте его во всех терминалах. Перед опытом остановите прежние экземпляры turtlesim, teleop и издателей команд скорости.

**Терминал A — симулятор:**

```bash
ros2 launch turtle_bringup sim.launch.py
```

**Терминал B — нода без remap:**

```bash
ros2 run patrol patrol
```

Нода `/patrol` подписывается на `/turtle1/pose`. Callback подписки сохраняет последнюю позу, а таймер с периодом `0.1` секунды публикует `Twist`. До получения первой позы команда нулевая; после получения позы задаются `linear.x = 0.5` и `angular.z = 0.3`.

**Терминал C — наблюдение сбоя:**

```bash
ros2 node list --no-daemon --spin-time 2
ros2 node info /patrol
ros2 topic info /turtle1/pose --verbose
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /cmd_vel --once
ros2 topic echo /turtle1/pose --once
```

В графе видны `/patrol` и `/turtlesim`. У `/turtle1/pose` есть издатель turtlesim и подписчик patrol. Относительное имя `cmd_vel` при запуске без namespace разрешается в `/cmd_vel`: у этого топика есть издатель, но нет подписчика turtlesim. Поэтому команда публикуется, а черепаха остаётся неподвижной. Повторное чтение позы подтверждает отсутствие движения.

## Исправление через remap

Остановите `patrol` в терминале B через `Ctrl+C` и запустите заново с переназначением топика:

```bash
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

В терминале C проверьте соединение и движение:

```bash
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /turtle1/cmd_vel --once
ros2 topic echo /turtle1/pose --once
ros2 topic hz /turtle1/cmd_vel --window 100
```

Теперь `/turtle1/cmd_vel` имеет издателя `/patrol` и подписчика `/turtlesim`. Черепаха движется вперёд и поворачивает против часовой стрелки. Оставьте измерение частоты работать не менее 10 секунд и завершите его через `Ctrl+C`; ожидается частота около `10 Гц`.

Остановите `patrol`, подождите около двух секунд и снова прочитайте позу:

```bash
ros2 topic echo /turtle1/pose --once
```

Скорости должны стать нулевыми после таймаута turtlesim. Нода не отправляет отдельную команду торможения при завершении. Затем остановите launch в терминале A.

## Проверка сдачи

После сборки выполните из корня репозитория:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon test --packages-select patrol --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose --test-result-base build/patrol
python3 -m json.tool evidence/pr03/report.json > /dev/null
```

Тесты проверяют нулевую команду до получения позы и команду движения после её получения. CI собирает `patrol` и `turtle_bringup`, проверяет установленные ресурсы, запускает тесты patrol и проверяет комплектность evidence ПР03.

Если course kit распакован в `.course-kit/`, дополнительно выполните:

```bash
python3 .course-kit/v1/tools/check_practice.py PR03 --submission .
```

Фактические наблюдения и объяснение работы ноды сохранены в [evidence/pr03/demo.md](evidence/pr03/demo.md), результаты проверок — в [evidence/pr03/tests.txt](evidence/pr03/tests.txt), сведения о сдаче — в [evidence/pr03/report.json](evidence/pr03/report.json). GUI-опыт выполняется локально.
