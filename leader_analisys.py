from lerobot.teleoperators.so_leader import (
    SO101Leader, SO101LeaderConfig,
)

teleop = SO101Leader(SO101LeaderConfig(port="com3", id="my_awesome_leader_arm"))
teleop.connect()
print(teleop.get_action())
# 例: {'shoulder_pan.pos': .., 'shoulder_lift.pos': .., 'elbow_flex.pos': ..,
#      'wrist_flex.pos': .., 'wrist_roll.pos': .., 'gripper.pos': ..}