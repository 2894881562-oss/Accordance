# -*- coding: utf-8 -*-
"""
当日气运指引模块
查看当天整体行事基调，输出当日主卦、体用分析、互卦辅助。
当日气运采用日基准算法，同一天内结果相对稳定。
"""

from core.divination import time_qi_gua, daily_guidance_gua
from core.interpretation import interpret_hexagram, interpret_three_yao
from core.qi_context import get_accurate_day_ganzhi


def _sep(char="─", width=62):
    print(char * width)


def run_daily_fortune():
    """运行当日气运指引流程"""
    print()
    _sep("═")
    print("  当日气运指引")
    _sep("═")

    input("静心片刻后，按回车查看当日气运...")

    hexagram_info = time_qi_gua()
    r = interpret_hexagram(hexagram_info)

    daily_gua_info = daily_guidance_gua()
    dr = interpret_three_yao(daily_gua_info)

    lunar = hexagram_info["lunar_info"]

    # ===== 日期与主卦 =====
    print()
    _sep("━")
    print(f"  农历：{lunar['year']}年{lunar['month']}月{lunar['day']}日  |  "
          f"日干支：{get_accurate_day_ganzhi()}  |  "
          f"季节：{lunar['season']}")
    print(f"  当日主卦：【{r['gua_name']}】{r['ji_xiong']}")
    print(f"  基调：{'、'.join(r['core_meaning'][:3])}")
    print(f"  卦辞：{r['gua_ci']}")
    _sep("━")

    # ===== 体用 =====
    tiyong = r.get("tiyong_info", {})
    print()
    print(f"  【体用】{tiyong.get('relation', '')} — {tiyong.get('relation_desc', '')}")
    print(f"  【五行】{r['sheng_ke_analysis']}")
    print(f"  【旺衰】{r['wang_shuai_analysis']}")
    print(f"  【动爻】{r['dong_yao_tip']}")

    # ===== 互卦 =====
    print()
    print(f"  【互卦】{r['hu_gua_tip']}")

    # ===== 用神与动变 =====
    print()
    print(f"  【用神】{r['yongshen_system_summary']}")
    print(f"  【动变】{r['bian_line_relation_tip']}")

    # ===== 六神制化 =====
    print()
    print(f"  【六神制化】{r['liushen_zhihua_summary']}")

    # ===== 辅助单卦 =====
    print()
    print(f"  【辅助指引】{dr['core_tip']}")
    print(f"  {dr['meaning_tip']}")
    print(f"  宜：{'、'.join(daily_gua_info['gua_info']['core_meaning'][:2])}")

    # ===== 断语 =====
    print()
    _sep("═")
    print(f"  【当日断语】")
    print(f"  {r['judgment_detail']}")
    print()
    print(f"  ▶ {r['judgment_conclusion']}")
    _sep("═")

    # ===== 人本指引 =====
    human = r.get("human_guidance", "")
    if human:
        print(human)

    print(f"  提醒：当日气运用於查看整体基调，临时问题请用三爻快占，重大决策请用六爻详占。")
    _sep("═")
    print()
