# -*- coding: utf-8 -*-
"""奇门运筹 CLI。"""

import datetime

from core.qimen import analyze_qimen, format_qimen_report
from core.qi_context import collect_focus_seed
from core.question_history import handle_duplicate_check, record_question


def _sep(char="─", width=62):
    print(char * width)


def _qimen_history_question(topic, direction, mode):
    return (
        f"奇门：{topic or '未命名事项'}｜"
        f"方位：{direction or '未指定'}｜场景：{mode or '综合'}"
    )


def _qimen_history_summary(result):
    integrated = result.get("integrated_decision", {})
    confidence = result.get("confidence_profile", {})
    primary = integrated.get("primary_direction") or "未定方位"
    final_signal = integrated.get("final_signal") or "信号未定"
    confidence_score = confidence.get("score", "未评估")
    return f"{primary}，{final_signal}，置信度{confidence_score}"


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
    history_question = _qimen_history_question(topic, direction, mode)
    should_proceed, _ = handle_duplicate_check(history_question, "奇门运筹", allow_rephrase=False)
    if not should_proceed:
        return

    focus_info = collect_focus_seed("请静心凝神，定住所谋之事。准备好后按回车定局...")
    focus_moment = datetime.datetime.now()

    result = analyze_qimen(topic=topic, direction=direction, mode=mode, current=focus_moment)
    record_question(history_question, "奇门运筹", _qimen_history_summary(result))
    print()
    print(f"定局人念：{focus_info['focus_seconds']:.2f}秒")
    print(format_qimen_report(result))
    _sep("═")
