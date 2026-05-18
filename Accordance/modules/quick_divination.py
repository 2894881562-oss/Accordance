# -*- coding: utf-8 -*-
"""
三爻快占模块

适合紧急场景、快速判断、单卦指引。

当前版本：
使用动态三爻快占 + 梅花易数体用分析 + 互卦辅助。
"""

from core.divination import dynamic_three_yao_quick_divination
from core.interpretation import interpret_three_yao
from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi


def print_separator():
    print("=" * 70)


def run_quick_divination():
    """运行三爻快占流程"""

    print_separator()
    print("【三爻快占】")
    print("说明：本功能采用动态三爻方式，结合梅花易数单卦体用分析。")
    print("适合紧急场景、临时判断、快速查看当前状态。")
    print_separator()

    question = input("请输入你所问之事：").strip()

    if not question:
        question = "未命名问题"

    external_omen = input("若起卦前后有明显外应请输入，无则回车：").strip()

    focus_info = collect_focus_seed(
        "请专注于核心问题。准备好后，按回车快速起卦..."
    )

    three_yao_info = dynamic_three_yao_quick_divination(
        question=question,
        mode="quick",
        extra_text=f"三爻快占|外应:{external_omen}",
        focus_seed=focus_info["focus_seed"]
    )
    three_yao_info["external_omen"] = external_omen

    interpret_result = interpret_three_yao(three_yao_info)

    print_separator()
    print("【快占问题】")
    print(f"所问之事：{question}")

    print_separator()
    print("【快占结果】")
    print(interpret_result["core_tip"])
    print(interpret_result["meaning_tip"])

    # 体用分析
    if interpret_result.get("tiyong_note"):
        print()
        print(f"【爻象与旺衰】{interpret_result['tiyong_note']}")
    if interpret_result.get("single_tiyong_tip"):
        print(interpret_result["single_tiyong_tip"])

    print_separator()
    print("【指引信息】")
    print(interpret_result["direction_tip"])
    print(interpret_result["weather_tip"])
    print(interpret_result["wu_xiang_tip"])

    print_separator()
    print("【气机信息】")
    print(f"日干支：{get_accurate_day_ganzhi()}")
    print(f"人念停顿：{focus_info['focus_seconds']:.3f} 秒")
    print(f"气机种子：{three_yao_info['qi_seed']}")
    print(f"三爻结果：{three_yao_info['yao_list']}")

    print_separator()
    print("【外应参考（梅花克应）】")
    print(interpret_result["external_omen_tip"])

    print_separator()
    print(f"【行动建议】：{interpret_result['suggest']}")
    print_separator()
