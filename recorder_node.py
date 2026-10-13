#!/usr/bin/env python3
"""x120テレオペ記録ノード（2カメラ版）。observationとactionを一定周期で保存する。"""

import json
import os
import re
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import JointState, CompressedImage
from std_msgs.msg import Float64

STATE_JOINTS = ["swing_joint", "boom_joint", "arm_joint", "bucket_joint"]
ACTION_KEYS = ["swing", "boom", "arm", "bucket"]
CMD_TOPICS = {k: f"/zx120/{k}/cmd" for k in ACTION_KEYS}
CAMERAS = {"cam1": "/zx120/cam1", "cam2": "/zx120/cam2"}


class RecorderNode(Node):
    def __init__(self):
        super().__init__("zx120_recorder")

        self.declare_parameter("out_dir", "/root/ros2_ws/recordings")
        self.declare_parameter("episode", "")          # 空文字なら自動採番
        self.declare_parameter("rate_hz", 10.0)
        self.declare_parameter("task", "excavate soil with zx120")
        self.declare_parameter("stale_sec", 0.5)       # この秒数より古い画像をstaleと判定

        base = self.get_parameter("out_dir").value
        os.makedirs(base, exist_ok=True)
        ep = self.get_parameter("episode").value or self._next_episode(base)
        self.rate = float(self.get_parameter("rate_hz").value)
        self.task = self.get_parameter("task").value
        self.stale_sec = float(self.get_parameter("stale_sec").value)

        self.ep_dir = os.path.join(base, ep)
        if os.path.exists(self.ep_dir):
            raise RuntimeError(f"{self.ep_dir} は既に存在します。別のepisode名を指定してください。")
        for cam in CAMERAS:
            os.makedirs(os.path.join(self.ep_dir, "images", cam))

        self.jsonl = open(os.path.join(self.ep_dir, "data.jsonl"), "w")
        self.meta = {
            "episode": ep, "task": self.task, "rate_hz": self.rate,
            "state_joints": STATE_JOINTS, "action_keys": ACTION_KEYS,
            "cameras": CAMERAS, "start_time": time.time(),
        }
        self._write_meta()

        self.state = {}
        self.action = {k: None for k in ACTION_KEYS}
        self.jpeg = {c: None for c in CAMERAS}
        self.jpeg_t = {c: 0.0 for c in CAMERAS}
        # --- dup検出用
        self.jpeg_seq = {c : 0 for c in CAMERAS}    # カメラごとの受信回数
        self.last_seq = {c : -1 for c in CAMERAS}   # 前回記録した時の受信回数
        self.n_dup = 0                              # 重複画像を含むフレーム数
        self.n_dup_cam = {c : 0 for c in CAMERAS}   # カメラ別の重複回数
        # -------------
        self.frame = 0
        self.n_stale = 0
        self.closed = False

        be = QoSProfile(depth=10)
        be.reliability = ReliabilityPolicy.BEST_EFFORT
        be.history = HistoryPolicy.KEEP_LAST

        self.create_subscription(JointState, "/zx120/joint_states", self.on_js, 10)
        for cam, topic in CAMERAS.items():
            self.create_subscription(
                CompressedImage, topic, lambda m, c=cam: self.on_img(m, c), be)
        for key, topic in CMD_TOPICS.items():
            self.create_subscription(
                Float64, topic, lambda m, k=key: self.on_cmd(m, k), be)

        self.timer = self.create_timer(1.0 / self.rate, self.on_tick)
        self.get_logger().info(f"Recording to {self.ep_dir} at {self.rate} Hz")

    @staticmethod
    def _next_episode(base):
        nums = []
        for d in os.listdir(base):
            m = re.fullmatch(r"episode_(\d{3})", d)
            if m:
                nums.append(int(m.group(1)))
        return f"episode_{(max(nums) + 1) if nums else 0:03d}"

    def _write_meta(self):
        with open(os.path.join(self.ep_dir, "meta.json"), "w") as f:
            json.dump(self.meta, f, indent=2, ensure_ascii=False)

    def on_js(self, msg):
        pos = dict(zip(msg.name, msg.position))
        if all(j in pos for j in STATE_JOINTS):
            self.state = {j: float(pos[j]) for j in STATE_JOINTS}

    def on_img(self, msg, cam):
        self.jpeg[cam] = bytes(msg.data)
        self.jpeg_t[cam] = time.monotonic()
        self.jpeg_seq[cam] += 1                 #受信回数を更新

    def on_cmd(self, msg, key):
        self.action[key] = float(msg.data)

    def on_tick(self):
        missing = []
        if not self.state:
            missing.append("joint_states")
        missing += [f"cmd:{k}" for k, v in self.action.items() if v is None]
        missing += [c for c, v in self.jpeg.items() if v is None]
        if missing:
            self.get_logger().warn(f"waiting: {missing}", throttle_duration_sec=2.0)
            return

        now = time.monotonic()
        stale = [c for c in CAMERAS if now - self.jpeg_t[c] > self.stale_sec]
        if stale:
            self.n_stale += 1
            self.get_logger().warn(f"stale image: {stale}", throttle_duration_sec=2.0)

        # --- dup判定：前回の記録から新しい画像を受信していないカメラ ---
        dup = [c for c in CAMERAS if self.jpeg_seq[c] == self.last_seq[c]]
        if dup:
            self.n_dup += 1
            for c in dup:
                self.n_dup_cam[c] += 1
        self.last_seq = dict(self.jpeg_seq)
        # --- -----------------------------------------------------------

        images = {}
        for cam in CAMERAS:
            rel = os.path.join("images", cam, f"frame_{self.frame:06d}.jpg")
            with open(os.path.join(self.ep_dir, rel), "wb") as f:
                f.write(self.jpeg[cam])
            images[cam] = rel

        rec = {
            "frame": self.frame,
            "timestamp": time.time(),
            "observation.state": [self.state[j] for j in STATE_JOINTS],
            "action": [self.action[k] for k in ACTION_KEYS],
            "images": images,
            "stale": stale,
            "dup":dup,
        }
        self.jsonl.write(json.dumps(rec) + "\n")
        self.jsonl.flush()

        self.frame += 1
        if self.frame % 50 == 0:
            self.get_logger().info(
                f"frame={self.frame} ({self.frame / self.rate:.1f}s) "
                f"dup={self.n_dup / self.frame * 100:.1f}%"
                f"state={[round(v, 2) for v in rec['observation.state']]} "
                f"action={[round(v, 2) for v in rec['action']]}")

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.jsonl.close()
        dup_ratio = self.n_dup / self.frame * 100 if self.frame else 0.0
        self.meta.update({
            "end_time": time.time(),
            "num_frames": self.frame,
            "num_stale": self.n_stale,
            "num_dup": self.n_dup,
            "num_dup_per_camera": self.n_dup_cam,
            "dup_ratio_percent": round(dup_ratio,2),
        })
        self._write_meta()
        self.get_logger().info(
            f"Saved {self.frame} frames ({self.frame / self.rate:.1f}s), "
            f"stale={self.n_stale} -> {self.ep_dir}")


def main():
    rclpy.init()
    try:
        node = RecorderNode()
    except RuntimeError as e:
        print(f"[ERROR] {e}")
        rclpy.shutdown()
        return
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
