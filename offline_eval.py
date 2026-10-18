#!/usr/bin/env python3
"""評価用データセットで、方策の予測actionと記録actionを比較する。"""

import argparse
import numpy as np
import torch
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors

NAMES = ["swing", "boom", "arm", "bucket"]
KEYS = ["observation.state", "observation.images.cam1", "observation.images.cam2"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy_path", required=True)
    ap.add_argument("--repo_id", default="zx120_excavation_eval")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    policy = ACTPolicy.from_pretrained(args.policy_path).to(device).eval()
    pre, post = make_pre_post_processors(policy.config, pretrained_path=args.policy_path)

    ds = LeRobotDataset(args.repo_id, video_backend="pyav")
    pred, true, base = [], [], []
    last_ep = None
    for i in range(len(ds)):
        item = ds[i]
        ep = int(item["episode_index"])
        if ep != last_ep:
            policy.reset()          # エピソードの開始時にACTの行動キューを空にする
            last_ep = ep
        batch = {k: item[k].unsqueeze(0) for k in KEYS}
        batch["task"] = [item["task"]]
        with torch.inference_mode():
            a = post(policy.select_action(pre(batch)))
        pred.append(a.squeeze(0).float().cpu().numpy())
        true.append(item["action"].numpy())
        base.append(item["observation.state"].numpy())

    pred, true, base = map(np.asarray, (pred, true, base))
    mae = np.abs(pred - true).mean(axis=0)
    mae_base = np.abs(base - true).mean(axis=0)
    print(f"frames={len(true)}")
    print(f"{'joint':8s} {'方策MAE[rad]':>12s} {'基準MAE[rad]':>12s} {'改善率':>8s}")
    for n, m, b in zip(NAMES, mae, mae_base):
        print(f"{n:8s} {m:12.4f} {b:12.4f} {(1 - m / b) * 100 if b > 0 else 0:7.1f}%")
    print(f"{'mean':8s} {mae.mean():12.4f} {mae_base.mean():12.4f}")


if __name__ == "__main__":
    main()
EOF

python3 ~/opera_lerobot/offline_eval.py \
  --policy_path ~/opera_lerobot/outputs/train/act_zx120_v1/checkpoints/last/pretrained_model
