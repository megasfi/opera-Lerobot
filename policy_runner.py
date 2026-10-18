#!/usr/bin/env python3
"""ZeroMQで観測を受け取り、ACTで推論したactionを送り返す。"""

import argparse
import io
import json
import time

import numpy as np
import torch
import zmq
from PIL import Image
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors


def jpeg_to_tensor(b):
    img = np.array(Image.open(io.BytesIO(b)).convert("RGB"))
    return torch.from_numpy(img).permute(2, 0, 1).float().div(255.0).unsqueeze(0)


def latest(sock, timeout_ms=1000):
    """溜まっている観測から最新のものを返す。"""
    if not sock.poll(timeout_ms):
        return None
    msg = sock.recv_multipart()
    while sock.poll(0):
        msg = sock.recv_multipart()
    return msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy_path", required=True)
    ap.add_argument("--init_repo_id", default="zx120_excavation_train")
    ap.add_argument("--init_sec", type=float, default=5.0)
    ap.add_argument("--duration", type=float, default=60.0)
    ap.add_argument("--task", default="excavate soil and dump to the right")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    policy = ACTPolicy.from_pretrained(args.policy_path).to(device).eval()
    pre, post = make_pre_post_processors(policy.config, pretrained_path=args.policy_path)

    init_pose = LeRobotDataset(args.init_repo_id, video_backend="pyav")[0]["observation.state"].tolist()
    print("init_pose:", [round(v, 3) for v in init_pose])

    ctx = zmq.Context()
    obs_sub = ctx.socket(zmq.SUB)
    obs_sub.connect("tcp://127.0.0.1:5600")
    obs_sub.setsockopt_string(zmq.SUBSCRIBE, "")
    act_pub = ctx.socket(zmq.PUB)
    act_pub.bind("tcp://127.0.0.1:5601")
    time.sleep(0.5)

    print(f"初期姿勢へ移動中（{args.init_sec}秒）")
    t0 = time.time()
    while time.time() - t0 < args.init_sec:
        act_pub.send_string(json.dumps(init_pose))
        time.sleep(0.1)

    policy.reset()
    print("方策を実行します（Ctrl+Cで停止）")
    t0 = time.time()
    n = 0
    try:
        while time.time() - t0 < args.duration:
            msg = latest(obs_sub)
            if msg is None:
                print("観測が届きません"); continue
            head = json.loads(msg[0])
            batch = {
                "observation.state": torch.tensor([head["state"]], dtype=torch.float32),
                "observation.images.cam1": jpeg_to_tensor(msg[1]),
                "observation.images.cam2": jpeg_to_tensor(msg[2]),
                "task": [args.task],
            }
            if n == 0:
                print("画像サイズ:", tuple(batch["observation.images.cam1"].shape),
                      tuple(batch["observation.images.cam2"].shape))
            with torch.inference_mode():
                a = post(policy.select_action(pre(batch))).squeeze(0).float().cpu().tolist()
            act_pub.send_string(json.dumps(a))
            n += 1
            if n % 10 == 0:
                print(f"{time.time()-t0:5.1f}s state={[round(v,2) for v in head['state']]} "
                      f"action={[round(v,2) for v in a]}")
    except KeyboardInterrupt:
        pass
    finally:
        print(f"終了: {n} 回推論")
        act_pub.close(); obs_sub.close(); ctx.term()


if __name__ == "__main__":
    main()
EOF
