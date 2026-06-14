# -*- coding: utf-8 -*-
"""
三爻快占模块
适合紧急场景、快速判断、单卦指引。
使用动态三爻快占 + 梅花易数单卦体用分析。
"""

from core.divination import dynamic_three_yao_quick_divination
from core.interpretation import interpret_three_yao
from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi
from core.question_precheck import build_question_profile, format_question_profile
from core.question_history import handle_duplicate_check, record_question


def _sep(char="─", width=62):
    print(char * width)


def run_quick_divination(prefilled_question=None):
    """运行三爻快占流程"""
    print()
    _sep("═")
    print("  三爻快占")
    _sep("═")

    question = (prefilled_question or "").strip()
    if not question:
        question = input("请输入你所问之事：").strip()
    if not question:
        question = "未命名问题"

    should_proceed, question = handle_duplicate_check(question, "三爻快占")
    if not should_proceed:
        return

    question_profile = build_question_profile(question, current_method_key="quick")
    print()
    print(format_question_profile(question_profile))

    external_omen = input("若有外应请输入，无则回车：").strip()
    focus_info = collect_focus_seed("请专注于核心问题。准备好后按回车起卦...")

    three_yao_info = dynamic_three_yao_quick_divination(
        question=question, mode="quick",
        extra_text=f"三爻快占|外应:{external_omen}",
        focus_seed=focus_info["focus_seed"],
    )
    three_yao_info["external_omen"] = external_omen
    r = interpret_three_yao(three_yao_info)

    record_question(
        question, "三爻快占",
        f"{three_yao_info['gua_info']['full_name']}卦，"
        f"五行{three_yao_info['gua_info']['element']}，"
        f"{r['suggest'][:20]}"
    )

    print()
    _sep("━")
    print(f"  问题：{question}")
    print(f"  {r['core_tip']}")
    print(f"  {r['meaning_tip']}")
    _sep("━")

    if r.get("tiyong_note") or r.get("single_tiyong_tip"):
        print()
        if r.get("tiyong_note"):
            print(f"  {r['tiyong_note']}")
        if r.get("single_tiyong_tip"):
            print(f"  {r['single_tiyong_tip']}")

    print()
    print(f"  【方位】{r['direction_tip']}")
    print(f"  【天时】{r['weather_tip']}")
    print(f"  【物象】{r['wu_xiang_tip']}")
    print()
    print("  【适用边界】三爻快占适合紧急、单点、短期判断；若要看前因后果、过程转折或重大决策，应改用六爻详占。")
    print()
    print(f"  ▶ {r['suggest']}")

    omen = r.get("external_omen_tip", "")
    if omen:
        print()
        print(f"  外应：{omen}")

    print()
    print(f"  日干支：{get_accurate_day_ganzhi()}  |  "
          f"人念：{focus_info['focus_seconds']:.2f}秒  |  "
          f"种子：{three_yao_info['qi_seed']}")
    print(f"  三爻：{three_yao_info['yao_list']}")
    _sep("═")
    print()
