# -*- coding: utf-8 -*-
"""奇门运筹 CLI。"""

import datetime

from core.qimen import analyze_qimen, format_qimen_report
from core.qi_context import collect_focus_seed


def _sep(char="─", width=62):
    print(char * width)


def run_qimen_analysis(prefilled_topic=""):
    """运行传统奇门运筹分析。"""
    print()
    _sep("═")
    print("  奇门运筹分析")
    _sep("═")
    print("本功能按当前时辰生成简化九宫盘，并标出旬首、藏甲宫、庚方与三奇护局。")
    print("结果只作方位、时机、格局与遁甲护核的运筹参考。")
    print("不实现动漫设定中的“风后奇门”拨盘改局能力。")

    topic = prefilled_topic or input("所谋之事（如谈判、竞争、出行、项目推进）：").strip()
    direction = input("当前或计划采用的方位（可选，如东、东南、西北）：").strip()
    mode = input("场景类型（可选：谈判/竞争/财务/出行/事业/学习/健康/综合）：").strip()
    focus_info = collect_focus_seed("请静心凝神，定住所谋之事。准备好后按回车定局...")
    focus_moment = datetime.datetime.now()

    result = analyze_qimen(topic=topic, direction=direction, mode=mode, current=focus_moment)
    print()
    print(f"定局人念：{focus_info['focus_seconds']:.2f}秒")
    print(format_qimen_report(result))
    _sep("═")
