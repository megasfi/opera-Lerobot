# follower_joint: dict(leader_key, leader_min, leader_max, foll_lower, foll_upper, invert)
# foll_lower/upper は「1. の解析結果（URDF limit）」を入れる
JOINT_MAP = {
    "swing_joint":  dict(src="shoulder_pan.pos",  lmin=-100, lmax=100,
                         fmin=-3.14, fmax=3.14, invert=False),
    "boom_joint":   dict(src="shoulder_lift.pos", lmin=-100, lmax=100,
                         fmin=-0.50, fmax=1.00,  invert=False),
    "arm_joint":    dict(src="elbow_flex.pos",    lmin=-100, lmax=100,
                         fmin=-2.00, fmax=0.50,  invert=True),
    "bucket_joint": dict(src="wrist_flex.pos",    lmin=-100, lmax=100,
                         fmin=-1.00, fmax=1.00,  invert=False),
    # wrist_roll / gripper は油圧ショベルに対応関節がないため未使用
}