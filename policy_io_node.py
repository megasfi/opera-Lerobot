#!/usr/bin/env python3
"""方策評価用の入出力ノード。観測をZeroMQで送り、受け取ったactionを/zx120/*/cmdに送る。"""

import json
import math
import time

import zmq
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import JointState, CompressedImage
from std_msgs.msg import Float64

r = math.radians
JOINTS = ["swing_joint", "boom_joint", "arm_joint", "bucket_joint"]
KEYS = ["swing", "boom", "arm", "bucket"]
LIMITS = {"swing": (r(-90), r(90)), "boom": (r(-70), r(44)),
          "arm": (r(30), r(152)), "bucket": (r(-33), r(143))}


class PolicyIO(Node):
    def __init__(self):
        super().__init__("zx120_policy_io")
        self.declare_parameter("obs_addr", "tcp://127.0.0.1:5600")
        self.declare_parameter("act_addr", "tcp://127.0.0.1:5601")
        self.declare_parameter("obs_rate_hz", 10.0)
        self.declare_parameter("max_step", 0.1)       # 50 Hzの1周期あたりの最大変化量[rad]
        self.declare_parameter("act_timeout", 0.5)    # この秒数actionが来なければ指令を止める

        self.max_step = self.get_parameter("max_step").value
        self.timeout = self.get_parameter("act_timeout").value

        self.state = None
        self.jpeg = {"cam1": None, "cam2": None}
        self.cmd = None
        self.target = None
        self.target_t = 0.0

        ctx = zmq.Context()
        self.obs_pub = ctx.socket(zmq.PUB)
        self.obs_pub.bind(self.get_parameter("obs_addr").value)
        self.act_sub = ctx.socket(zmq.SUB)
        self.act_sub.connect(self.get_parameter("act_addr").value)
        self.act_sub.setsockopt_string(zmq.SUBSCRIBE, "")

        be = QoSProfile(depth=10)
        be.reliability = ReliabilityPolicy.BEST_EFFORT
        be.history = HistoryPolicy.KEEP_LAST
        self.create_subscription(JointState, "/zx120/joint_states", self.on_js, 10)
        for cam in self.jpeg:
            self.create_subscription(CompressedImage, f"/zx120/{cam}",
                                     lambda m, c=cam: self.on_img(m, c), be)
        self.pubs = {k: self.create_publisher(Float64, f"/zx120/{k}/cmd", 10) for k in KEYS}

        self.create_timer(1.0 / self.get_parameter("obs_rate_hz").value, self.send_obs)
        self.create_timer(1.0 / 50.0, self.send_cmd)
        self.get_logger().info("policy_io ready (obs PUB 5600 / act SUB 5601)")

    def on_js(self, msg):
        pos = dict(zip(msg.name, msg.position))
        if all(j in pos for j in JOINTS):
            self.state = [float(pos[j]) for j in JOINTS]
            if self.cmd is None:
                self.cmd = list(self.state)   # 現在の姿勢から指令を始める

    def on_img(self, msg, cam):
        self.jpeg[cam] = bytes(msg.data)

    def send_obs(self):
        if self.state is None or None in self.jpeg.values():
            self.get_logger().warn("waiting observations...", throttle_duration_sec=2.0)
            return
        head = json.dumps({"t": time.time(), "state": self.state}).encode()
        self.obs_pub.send_multipart([head, self.jpeg["cam1"], self.jpeg["cam2"]])

    def send_cmd(self):
        while True:                               # 溜まっているactionから最新のものを使う
            try:
                self.target = json.loads(self.act_sub.recv_string(flags=zmq.NOBLOCK))
                self.target_t = time.monotonic()
            except zmq.Again:
                break
        if self.cmd is None or self.target is None:
            return
        if time.monotonic() - self.target_t > self.timeout:
            self.get_logger().warn("action timeout: 指令を停止", throttle_duration_sec=2.0)
            return
        for i, k in enumerate(KEYS):
            lo, hi = LIMITS[k]
            goal = min(hi, max(lo, float(self.target[i])))
            d = max(-self.max_step, min(self.max_step, goal - self.cmd[i]))
            self.cmd[i] += d
            self.pubs[k].publish(Float64(data=self.cmd[i]))


def main():
    rclpy.init()
    node = PolicyIO()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
EOF
