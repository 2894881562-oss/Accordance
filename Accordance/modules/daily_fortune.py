# -*- coding: utf-8 -*-
"""
当日气运指引模块

功能定位：
1. 查看当天整体行事基调；
2. 输出当日主卦、体用分析、互卦辅助；
3. 当日气运应保持"日内相对稳定"，不应每次刷新都剧烈变化。

当前版本：
1. 主卦使用 time_qi_gua()，基于农历年月日时；
2. 辅助单卦使用 daily_guidance_gua()，基于农历日期生成；
3. 不使用 random、不使用用户停顿时间；
4. 使用精确日干支算法。
"""

from core.divination import time_qi_gua, daily_guidance_gua
from core.interpretation import interpret_hexagram, interpret_three_yao
from core.qi_context import get_accurate_day_ganzhi


def print_separator():
    print("=" * 70)


def run_daily_fortune():
    """运行当日气运指引流程"""

    print_separator()
    print("【当日气运指引】")
    print("说明：本功能用于查看当天整体行事基调，含体用生克与互卦辅助。")
    print("当日气运采用日基准算法，同一天内结果相对稳定。")
    input("静心片刻后，按回车查看当日气运...")

    # 当日主卦
    hexagram_info = time_qi_gua()
    interpret_result = interpret_hexagram(hexagram_info)

    # 当日辅助单卦
    daily_gua_info = daily_guidance_gua()
    daily_interpret = interpret_three_yao(daily_gua_info)

    lunar_info = hexagram_info["lunar_info"]

    print_separator()
    print("【日期信息】")
    print(f"农历：{lunar_info['year']}年 {lunar_info['month']}月 {lunar_info['day']}日")
    print(f"日干支：{get_accurate_day_ganzhi()}")
    print(f"当前时辰序号：{lunar_info['shi_chen']}")
    print(f"当前季节：{lunar_info['season']}")

    print_separator()
    print(f"【当日气运主卦】：{interpret_result['gua_name']}（{interpret_result['ji_xiong']}）")
    print(f"当日核心基调：{'、'.join(interpret_result['core_meaning'][:4])}")
    print(f"主卦卦辞：{interpret_result['gua_ci']}")

    print_separator()
    print("【体用生克分析】")
    print(interpret_result['tiyong_tip'])

    print_separator()
    print("【五行生克与旺衰】")
    print(interpret_result['sheng_ke_analysis'])
    print(interpret_result['wang_shuai_analysis'])

    print_separator()
    print("【互卦指引（当日过程视角）】")
    print(interpret_result['hu_gua_tip'])
    print(interpret_result['hu_cuo_zong_tip'])

    print_separator()
    print("【当日辅助指引】")
    print(daily_interpret["core_tip"])
    print(daily_interpret["direction_tip"])
    print(daily_interpret["weather_tip"])
    print(daily_interpret["wu_xiang_tip"])
    if daily_interpret.get("single_tiyong_tip"):
        print(daily_interpret["single_tiyong_tip"])
    print(f"心绪指引：宜{'、'.join(daily_gua_info['gua_info']['core_meaning'][:2])}")

    print_separator()
    print("【空破刑冲与六神制化】")
    print(interpret_result['line_strength_summary'])
    print(interpret_result['bian_line_relation_tip'])
    print(interpret_result['yongshen_system_summary'])
    print(interpret_result['dizhi_relation_summary'])
    print(interpret_result['liushen_zhihua_summary'])

    print_separator()
    print("【当日行事建议】")
    print(interpret_result["traditional_evidence_chain"])
    print()
    print(interpret_result["decision_suggest"])

    print_separator()
    print("【使用提醒】")
    print("1. 当日气运用于查看当天整体基调，不建议短时间内反复刷新求不同结果。")
    print('2. 如果是临时问题，请使用“三爻快占”。')
    print('3. 如果是重大决策，请使用“六爻详占”。')
    print_separator()
