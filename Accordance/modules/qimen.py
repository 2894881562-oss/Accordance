# -*- coding: utf-8 -*-
"""奇门运筹 CLI。"""

import datetime

from core.cli_input import ask_choice, ask_text, present_conclusion
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


def _plain_qimen_conclusion(result):
    """压缩奇门首屏结论，完整依据留在详细报告。"""
    decision = result.get("integrated_decision", {})
    confidence = result.get("confidence_profile", {})
    guardrails = result.get("execution_guardrails", {})
    signal = decision.get("final_signal") or "信号未定"
    primary = decision.get("primary_direction") or "待定方位"
    priority = decision.get("priority") or "先核信息"
    guard_mode = guardrails.get("mode") or "小步验证"
    score = confidence.get("score", "未评估")
    level = confidence.get("level") or "待校准"
    return (
        f"{signal}：主位优先{primary}，策略为{priority}，执行上{guard_mode}。"
        f"置信度{score}/100（{level}）；关键动作前先核对现实条件与停止条件。"
    )


def run_qimen_analysis(prefilled_topic=""):
    """运行传统奇门运筹分析。"""
    print()
    _sep("═")
    print("  奇门运筹分析")
    _sep("═")
    print("本功能按当前时辰生成简化九宫盘，并标出旬首、藏甲宫、庚方与三奇护局。")
    print("结果只作方位、时机、格局与遁甲护核的运筹参考。")
    print("不实现动漫设定中的“风后奇门”拨盘改局能力。")

    topic = ask_text(
        "所谋之事（如谈判、竞争、出行、项目推进）：",
        "所谋之事",
        200,
        initial=prefilled_topic or None,
    )
    topic_key = f"奇门：{topic}"
    should_proceed, _ = handle_duplicate_check(
        topic_key,
        "奇门运筹",
        allow_rephrase=False,
        match_mode="prefix",
    )
    if not should_proceed:
        return

    direction = ask_text(
        "当前或计划采用的方位（可选，如东、东南、西北）：",
        "方位",
        20,
        required=False,
    )
    mode = ask_choice(
        "场景类型（可选：谈判/竞争/财务/出行/事业/学习/健康/综合）：",
        "场景类型",
        ("谈判", "竞争", "财务", "出行", "事业", "学习", "健康", "综合"),
        default="综合",
    )
    history_question = _qimen_history_question(topic, direction, mode)

    focus_info = collect_focus_seed("请静心凝神，定住所谋之事。准备好后按回车定局...")
    focus_moment = datetime.datetime.now()

    result = analyze_qimen(topic=topic, direction=direction, mode=mode, current=focus_moment)
    record_question(history_question, "奇门运筹", _qimen_history_summary(result))
    print()
    print(f"定局人念：{focus_info['focus_seconds']:.2f}秒")
    if not present_conclusion(_plain_qimen_conclusion(result)):
        return
    print(format_qimen_report(result, include_plain_conclusion=False))
    _sep("═")
