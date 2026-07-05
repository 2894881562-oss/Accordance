# -*- coding: utf-8 -*-
"""奇门运筹 CLI。"""

from core.qimen import analyze_qimen, format_qimen_report


def _sep(char="─", width=62):
    print(char * width)


def run_qimen_analysis(prefilled_topic=""):
    """运行传统奇门运筹分析。"""
    print()
    _sep("═")
    print("  奇门运筹分析")
    _sep("═")
    print("本功能按当前时辰生成简化九宫盘，只作方位、时机、格局运筹参考。")
    print("不实现动漫设定中的“风后奇门”拨盘改局能力。")

    topic = prefilled_topic or input("所谋之事（如谈判、竞争、出行、项目推进）：").strip()
    direction = input("当前或计划采用的方位（可选，如东、东南、西北）：").strip()
    mode = input("场景类型（可选：谈判/竞争/财务/出行/事业/学习/健康/综合）：").strip()

    result = analyze_qimen(topic=topic, direction=direction, mode=mode)
    print()
    print(format_qimen_report(result))
    _sep("═")
