# leader_range.py : リーダーを全可動域で動かしながら各関節の min/max を計測
from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
import time

teleop = SO101Leader(SO101LeaderConfig(port="COM3", id="my_awesome_leader_arm"))  # COM番号は環境に合わせる
teleop.connect()

mins, maxs = {}, {}
print("リーダーを全ての関節について可動端まで、ゆっくり動かしてください（Ctrl+Cで終了）")
try:
    while True:
        act = teleop.get_action()
        for k, v in act.items():
            mins[k] = min(v, mins.get(k, v))
            maxs[k] = max(v, maxs.get(k, v))
        # 現在の観測範囲を上書き表示
        line = " | ".join(f"{k}:[{mins[k]:7.1f},{maxs[k]:7.1f}]" for k in act)
        print("\r" + line, end="")
        time.sleep(0.02)
except KeyboardInterrupt:
    print("\n\n=== 計測結果 ===")
    for k in mins:
        print(f"{k:18s} min={mins[k]:8.2f}  max={maxs[k]:8.2f}")
finally:
    teleop.disconnect()