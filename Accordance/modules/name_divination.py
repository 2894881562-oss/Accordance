# -*- coding: utf-8 -*-
"""姓名起卦模块。笔画数建议使用康熙字典笔画；使用六爻纳甲体系解卦。"""

from core.divination import name_qi_gua
from core.interpretation import interpret_hexagram
from core.qi_context import get_accurate_day_ganzhi
from core.question_history import handle_duplicate_check, record_question
from config.name_strokes import analyze_text_strokes


def _sep(char="─", width=62):
    print(char * width)


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


def _fill_missing_strokes(label, analysis):
    if not analysis["missing"]:
        return analysis

    total = analysis["total"]
    details = []
    for item in analysis["details"]:
        if item["stroke"] is not None:
            details.append(item)
            continue
        stroke = _input_positive_int(f"未识别{label}字「{item['char']}」的康熙笔画，请手动输入：")
        total += stroke
        details.append({"char": item["char"], "stroke": stroke})

    return {"total": total, "details": details, "missing": []}


def _format_stroke_details(analysis):
    return " + ".join(f"{item['char']}{item['stroke']}画" for item in analysis["details"])


def _name_history_prefix(xing, ming):
    return f"姓名起卦：{xing}{ming}"


def _name_history_question(xing, ming, xing_stroke, ming_stroke):
    return f"姓名起卦：{xing}{ming}｜姓氏{xing_stroke}画｜名字{ming_stroke}画"


def run_name_divination():
    """运行姓名起卦流程"""
    print()
    _sep("═")
    print("  姓名起卦 · 六爻纳甲体系解卦")
    _sep("═")

    xing = input("请输入姓氏：").strip() or "未命名姓氏"
    ming = input("请输入名字：").strip() or "未命名名字"
    should_proceed, _ = handle_duplicate_check(
        _name_history_prefix(xing, ming),
        "姓名起卦",
        allow_rephrase=False,
        match_mode="prefix",
    )
    if not should_proceed:
        return

    xing_analysis = _fill_missing_strokes("姓氏", analyze_text_strokes(xing))
    ming_analysis = _fill_missing_strokes("名字", analyze_text_strokes(ming))
    xing_stroke = xing_analysis["total"]
    ming_stroke = ming_analysis["total"]
    history_question = _name_history_question(xing, ming, xing_stroke, ming_stroke)

    print(
        f"自动识别笔画：姓氏「{xing}」{xing_stroke}画"
        f"（{_format_stroke_details(xing_analysis)}）；"
        f"名字「{ming}」{ming_stroke}画"
        f"（{_format_stroke_details(ming_analysis)}）。"
    )

    name_gua_info = name_qi_gua(xing=xing, ming=ming, xing_stroke=xing_stroke, ming_stroke=ming_stroke)
    r = interpret_hexagram(name_gua_info)
    tiyong = r.get("tiyong_info", {})
    record_question(
        history_question,
        "姓名起卦",
        f"{r['gua_name']}（{r['ji_xiong']}），体用：{tiyong.get('relation', '未知')}",
    )

    # ===== 基本信息 =====
    print()
    _sep("━")
    print(f"  姓名：{xing}{ming}（姓氏{xing_stroke}画，名字{ming_stroke}画）")
    print(f"  【{r['gua_name']}】{r['ji_xiong']}  |  "
          f"体用：{tiyong.get('relation', '')}（{tiyong.get('relation_desc', '')}）")
    _sep("━")
    print(f"  卦辞：{r['gua_ci']}")
    print(f"  卦意：{'、'.join(r['core_meaning'][:4])}")
    print(f"  校准：{r['calibration_tip']}")
    if r.get("daxiang"):
        print(f"  大象：{r['daxiang']}")
    print()

    # ===== 纳甲装卦 =====
    print("  【纳甲装卦】")
    lines = r['zhuanggua_result']['lines']
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

    zg = r['zhuanggua_result']
    print(f"  世爻：第{zg['shi_ying']['shi']}爻  |  应爻：第{zg['shi_ying']['ying']}爻  |  "
          f"卦宫：{zg['palace_name']}宫（{zg['palace_wuxing']}）")
    print(f"  日辰：{zg.get('day_ganzhi', '未知')}  |  月建：{zg.get('yueling', '未知')}")
    print()

    # ===== 体用与动变 =====
    print(f"  【体用】{tiyong.get('relation', '')} — {tiyong.get('relation_desc', '')}")
    print(f"  【五行】{r['sheng_ke_analysis']}")
    print(f"  【旺衰】{r['wang_shuai_analysis']}")
    print(f"  【动爻】{r['dong_yao_tip']}")
    print()

    print(f"  【互卦】{r['hu_gua_tip']}")
    print(f"  【错卦】{r['cuo_gua_tip']}")
    print()

    # ===== 用神与六亲 =====
    print(f"  【用神分析】{r['yongshen_system_summary']}")
    print()
    print(f"  【传统依据】{r['source_trace']}")
    print(f"  【现实校验】{r['reality_check']}")
    print()
    print(f"  【动变回头】{r['bian_line_relation_tip']}")
    print()
    print(f"  【六亲格局】{r['liuqin_interpretation']}")
    print()
    print(f"  【六神制化】{r['liushen_zhihua_summary']}")
    print()

    # ===== 断语 =====
    _sep("═")
    print(f"  【断语】")
    print(f"  {r['judgment_detail']}")
    print()
    print(f"  ▶ {r['judgment_conclusion']}")
    _sep("═")

    # ===== 人本指引 =====
    human = r.get("human_guidance", "")
    if human:
        print(human)
    print(r.get("human_agency_reminder", ""))

    print(f"  起卦日干支：{get_accurate_day_ganzhi()}")
    print(f"  【简短结论】{r['plain_conclusion']}")
    _sep("═")
    print()
