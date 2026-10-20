# opera-Lerobot
SO-101リーダーアームで、OPERA-Simを動かすためのスクリプト群です。
※OperaSim-PhysXについては　https://operasim-physx.readthedocs.io/ja/latest/install.html#ros-tcp-connector　を参照してください。

## 1.全体の構成
【Windows】SO-101 を WSL2 にアタッチ
【WSL2】コンテナ起動（start.sh）
├ シェル1：RViz + 制御系（zx120_standby）
├ シェル2：ブリッジ（so101_zx120_bridge）
【WSL2ネイティブ】シェル3：送信スクリプト（lerobot）

* それぞれのスクリプトの機能については、下表をご覧ください。

| スクリプト | 概要 |
| --- | --- |
| bridge_node.py |SO-101 リーダーアーム → zx120(Gazebo) 関節写像ブリッジ（確定版）。
| check_lerobot.py |  |
| leader_analisys.py |  |
| mapping_design.py |  |
| recorder_node.py |  |
| urdf_analisys.py |  |
|offline_eval.py|評価用データセットで、方策の予測actionと記録actionを比較する。|
| policy_io_node.py | 方策評価用の入出力ノード。観測をZeroMQで送り、受け取ったactionを/zx120/*/cmdに送る。 |
| policy_runner.py | ZeroMQで観測を受け取り、ACTで推論したactionを送り返す。 |

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
* * ※ただし７は、rvizが立ち上がるので、OperaSim-PhysXを立ち上げるときは**見出し７**へ

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

## 7.OperaSim-PhysXとSO-101の動作をつなぐ
* * ※**見出し４**で立ち上げたタブを使ってもよい。その場合はコンテナに入る必要はないので、以下の1-4の手順は不要
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. cd ~/ros2_ws/src/opera-ros2-rocker
4. sudo ./start.sh
5. source /opt/ros/humble/setup.bash
6. source ~/ros2_ws/install/setup.bash
7. ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10000

## 8.エピソードを記録する
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. cd ~/ros2_ws/src/opera-ros2-rocker
4. sudo ./enter.sh
5. source /opt/ros/humble/setup.bash
6. source ~/ros2_ws/install/setup.bash
7. python3 ~/ros2_ws/src/so101_zx120_bridge/so101_zx120_bridge/recorder_node.py

## 9.取得したエピソードをバックアップ
1. 新しいタブでコマンドプロンプトを開く
2. wsl -d Ubuntu-24.04
3. mv ~/opera_lerobot/recordings ~/opera_lerobot/recordings_old_$(date +%Y%m%d_%H%M) 2>/dev/null
4. mkdir -p ~/opera_lerobot/recordings
5. sudo docker cp pwri-opera-ros2:/root/ros2_ws/recordings/. ~/opera_lerobot/recordings/
6. sudo chown -R $USER:$USER ~/opera_lerobot/recordings

##10. 記録データをコピーして変換する。
##10-1.記録データのコピー
mv ~/opera_lerobot/recordings ~/opera_lerobot/recordings_old_$(date +%Y%m%d_%H%M) 2>/dev/null
mkdir -p ~/opera_lerobot/recordings
sudo docker cp pwri-opera-ros2:/root/ros2_ws/recordings/. ~/opera_lerobot/recordings/
sudo chown -R $USER:$USER ~/opera_lerobot/recordings

##10-2.記録データの変換
source ~/lerobot/venv/bin/activate
cd ~/opera_lerobot

### 学習用（60本）
python3 convert_to_lerobot.py --repo_id zx120_excavation_train \
  --episodes episode_00{0..8} --overwrite

### 評価用（8本）
python3 convert_to_lerobot.py --repo_id zx120_excavation_eval \
  --episodes episode_009 --overwrite

## 11. ACTを学習する

source ~/lerobot/venv/bin/activate
cd ~/opera_lerobot

lerobot-train \
  --dataset.repo_id=zx120_excavation_train \
  --dataset.video_backend=pyav \
  --policy.type=act \
  --policy.device=cuda \
  --policy.push_to_hub=false \
  --output_dir=outputs/train/act_zx120_v1 \
  --job_name=act_zx120_v1 \
  --batch_size=8 \
  --steps=20000 \
  --save_freq=5000 \
  --wandb.enable=false
