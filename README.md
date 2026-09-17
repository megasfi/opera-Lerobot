# opera-Lerobot
SO-101リーダーアームで、OPERA-Simを動かすためのスクリプト群です。


## 1.全体の流れ
【Windows】SO-101 を WSL2 にアタッチ
【WSL2】コンテナ起動（start.sh）
  ├ シェル1：RViz + 制御系（zx120_standby）
  ├ シェル2：ブリッジ（so101_zx120_bridge）
【WSL2ネイティブ】シェル3：送信スクリプト（lerobot）

## 2.事前準備
* コマンドプロンプトを開く
* wsl -d Ubuntu-24.04
* ls -l /dev/ttyACM0
* * ※もしls: cannot access '/dev/ttyACM0': No such file or directoryが出たら、3を実行
* * ※問題なさそうであれば4へ

## 3. 管理者権限を持つwindows power shellで、SO-101のリーダをアタッチ
1. usbipd list
2. usbipd attach --wsl --busid <BUSID>
* * <BUSID>は、usbipd list の結果を参考にしてください。

## 4. ROS launch
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. cd ~/ros2_ws/src/opera-ros2-rocker
4. sudo ./start.sh
5. source /opt/ros/humble/setup.bash
6. source ~/ros2_ws/install/setup.bash
7. ros2 launch zx120_unity zx120_standby.launch.py

## 5.LeaderからOperaにデータを渡す
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. cd ~/ros2_ws/src/opera-ros2-rocker
4. sudo ./enter.sh
5. source /opt/ros/humble/setup.bash
6. source ~/ros2_ws/install/setup.bash
7. ros2 run so101_zx120_bridge so101_to_zx120_bridge --ros-args -p max_step:=0.1

## 6.Leaderを起動する
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. source ~/lerobot/venv/bin/activate
4. python3 ~/opera_lerobot/so101_zmq_sender.py## 1.全体の流れ
【Windows】SO-101 を WSL2 にアタッチ
【WSL2】コンテナ起動（start.sh）
  ├ シェル1：RViz + 制御系（zx120_standby）
  ├ シェル2：ブリッジ（so101_zx120_bridge）
【WSL2ネイティブ】シェル3：送信スクリプト（lerobot）

## 2.事前準備
* コマンドプロンプトを開く
* wsl -d Ubuntu-24.04
* ls -l /dev/ttyACM0
* * ※もしls: cannot access '/dev/ttyACM0': No such file or directoryが出たら、3を実行
* * ※問題なさそうであれば4へ

## 3. 管理者権限を持つwindows power shellで、SO-101のリーダをアタッチ
1. usbipd list
2. usbipd attach --wsl --busid <BUSID>
* * <BUSID>は、usbipd list の結果を参考にしてください。

## 4. ROS launch
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. cd ~/ros2_ws/src/opera-ros2-rocker
4. sudo ./start.sh
5. source /opt/ros/humble/setup.bash
6. source ~/ros2_ws/install/setup.bash
7. ros2 launch zx120_unity zx120_standby.launch.py

## 5.LeaderからOperaにデータを渡す
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. cd ~/ros2_ws/src/opera-ros2-rocker
4. sudo ./enter.sh
5. source /opt/ros/humble/setup.bash
6. source ~/ros2_ws/install/setup.bash
7. ros2 run so101_zx120_bridge so101_to_zx120_bridge --ros-args -p max_step:=0.1

## 6.Leaderを起動する
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. source ~/lerobot/venv/bin/activate
4. python3 ~/opera_lerobot/so101_zmq_sender.py
