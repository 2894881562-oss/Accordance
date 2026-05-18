# -*- coding: utf-8 -*-
"""
六爻详占模块

适合重大决策、趋势判断、前因后果分析。

当前版本：
使用动态时间起卦法。
结果由：
1. 农历时间
2. 起卦瞬间
3. 用户问题文本
4. 用户按回车前的停顿时间
共同决定。

这样避免同一时辰内重复起卦完全固定，
同时不使用纯随机作为主要依据。
"""

from core.divination import dynamic_time_qi_gua
from core.interpretation import interpret_hexagram
from core.qi_context import collect_focus_seed


def print_separator():
    print("=" * 70)


def run_full_divination():
    """运行六爻详占流程"""

    print_separator()
    print("【六爻详占】")
    print("说明：本功能采用“天时 + 人念 + 问题 + 起卦瞬间”的动态起卦方式。")
    print("同一问题在不同起卦瞬间可能得到不同结果，但并非纯随机。")
    print_separator()

    question = input("请输入你所问之事：").strip()

    if not question:
        question = "未命名问题"

    focus_info = collect_focus_seed(
        "请静心凝神，专注于所问之事。准备好后，按回车确认起卦..."
    )

    hexagram_info = dynamic_time_qi_gua(
        question=question,
        mode="full",
        extra_text="六爻详占",
        focus_seed=focus_info["focus_seed"]
    )

    interpret_result = interpret_hexagram(hexagram_info)


    print_separator()
    print("【起卦结果】")
    print(f"卦名：{interpret_result['gua_name']}")
    print(f"卦辞：{interpret_result['gua_ci']}")
    print(f"吉凶等级：{interpret_result['ji_xiong']}")
    print(f"核心意象：{'、'.join(interpret_result['core_meaning'])}")
    print_separator()
    print("【卦象解读】")
    print(interpret_result['qian_yin_hou_guo'])
    print(interpret_result['sheng_ke_analysis'])
    print(interpret_result['wang_shuai_analysis'])
    print(interpret_result['dong_yao_tip'])

    # 新增：打印动爻爻辞和变卦
    if interpret_result.get("yao_ci_tip"):
        print(interpret_result['yao_ci_tip'])
    if interpret_result.get("bian_gua_tip"):
        print(interpret_result['bian_gua_tip'])

    # 新增：打印纳甲解读（完善后的版本）
    if interpret_result.get("naja_analysis"):
        print_separator()
        print("【六爻纳甲深度解读】")
        print(interpret_result['naja_analysis'])

    print_separator()
    print("【气机信息】")
    print(f"人念停顿：{focus_info['focus_seconds']:.3f} 秒")
    print(f"气机种子：{hexagram_info['qi_seed']}")
    print_separator()
    print(f"【决策建议】：{interpret_result['decision_suggest']}")
    print_separator()



