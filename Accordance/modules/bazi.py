# -*- coding: utf-8 -*-
"""八字命理 CLI。"""

from core.bazi import analyze_bazi_birth, format_bazi_report


def _sep(char="─", width=62):
    print(char * width)


def _ask_int(prompt, default=None):
    value = input(prompt).strip()
    if not value and default is not None:
        return default
    return int(value)


def run_bazi_analysis():
    """运行八字基础分析。"""
    print()
    _sep("═")
    print("  四柱八字基础分析")
    _sep("═")
    print("本功能按公历生日排四柱，节气分界采用工程近似；结果仅作传统文化研究参考。")

    birth_date = input("公历出生日期（YYYY-MM-DD）：").strip()
    birth_hour = _ask_int("出生小时（0-23）：")
    birth_minute = _ask_int("出生分钟（0-59，可回车默认0）：", 0)
    gender = input("性别（可选，男/女/不填）：").strip()

    try:
        result = analyze_bazi_birth(birth_date, birth_hour, birth_minute, gender)
    except ValueError as exc:
        print(f"输入错误：{exc}")
        return

    print()
    print(format_bazi_report(result))
    _sep("═")
