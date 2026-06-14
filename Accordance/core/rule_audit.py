# -*- coding: utf-8 -*-
"""传统规则数据自检。

用于检查纳甲、八宫、世应、六十四卦和象义校准表是否互相一致。
自检只读数据，不参与起卦结果生成。
"""

from config.bagua_data import PALACE_HEXAGRAMS
from config.hexagram_data import HEXAGRAM_DATA
from config.hexagram_calibration import HEXAGRAM_CALIBRATION
from config.naja_data import (
    BAGUA_NAJIA, BAGUA_SHI_YING, LIUSHEN_START,
)
from config.wuxing_rules import (
    DIZHI_ORDER, WUXING_SHIER_CHANGSHENG,
)
from core.zhuanggua import (
    get_hexagram_palace, get_najia_all_lines, zhuang_gua_complete,
)


EXPECTED_BAGUA_NAJIA = {
    "乾": ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"],
    "兑": ["丁巳", "丁卯", "丁丑", "丁亥", "丁酉", "丁未"],
    "离": ["己卯", "己丑", "己亥", "己酉", "己未", "己巳"],
    "震": ["庚子", "庚寅", "庚辰", "庚午", "庚申", "庚戌"],
    "巽": ["辛丑", "辛亥", "辛酉", "辛未", "辛巳", "辛卯"],
    "坎": ["戊寅", "戊辰", "戊午", "戊申", "戊戌", "戊子"],
    "艮": ["丙辰", "丙午", "丙申", "丙戌", "丙子", "丙寅"],
    "坤": ["乙未", "乙巳", "乙卯", "癸丑", "癸亥", "癸酉"],
}


EXPECTED_CHANGSHENG_STARTS = {
    "甲木": "亥", "乙木": "午",
    "丙火": "寅", "丁火": "酉",
    "戊土": "寅", "己土": "酉",
    "庚金": "巳", "辛金": "子",
    "壬水": "申", "癸水": "卯",
}


def _add_issue(bucket, code, message):
    bucket.append({"code": code, "message": message})


def audit_traditional_rules():
    """返回传统规则数据自检报告。"""
    errors = []
    warnings = []

    if len(HEXAGRAM_DATA) != 64:
        _add_issue(errors, "hexagram_count", f"六十四卦数量为 {len(HEXAGRAM_DATA)}，应为64。")

    serials = sorted(item.get("serial_num") for item in HEXAGRAM_DATA.values())
    if serials != list(range(1, 65)):
        _add_issue(errors, "hexagram_serial", "卦序号未完整覆盖1-64。")

    palace_keys = {key for hexagrams in PALACE_HEXAGRAMS.values() for key in hexagrams}
    if palace_keys != set(HEXAGRAM_DATA):
        missing = set(HEXAGRAM_DATA) - palace_keys
        extra = palace_keys - set(HEXAGRAM_DATA)
        _add_issue(errors, "palace_coverage", f"八宫卦表覆盖异常：缺{missing}，多{extra}。")

    for key, detail in HEXAGRAM_DATA.items():
        upper_num, lower_num = key
        name = detail.get("name", "")
        palace = get_hexagram_palace(upper_num, lower_num)
        expected_palace = f"{palace['palace_name']}宫"
        if detail.get("palace") != expected_palace:
            _add_issue(
                errors,
                "palace_mismatch",
                f"{name} 原始卦宫为{detail.get('palace')}，八宫表为{expected_palace}。",
            )

        if name not in BAGUA_SHI_YING:
            _add_issue(errors, "shiying_missing", f"{name} 缺少世应定位。")
        else:
            shi_ying = BAGUA_SHI_YING[name]
            shi = shi_ying.get("shi", 0)
            ying = shi_ying.get("ying", 0)
            if not (1 <= shi <= 6 and 1 <= ying <= 6 and abs(shi - ying) == 3):
                _add_issue(errors, "shiying_invalid", f"{name} 世应异常：{shi_ying}。")

        najia = get_najia_all_lines(upper_num, lower_num)
        if len(najia) != 6 or any(item == "未知" for item in najia):
            _add_issue(errors, "naja_incomplete", f"{name} 纳甲不完整：{najia}。")

        zhuang = zhuang_gua_complete(upper_num, lower_num)
        lines = zhuang.get("lines", [])
        if len(lines) != 6:
            _add_issue(errors, "line_count", f"{name} 装卦爻数为{len(lines)}，应为6。")
        for line in lines:
            required = ("najia", "liuqin", "liushen", "changsheng", "dizhi", "dizhi_wuxing")
            missing = [field for field in required if not line.get(field) or line.get(field) == "未知"]
            if missing:
                _add_issue(errors, "line_field_missing", f"{name}{line.get('position_name', '')}缺字段：{missing}。")

        if name not in HEXAGRAM_CALIBRATION:
            _add_issue(warnings, "calibration_missing", f"{name} 缺少象义校准。")

    if BAGUA_NAJIA != EXPECTED_BAGUA_NAJIA:
        _add_issue(errors, "bagua_najia_changed", "八经卦纳甲表与内置审计基准不一致。")

    for gua_name, lines in BAGUA_NAJIA.items():
        if len(lines) != 6:
            _add_issue(errors, "bagua_najia_len", f"{gua_name} 纳甲条数为{len(lines)}，应为6。")
        for item in lines:
            if len(item) != 2 or item[1] not in DIZHI_ORDER:
                _add_issue(errors, "bagua_najia_ganzhi", f"{gua_name} 纳甲干支异常：{item}。")

    if WUXING_SHIER_CHANGSHENG != EXPECTED_CHANGSHENG_STARTS:
        _add_issue(errors, "changsheng_start", "十二长生起点与审计基准不一致。")

    if set(LIUSHEN_START) != set("甲乙丙丁戊己庚辛壬癸"):
        _add_issue(errors, "liushen_start", "六神起例未覆盖十天干。")

    summary = {
        "hexagrams": len(HEXAGRAM_DATA),
        "palaces": len(PALACE_HEXAGRAMS),
        "shiying": len(BAGUA_SHI_YING),
        "calibrations": len(HEXAGRAM_CALIBRATION),
        "bagua_najia": len(BAGUA_NAJIA),
    }
    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def format_audit_report(report):
    """格式化自检报告，供命令行模块输出。"""
    summary = report.get("summary", {})
    lines = [
        "传统规则自检报告",
        f"状态：{'通过' if report.get('passed') else '存在错误'}",
        (
            f"覆盖：六十四卦{summary.get('hexagrams', 0)}，"
            f"八宫{summary.get('palaces', 0)}，"
            f"世应{summary.get('shiying', 0)}，"
            f"象义校准{summary.get('calibrations', 0)}，"
            f"八卦纳甲{summary.get('bagua_najia', 0)}"
        ),
    ]

    errors = report.get("errors", [])
    warnings = report.get("warnings", [])
    if errors:
        lines.append("错误：")
        for item in errors[:20]:
            lines.append(f"- [{item['code']}] {item['message']}")
        if len(errors) > 20:
            lines.append(f"- 其余 {len(errors) - 20} 条略。")
    if warnings:
        lines.append("提醒：")
        for item in warnings[:20]:
            lines.append(f"- [{item['code']}] {item['message']}")
        if len(warnings) > 20:
            lines.append(f"- 其余 {len(warnings) - 20} 条略。")
    if not errors and not warnings:
        lines.append("未发现错误或缺项。")
    return "\n".join(lines)
