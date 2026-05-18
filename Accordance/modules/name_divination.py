# -*- coding: utf-8 -*-
"""姓名起卦模块。"""

from core.divination import name_qi_gua
from core.interpretation import interpret_hexagram
from core.qi_context import get_accurate_day_ganzhi


def print_separator():
    print("=" * 70)


def _input_positive_int(prompt):
    while True:
        value = input(prompt).strip()
        try:
            num = int(value)
            if num > 0:
                return num
        except ValueError:
            pass
        print("输入无效，请输入正整数笔画数。")


def run_name_divination():
    """运行姓名起卦流程。"""
    print_separator()
    print("【姓名起卦】")
    print("说明：笔画数建议使用康熙字典笔画；使用六爻纳甲体系解卦。")

    xing = input("请输入姓氏：").strip() or "未命名姓氏"
    ming = input("请输入名字：").strip() or "未命名名字"

    xing_stroke = _input_positive_int(f"请输入姓氏「{xing}」的总笔画数：")
    ming_stroke = _input_positive_int(f"请输入名字「{ming}」的总笔画数：")

    name_gua_info = name_qi_gua(
        xing=xing,
        ming=ming,
        xing_stroke=xing_stroke,
        ming_stroke=ming_stroke,
    )
    interpret_result = interpret_hexagram(name_gua_info)

    print_separator()
    print("【姓名信息】")
    print(f"姓名：{xing}{ming}")
    print(f"姓氏笔画：{xing_stroke}")
    print(f"名字笔画：{ming_stroke}")
    print(f"起卦日干支：{get_accurate_day_ganzhi()}")

    print_separator()
    print(f"【起卦结果】：{interpret_result['gua_name']}")
    print(f"卦辞：{interpret_result['gua_ci']}")
    print(f"吉凶等级：{interpret_result['ji_xiong']}")
    print(f"核心意象：{'、'.join(interpret_result['core_meaning'])}")

    print_separator()
    print("【体用生克分析】")
    print(interpret_result['tiyong_tip'])

    print_separator()
    print("【五行生克与旺衰】")
    print(interpret_result["qian_yin_hou_guo"])
    print(interpret_result["sheng_ke_analysis"])
    print(interpret_result["wang_shuai_analysis"])
    print(interpret_result["dong_yao_tip"])
    if interpret_result.get("yao_ci_tip"):
        print(interpret_result["yao_ci_tip"])
    if interpret_result.get("bian_gua_tip"):
        print(interpret_result["bian_gua_tip"])

    print_separator()
    print("【互卦与错卦】")
    print(interpret_result['hu_gua_tip'])
    print(interpret_result['hu_cuo_zong_tip'])
    print(interpret_result['cuo_gua_tip'])

    print_separator()
    print("【六爻纳甲装卦表】")
    print(interpret_result['zhuanggua_table'])

    print_separator()
    print("【六亲格局】")
    print(interpret_result['yongshen_system_summary'])
    print(interpret_result['liuqin_summary'])
    if interpret_result.get("dong_yao_liuqin_tip"):
        print(interpret_result['dong_yao_liuqin_tip'])
    if interpret_result.get("liuqin_interpretation"):
        print(interpret_result['liuqin_interpretation'])

    print_separator()
    print("【空破刑冲与纳音力量】")
    print(interpret_result['line_strength_summary'])
    print(interpret_result['bian_line_relation_tip'])
    print(interpret_result['dizhi_relation_summary'])
    print(interpret_result['nayin_summary'])
    print(interpret_result['liushen_zhihua_summary'])

    print_separator()
    print("【传统依据链】")
    print(interpret_result['traditional_evidence_chain'])
    print_separator()
    print(f"【综合建议】：{interpret_result['decision_suggest']}")
    print_separator()
