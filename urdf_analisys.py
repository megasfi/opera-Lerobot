"""zx120.urdf から revolute/continuous 関節と可動範囲を抽出する。"""
import xml.etree.ElementTree as ET

tree = ET.parse("C:/Users/rsakai.CMI2014/Downloads/zx120.xacro")   # ダウンロードしたファイルを指定
root = tree.getroot()

for joint in root.iter("joint"):
    jtype = joint.get("type")
    if jtype in ("revolute", "continuous", "prismatic"):
        name = joint.get("name")
        limit = joint.find("limit")
        if limit is not None:
            lo = limit.get("lower")
            hi = limit.get("upper")
        else:
            lo = hi = "None (continuous)"
        axis = joint.find("axis")
        ax = axis.get("xyz") if axis is not None else "default"
        print(f"{name:20s} type={jtype:10s} lower={lo} upper={hi} axis=({ax})")