# -*- coding: utf-8 -*-
"""
三爻快占模块

适合紧急场景、快速判断、单卦指引。

当前版本：
使用动态三爻快占。
结果由：
1. 农历时间
2. 起卦瞬间
3. 用户问题文本
4. 用户按回车前的停顿时间
共同决定。

这样避免纯随机，同时保持起卦结果的气机变化。
"""

from core.divination import dynamic_three_yao_quick_divination
from core.interpretation import interpret_three_yao
from core.qi_context import collect_focus_seed


def print_separator():
    print("=" * 70)


def run_quick_divination():
    """运行三爻快占流程"""

    print_separator()
    print("【三爻快占】")
    print("说明：本功能采用“天时 + 人念 + 问题 + 起卦瞬间”的动态三爻方式。")
    print("适合紧急场景、临时判断、快速查看当前状态。")
    print_separator()

    question = input("请输入你所问之事：").strip()

    if not question:
        question = "未命名问题"

    focus_info = collect_focus_seed(
        "请专注于核心问题。准备好后，按回车快速起卦..."
    )

    three_yao_info = dynamic_three_yao_quick_divination(
        question=question,
        mode="quick",
        extra_text="三爻快占",
        focus_seed=focus_info["focus_seed"]
    )

    interpret_result = interpret_three_yao(three_yao_info)

    print_separator()
    print("【快占问题】")
    print(f"所问之事：{question}")

    print_separator()
    print("【快占结果】")
    print(interpret_result["core_tip"])
    print(interpret_result["meaning_tip"])

    print_separator()
    print("【指引信息】")
    print(interpret_result["direction_tip"])
    print(interpret_result["weather_tip"])
    print(interpret_result["wu_xiang_tip"])

    print_separator()
    print("【气机信息】")
    print(f"人念停顿：{focus_info['focus_seconds']:.3f} 秒")
    print(f"气机种子：{three_yao_info['qi_seed']}")
    print(f"三爻结果：{three_yao_info['yao_list']}")

    print_separator()
    print(f"【行动建议】：{interpret_result['suggest']}")
    print_separator()



