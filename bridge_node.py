#!/usr/bin/env python3
"""SO-101 リーダーアーム → zx120(Gazebo) 関節写像ブリッジ（確定版）。"""

import math
import numpy as np
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Duration

# common を外した正しい import パス
from lerobot.teleoperators.so101_leader import (
    SO101Leader, SO101LeaderConfig,
)

r = math.radians

# lmin/lmax = leader_range.py の実測値（端で詰まらないよう僅かに余裕）
# fmin/fmax = zx120.urdf の可動範囲（continuous 関節は人為設定）
JOINT_MAP = {
    "swing_joint":      dict(src="shoulder_pan.pos",  lmin=-116, lmax=117,
                             fmin=r(-90), fmax=r(90),  invert=False),
    "boom_joint":       dict(src="shoulder_lift.pos", lmin=-118, lmax=111,
                             fmin=r(-70), fmax=r(44),  invert=False),
    "arm_joint":        dict(src="elbow_flex.pos",    lmin=-98,  lmax=98,
                             fmin=r(30),  fmax=r(152), invert=False),
    "bucket_joint":     dict(src="wrist_flex.pos",    lmin=-109, lmax=111,
                             fmin=r(-33), fmax=r(143), invert=False),
    "bucket_end_joint": dict(src="wrist_roll.pos",    lmin=-160, lmax=177,
                             fmin=r(-90), fmax=r(90),  invert=False),
}


def remap(x, lmin, lmax, fmin, fmax, invert):
    """リーダー範囲[lmin,lmax] → フォロワ範囲[fmin,fmax] へ線形写像（0-1クリップ）。"""
    if lmax == lmin:
        return fmin
    t = (x - lmin) / (lmax - lmin)
    t = min(1.0, max(0.0, t))
    if invert:
        t = 1.0 - t
    return fmin + t * (fmax - fmin)


class SO101ToZx120Bridge(Node):
    def __init__(self):
        super().__init__("so101_to_zx120_bridge")

        self.declare_parameter("leader_port", "COM5")       # Windows: COM番号
        self.declare_parameter("leader_id", "my_leader")
        self.declare_parameter(
            "controller_topic",
            "/joint_trajectory_controller/joint_trajectory")
        self.declare_parameter("rate_hz", 50.0)
        self.declare_parameter("max_step", 0.05)   # 1周期あたり最大変化[rad]（安全）

        port = self.get_parameter("leader_port").value
        lid = self.get_parameter("leader_id").value
        topic = self.get_parameter("controller_topic").value
        rate = self.get_parameter("rate_hz").value
        self.max_step = self.get_parameter("max_step").value

        self.joint_names = list(JOINT_MAP.keys())
        self.cmd = np.zeros(len(self.joint_names))
        self.have_cmd = False

        self.pub = self.create_publisher(JointTrajectory, topic, 10)
        self.create_subscription(JointState, "/joint_states", self.on_js, 10)

        self.teleop = SO101Leader(SO101LeaderConfig(port=port, id=lid))
        self.teleop.connect()
        self.get_logger().info(f"SO-101 leader connected on {port}.")

        self.timer = self.create_timer(1.0 / rate, self.on_timer)

    def on_js(self, msg: JointState):
        """初回のみ現在角へ cmd を合わせ、起動時の飛び出しを防ぐ。"""
        if not self.have_cmd:
            name_to_pos = dict(zip(msg.name, msg.position))
            for i, jn in enumerate(self.joint_names):
                if jn in name_to_pos:
                    self.cmd[i] = name_to_pos[jn]
            self.have_cmd = True
            self.get_logger().info("Initialized cmd from current joint states.")

    def on_timer(self):
        if not self.have_cmd:
            return  # /joint_states 未受信のうちは送らない（安全）

        action = self.teleop.get_action()
        target = self.cmd.copy()
        for i, jn in enumerate(self.joint_names):
            m = JOINT_MAP[jn]
            if m["src"] in action:
                mapped = remap(action[m["src"]], m["lmin"], m["lmax"],
                               m["fmin"], m["fmax"], m["invert"])
                delta = mapped - self.cmd[i]
                delta = max(-self.max_step, min(self.max_step, delta))  # レート制限
                target[i] = self.cmd[i] + delta
        self.cmd = target

        traj = JointTrajectory()
        traj.joint_names = self.joint_names
        pt = JointTrajectoryPoint()
        pt.positions = [float(v) for v in self.cmd]
        pt.time_from_start = Duration(sec=0, nanosec=int(0.1 * 1e9))
        traj.points.append(pt)
        self.pub.publish(traj)

    def destroy_node(self):
        try:
            self.teleop.disconnect()
        except Exception:
            pass
        super().destroy_node()


def main():
    rclpy.init()
    node = SO101ToZx120Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()