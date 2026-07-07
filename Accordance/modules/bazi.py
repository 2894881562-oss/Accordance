# -*- coding: utf-8 -*-
"""八字命理 CLI。"""

from core.bazi import analyze_bazi_birth, format_bazi_report, parse_birth_datetime
from core.question_history import handle_duplicate_check, record_question


def _sep(char="─", width=62):
    print(char * width)


def _ask_int(prompt, default=None, min_value=None, max_value=None):
    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        try:
            number = int(value)
        except ValueError:
            print("输入无效，请输入整数。")
            continue
        if min_value is not None and number < min_value:
            print(f"输入无效，不能小于 {min_value}。")
            continue
        if max_value is not None and number > max_value:
            print(f"输入无效，不能大于 {max_value}。")
            continue
        return number


def _ask_birth_date(prompt):
    while True:
        value = input(prompt).strip()
        try:
            solar = parse_birth_datetime(value, 0, 0)
        except ValueError:
            print("日期输入无效，请使用公历 YYYY-MM-DD，例如 2026-03-20；月份/日期可不补零，例如 2026-3-1。")
            continue
        return solar.strftime("%Y-%m-%d")


def _bazi_history_question(birth_date, birth_hour, birth_minute, gender):
    gender_text = gender or "未指定"
    return f"八字：{birth_date} {birth_hour:02d}:{birth_minute:02d}｜性别：{gender_text}"


def _bazi_history_summary(result):
    day_master = result.get("day_master", {})
    pattern = result.get("pattern_analysis", {})
    timing = result.get("current_timing_analysis", {})
    return (
        f"{result.get('bazi', '未知八字')}，"
        f"日主{day_master.get('day_gan', '未知')}{day_master.get('day_element', '')}，"
        f"{day_master.get('level', '强弱未定')}，"
        f"{pattern.get('pattern', '格局未定')}，"
        f"岁运{timing.get('level', '未评估')}"
    )


def run_bazi_analysis():
    """运行八字基础分析。"""
    print()
    _sep("═")
    print("  四柱八字基础分析")
    _sep("═")
    print("本功能按公历生日排四柱，节气分界采用工程近似；结果仅作传统文化研究参考。")

    birth_date = _ask_birth_date("公历出生日期（YYYY-MM-DD，可用 2026-3-1）：")
    birth_hour = _ask_int("出生小时（0-23）：", min_value=0, max_value=23)
    birth_minute = _ask_int("出生分钟（0-59，可回车默认0）：", 0, min_value=0, max_value=59)
    gender = input("性别（可选，男/女/不填）：").strip()

    history_question = _bazi_history_question(birth_date, birth_hour, birth_minute, gender)
    should_proceed, _ = handle_duplicate_check(
        history_question,
        "四柱八字",
        allow_rephrase=False,
        match_mode="exact",
    )
    if not should_proceed:
        return

    result = analyze_bazi_birth(birth_date, birth_hour, birth_minute, gender)
    record_question(history_question, "四柱八字", _bazi_history_summary(result))

    print()
    print(format_bazi_report(result))
    _sep("═")
