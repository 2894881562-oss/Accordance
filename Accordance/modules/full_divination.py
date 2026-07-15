# -*- coding: utf-8 -*-
"""
六爻详占模块
适合重大决策、趋势判断、前因后果分析。
整合京房纳甲筮法 + 梅花易数体用体系。
"""

from core.divination import dynamic_time_qi_gua
from core.cli_input import ask_text, present_conclusion
from core.interpretation import interpret_hexagram
from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi
from core.question_precheck import build_question_profile, format_question_profile
from core.question_history import handle_duplicate_check, record_question


def _sep(char="─", width=62):
    print(char * width)


def run_full_divination(prefilled_question=None):
    """运行六爻详占流程"""
    print()
    _sep("═")
    print("  六爻详占 · 京房纳甲筮法 + 梅花易数体用")
    _sep("═")

    question = ask_text(
        "请输入你所问之事：",
        "所问之事",
        200,
        initial=prefilled_question,
    )

    should_proceed, question = handle_duplicate_check(question, "六爻详占")
    if not should_proceed:
        return

    question_profile = build_question_profile(question, current_method_key="full")
    print()
    print(format_question_profile(question_profile))

    external_omen = ask_text(
        "若有外应请输入，无则回车：",
        "外应",
        160,
        required=False,
    )
    focus_info = collect_focus_seed("请静心凝神，专注于所问之事。准备好后按回车起卦...")

    hexagram_info = dynamic_time_qi_gua(
        question=question, mode="full",
        extra_text=f"六爻详占|外应:{external_omen}",
        focus_seed=focus_info["focus_seed"],
    )
    hexagram_info["external_omen"] = external_omen
    result = interpret_hexagram(hexagram_info)

    record_question(
        question, "六爻详占",
        f"{result['gua_name']}（{result['ji_xiong']}），"
        f"体用：{result.get('tiyong_info', {}).get('relation', '未知')}",
        context=f"外应：{external_omen}" if external_omen else "",
    )

    if not present_conclusion(result["plain_conclusion"]):
        return

    tiyong = result.get("tiyong_info", {})
    j = result  # shorthand

    # ===== 卦象概要 =====
    print()
    _sep("━")
    print(f"  【{j['gua_name']}】  {j['ji_xiong']}  |  "
          f"体用：{tiyong.get('relation', '')}（{tiyong.get('relation_desc', '')}）")
    _sep("━")
    print(f"  卦辞：{j['gua_ci']}")
    print(f"  卦意：{'、'.join(j['core_meaning'][:4])}")
    print(f"  校准：{j['calibration_tip']}")
    if j.get("daxiang"):
        print(f"  大象：{j['daxiang']}")
    if j.get("tuanzhuan"):
        print(f"  彖传：{j['tuanzhuan']}")
    print(f"  问题：{question}")
    print()

    # ===== 纳甲装卦（精简表） =====
    print("  【纳甲装卦】")
    lines = j['zhuanggua_result']['lines']
    for line in reversed(lines):
        marks = ""
        if line["is_shi"]:
            marks += " 世"
        if line["is_ying"]:
            marks += " 应"
        if line.get("is_dong"):
            marks += " →动"
        status = ""
        if line.get("line_status"):
            status = f"  [{','.join(line['line_status'])}]"
        print(f"  {line['position_name']}  {line['najia']}  {line['dizhi_wuxing']}  "
              f"{line['liuqin']}  {line['liushen']}{marks}{status}")
    print()

    zg = j['zhuanggua_result']
    print(f"  世爻：第{zg['shi_ying']['shi']}爻  |  "
          f"应爻：第{zg['shi_ying']['ying']}爻  |  "
          f"卦宫：{zg['palace_name']}宫（{zg['palace_wuxing']}，{zg.get('palace_role', '')}）")
    print(f"  日辰：{zg.get('day_ganzhi', '未知')}  |  "
          f"旬空：{'、'.join(zg.get('xunkong', {}).get('empty_branches', [])) or '无'}  |  "
          f"月建：{zg.get('yueling', '未知')}  |  "
          f"月破：{zg.get('yuepo', '未知')}  |  "
          f"日破：{zg.get('ripo', '未知')}")
    print()

    # ===== 动变与互错综 =====
    print(f"  【动爻】{j['dong_yao_tip']}")
    print(f"  {j['yao_ci_tip']}")
    print(f"  {j['bian_gua_tip']}")
    print()
    print(f"  【互卦】{j['hu_gua_tip']}")
    print(f"  【错卦】{j['cuo_gua_tip']}")
    print(f"  【综卦】{j['zong_gua_tip']}")
    print()

    # ===== 体用生克 =====
    print(f"  【体用】{tiyong.get('relation', '')} — {tiyong.get('relation_desc', '')}")
    print(f"  【五行】{j['sheng_ke_analysis']}")
    print(f"  【旺衰】{j['wang_shuai_analysis']}")
    print()

    # ===== 用神分析 =====
    print(f"  【用神分析】")
    print(f"  {j['yongshen_system_summary']}")
    print()
    print(f"  【传统依据】{j['source_trace']}")
    print(f"  【现实校验】{j['reality_check']}")
    print()

    # ===== 动变回头生克 =====
    print(f"  【动变回头】{j['bian_line_relation_tip']}")
    print()

    # ===== 六亲格局 =====
    if j.get("liuqin_interpretation"):
        print(f"  【六亲格局】{j['liuqin_interpretation']}")
        print()

    # ===== 爻力 =====
    print(f"  【爻力概要】{j['line_strength_summary']}")
    print()

    # ===== 六神制化 =====
    print(f"  【六神制化】{j['liushen_zhihua_summary']}")
    print()

    # ===== 卦身 =====
    guashen = j.get("guashen_summary", "")
    if guashen:
        print(f"  【卦身】{guashen}")
        print()

    # ===== 神煞 =====
    shensha = j.get("shensha_summary", "")
    if shensha and "未中" not in shensha:
        print(f"  【神煞】{shensha}")
        key_hints = j.get("shensha_key_hints", [])
        for hint in key_hints[:3]:
            print(f"    → {hint}")
        print()

    # ===== 地支关系 =====
    print(f"  【地支关系】{j['dizhi_relation_summary']}")
    print()

    # ===== 外应 =====
    omen = j.get("external_omen_tip", "")
    if omen:
        print(f"  【外应】{omen}")
        print()

    # ===== 综合断语（核心） =====
    _sep("═")
    print(f"  【断语】")
    print(f"  {j['judgment_detail']}")
    print()
    print(f"  ▶ {j['judgment_conclusion']}")
    _sep("═")

    # ===== 气机信息 =====
    print(f"  日干支：{get_accurate_day_ganzhi()}  |  "
          f"人念：{focus_info['focus_seconds']:.2f}秒  |  "
          f"种子：{hexagram_info['qi_seed']}")
    print()

    # ===== 人本指引 =====
    human = j.get("human_guidance", "")
    if human:
        print(human)
    print(j.get("human_agency_reminder", ""))
    print()
    # ===== 提醒 =====
    print(f"  【提醒】本系统仅为传统文化研究参考，不替代现实判断。")
    _sep("═")
    print()
