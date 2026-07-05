# -*- coding: utf-8 -*-
"""规则与数据一致性审计。

该模块面向维护者：把纳甲、世应、八宫、六十四卦校准与起卦法选择器
中最容易手写漂移的规则集中校验，便于每次改规则后快速回归。
"""

from config.bagua_data import NUM_TO_GUA_NAME, PALACE_HEXAGRAMS, PALACE_WUXING
from config.bazi_data import DIZHI_HIDDEN_STEMS, GAN_YINYANG, TEN_GOD_GROUP
from config.hexagram_calibration import HEXAGRAM_CALIBRATION, build_calibration_tip
from config.hexagram_data import HEXAGRAM_DATA
from config.naja_data import BAGUA_NAJIA, BAGUA_SHI_YING, LIUSHEN_ORDER, LIUSHEN_START, NAYIN_TABLE
from config.wuxing_rules import DIZHI_ORDER, DIZHI_WUXING, TIANGAN_WUXING
from core.method_selector import METHOD_PROFILES, NEGATIVE_HINTS, recommend_divination_methods
from core.zhuanggua import (
    SHI_YING_BY_PALACE_INDEX,
    get_changsheng_for_line,
    get_hexagram_palace,
    get_liuqin_all_lines,
    get_najia_all_lines,
    get_shi_ying,
    get_shi_ying_by_key,
)
from core.bazi import analyze_bazi_birth, get_ten_god


TIANGAN_ORDER = set(TIANGAN_WUXING)
VALID_DIZHI = set(DIZHI_ORDER)
VALID_LIUQIN = {"父母", "兄弟", "子孙", "妻财", "官鬼"}
REQUIRED_CALIBRATION_FIELDS = ("axis", "keywords", "proper_use", "risk")


def _issue(level, area, message, detail=""):
    return {
        "level": level,
        "area": area,
        "message": message,
        "detail": detail,
    }


def _hexagram_names():
    return {detail.get("name", "") for detail in HEXAGRAM_DATA.values()}


def audit_palace_hexagram_matrix():
    """校验八宫六十四卦矩阵。"""
    issues = []
    all_keys = []

    if set(PALACE_HEXAGRAMS) != set(PALACE_WUXING):
        issues.append(_issue(
            "error",
            "八宫",
            "PALACE_HEXAGRAMS 与 PALACE_WUXING 的宫名不一致",
            f"hexagrams={sorted(PALACE_HEXAGRAMS)} wuxing={sorted(PALACE_WUXING)}",
        ))

    for palace_name, hexagrams in PALACE_HEXAGRAMS.items():
        if len(hexagrams) != 8:
            issues.append(_issue("error", "八宫", f"{palace_name}宫不是 8 卦", str(len(hexagrams))))
        if len(set(hexagrams)) != len(hexagrams):
            issues.append(_issue("error", "八宫", f"{palace_name}宫内部存在重复卦键"))
        for index, key in enumerate(hexagrams):
            all_keys.append(key)
            if key not in HEXAGRAM_DATA:
                issues.append(_issue("error", "八宫", f"{palace_name}宫第{index + 1}卦不在六十四卦库", str(key)))
                continue
            expected_palace = f"{palace_name}宫"
            actual_palace = HEXAGRAM_DATA[key].get("palace", "")
            if actual_palace and actual_palace != expected_palace:
                issues.append(_issue(
                    "warning",
                    "八宫",
                    f"{HEXAGRAM_DATA[key].get('name')} 的 palace 字段与八宫表不一致",
                    f"data={actual_palace} expected={expected_palace}",
                ))

    if len(all_keys) != 64 or len(set(all_keys)) != 64:
        issues.append(_issue("error", "八宫", "八宫表未形成 64 个唯一卦键", f"total={len(all_keys)} unique={len(set(all_keys))}"))

    missing = set(HEXAGRAM_DATA) - set(all_keys)
    extra = set(all_keys) - set(HEXAGRAM_DATA)
    if missing:
        issues.append(_issue("error", "八宫", "八宫表缺少六十四卦键", str(sorted(missing))))
    if extra:
        issues.append(_issue("error", "八宫", "八宫表包含六十四卦库以外的卦键", str(sorted(extra))))

    return issues


def audit_shi_ying_rules():
    """校验手写世应表与八宫序列推导结果是否一致。"""
    issues = []
    expected_names = _hexagram_names()

    missing = expected_names - set(BAGUA_SHI_YING)
    extra = set(BAGUA_SHI_YING) - expected_names
    if missing:
        issues.append(_issue("error", "世应", "BAGUA_SHI_YING 缺少卦名", "、".join(sorted(missing))))
    if extra:
        issues.append(_issue("error", "世应", "BAGUA_SHI_YING 含未知卦名", "、".join(sorted(extra))))

    for key, detail in HEXAGRAM_DATA.items():
        name = detail.get("name", "")
        palace_info = get_hexagram_palace(*key)
        palace_index = palace_info.get("palace_index", -1)
        expected = SHI_YING_BY_PALACE_INDEX.get(palace_index)
        derived = get_shi_ying_by_key(*key)
        by_name = get_shi_ying(name)
        table_value = BAGUA_SHI_YING.get(name)

        if not expected:
            issues.append(_issue("error", "世应", f"{name} 无法按八宫序列推导世应", str(key)))
            continue
        if derived != expected:
            issues.append(_issue("error", "世应", f"{name} 推导世应错误", f"derived={derived} expected={expected}"))
        if by_name != expected:
            issues.append(_issue("error", "世应", f"{name} 名称查询世应错误", f"by_name={by_name} expected={expected}"))
        if table_value and dict(table_value) != expected:
            issues.append(_issue("error", "世应", f"{name} 手写世应表与八宫序列不一致", f"table={table_value} expected={expected}"))

    return issues


def audit_najia_rules():
    """校验纳甲、纳音、六亲与十二长生基础映射。"""
    issues = []
    expected_trigrams = set(NUM_TO_GUA_NAME.values())

    if set(BAGUA_NAJIA) != expected_trigrams:
        issues.append(_issue(
            "error",
            "纳甲",
            "BAGUA_NAJIA 的八卦键不完整",
            f"missing={sorted(expected_trigrams - set(BAGUA_NAJIA))} extra={sorted(set(BAGUA_NAJIA) - expected_trigrams)}",
        ))

    for gua_name, lines in BAGUA_NAJIA.items():
        if len(lines) != 6:
            issues.append(_issue("error", "纳甲", f"{gua_name} 纳甲不是 6 爻", str(lines)))
        if len(set(lines)) != len(lines):
            issues.append(_issue("warning", "纳甲", f"{gua_name} 纳甲存在重复干支", str(lines)))
        for line in lines:
            if len(line) != 2:
                issues.append(_issue("error", "纳甲", f"{gua_name} 出现非法干支长度", line))
                continue
            tiangan, dizhi = line[0], line[1]
            if tiangan not in TIANGAN_ORDER:
                issues.append(_issue("error", "纳甲", f"{gua_name} 出现未知天干", line))
            if dizhi not in VALID_DIZHI:
                issues.append(_issue("error", "纳甲", f"{gua_name} 出现未知地支", line))
            if line not in NAYIN_TABLE:
                issues.append(_issue("error", "纳音", f"{gua_name} 纳甲干支缺少纳音", line))
            changsheng = get_changsheng_for_line(line)
            if changsheng == "未知":
                issues.append(_issue("error", "十二长生", f"{gua_name} 纳甲干支无法推导十二长生", line))

    for upper_num, lower_num in HEXAGRAM_DATA:
        najia_lines = get_najia_all_lines(upper_num, lower_num)
        if len(najia_lines) != 6 or any(line == "未知" for line in najia_lines):
            issues.append(_issue("error", "纳甲", "重卦纳甲生成失败", f"{(upper_num, lower_num)} -> {najia_lines}"))

        palace_wuxing = get_hexagram_palace(upper_num, lower_num).get("palace_wuxing", "")
        liuqin_lines = get_liuqin_all_lines(upper_num, lower_num, palace_wuxing)
        unknown_liuqin = [item for item in liuqin_lines if item not in VALID_LIUQIN]
        if unknown_liuqin:
            issues.append(_issue("error", "六亲", "重卦六亲生成失败", f"{(upper_num, lower_num)} -> {liuqin_lines}"))

    if len(NAYIN_TABLE) != 60:
        issues.append(_issue("error", "纳音", "六十甲子纳音表数量不是 60", str(len(NAYIN_TABLE))))

    return issues


def audit_liushen_rules():
    """校验六神排布基础表。"""
    issues = []
    if len(LIUSHEN_ORDER) != 6 or len(set(LIUSHEN_ORDER)) != 6:
        issues.append(_issue("error", "六神", "LIUSHEN_ORDER 必须是 6 个唯一六神", str(LIUSHEN_ORDER)))
    if set(LIUSHEN_START) != TIANGAN_ORDER:
        issues.append(_issue(
            "error",
            "六神",
            "LIUSHEN_START 必须覆盖十天干",
            f"missing={sorted(TIANGAN_ORDER - set(LIUSHEN_START))} extra={sorted(set(LIUSHEN_START) - TIANGAN_ORDER)}",
        ))
    for gan, index in LIUSHEN_START.items():
        if not isinstance(index, int) or index < 0 or index >= 6:
            issues.append(_issue("error", "六神", f"{gan} 日六神起点非法", str(index)))
    return issues


def audit_hexagram_calibration():
    """校验六十四卦正文与象义校准表。"""
    issues = []
    names = _hexagram_names()

    if len(HEXAGRAM_DATA) != 64:
        issues.append(_issue("error", "六十四卦", "HEXAGRAM_DATA 数量不是 64", str(len(HEXAGRAM_DATA))))
    expected_keys = {(upper, lower) for upper in range(1, 9) for lower in range(1, 9)}
    if set(HEXAGRAM_DATA) != expected_keys:
        issues.append(_issue(
            "error",
            "六十四卦",
            "HEXAGRAM_DATA 未覆盖 8x8 全部卦键",
            f"missing={sorted(expected_keys - set(HEXAGRAM_DATA))} extra={sorted(set(HEXAGRAM_DATA) - expected_keys)}",
        ))

    serials = [detail.get("serial_num") for detail in HEXAGRAM_DATA.values()]
    if set(serials) != set(range(1, 65)):
        issues.append(_issue("error", "六十四卦", "卦序 serial_num 未覆盖 1-64", str(sorted(serials))))

    missing_calibration = names - set(HEXAGRAM_CALIBRATION)
    extra_calibration = set(HEXAGRAM_CALIBRATION) - names
    if missing_calibration:
        issues.append(_issue("error", "象义校准", "缺少卦象校准", "、".join(sorted(missing_calibration))))
    if extra_calibration:
        issues.append(_issue("error", "象义校准", "存在六十四卦以外的校准项", "、".join(sorted(extra_calibration))))

    for name, data in HEXAGRAM_CALIBRATION.items():
        for field in REQUIRED_CALIBRATION_FIELDS:
            if field not in data:
                issues.append(_issue("error", "象义校准", f"{name} 缺少字段 {field}"))
        axis = str(data.get("axis", "")).strip()
        proper_use = str(data.get("proper_use", "")).strip()
        risk = str(data.get("risk", "")).strip()
        keywords = data.get("keywords", [])
        if not axis or "暂缺" in axis:
            issues.append(_issue("error", "象义校准", f"{name} 主轴为空或暂缺"))
        if not proper_use or "暂缺" in proper_use:
            issues.append(_issue("error", "象义校准", f"{name} 宜用为空或暂缺"))
        if not risk or "暂缺" in risk:
            issues.append(_issue("error", "象义校准", f"{name} 风险为空或暂缺"))
        if not isinstance(keywords, list) or len(keywords) < 3:
            issues.append(_issue("warning", "象义校准", f"{name} keywords 少于 3 个", str(keywords)))
        if name in names and "暂缺" in build_calibration_tip(name):
            issues.append(_issue("error", "象义校准", f"{name} 输出提示仍含暂缺"))

    return issues


def audit_method_selector_profiles():
    """校验起卦法选择器配置和几个强规则样例。"""
    issues = []
    required = {"menu", "name", "fit", "basis", "keywords"}
    menus = []
    for key, profile in METHOD_PROFILES.items():
        missing = required - set(profile)
        if missing:
            issues.append(_issue("error", "起卦法选择器", f"{key} profile 缺少字段", "、".join(sorted(missing))))
        if key not in NEGATIVE_HINTS:
            issues.append(_issue("error", "起卦法选择器", f"{key} 缺少边界提示"))
        menus.append(profile.get("menu"))
        if not profile.get("keywords"):
            issues.append(_issue("warning", "起卦法选择器", f"{key} keywords 为空"))
    if len(menus) != len(set(menus)):
        issues.append(_issue("error", "起卦法选择器", "菜单编号存在重复", str(menus)))

    samples = [
        ("我的手机今天不见了，能找回吗", "item"),
        ("今天整体运势怎么样", "daily"),
        ("A方案还是B方案更适合", "decision"),
        ("这个公司名适合吗，按笔画看", "name"),
        ("我想看八字四柱和十神", "bazi"),
        ("这个合同长期合作风险如何", "full"),
        ("现在要不要马上联系他", "quick"),
    ]
    for question, expected_key in samples:
        ranked = recommend_divination_methods(question)
        actual_key = ranked[0]["key"] if ranked else ""
        if actual_key != expected_key:
            issues.append(_issue(
                "error",
                "起卦法选择器",
                "强规则样例推荐不符合预期",
                f"question={question} expected={expected_key} actual={actual_key}",
            ))

    return issues


def audit_bazi_rules():
    """校验八字基础表和十神计算。"""
    issues = []
    if set(GAN_YINYANG) != set(TIANGAN_ORDER):
        issues.append(_issue(
            "error",
            "八字",
            "天干阴阳表未覆盖十天干",
            f"missing={sorted(TIANGAN_ORDER - set(GAN_YINYANG))} extra={sorted(set(GAN_YINYANG) - TIANGAN_ORDER)}",
        ))
    if set(DIZHI_HIDDEN_STEMS) != VALID_DIZHI:
        issues.append(_issue(
            "error",
            "八字",
            "藏干表未覆盖十二地支",
            f"missing={sorted(VALID_DIZHI - set(DIZHI_HIDDEN_STEMS))} extra={sorted(set(DIZHI_HIDDEN_STEMS) - VALID_DIZHI)}",
        ))
    for dizhi, hidden_stems in DIZHI_HIDDEN_STEMS.items():
        weight_sum = round(sum(weight for _, weight in hidden_stems), 2)
        if weight_sum != 1.0:
            issues.append(_issue("warning", "八字", f"{dizhi}藏干权重合计不是1.0", str(weight_sum)))
        for stem, weight in hidden_stems:
            if stem not in TIANGAN_ORDER:
                issues.append(_issue("error", "八字", f"{dizhi}藏干出现未知天干", stem))
            if weight <= 0:
                issues.append(_issue("error", "八字", f"{dizhi}藏干权重必须为正", f"{stem}:{weight}"))

    expected_samples = {
        ("甲", "甲"): "比肩",
        ("甲", "乙"): "劫财",
        ("甲", "癸"): "正印",
        ("甲", "壬"): "偏印",
        ("甲", "丙"): "食神",
        ("甲", "丁"): "伤官",
        ("甲", "己"): "正财",
        ("甲", "戊"): "偏财",
        ("甲", "辛"): "正官",
        ("甲", "庚"): "七杀",
    }
    for args, expected in expected_samples.items():
        actual = get_ten_god(*args)
        if actual != expected:
            issues.append(_issue("error", "八字", "十神样例计算错误", f"{args}: actual={actual} expected={expected}"))

    for god, group in TEN_GOD_GROUP.items():
        if group not in {"印", "食伤", "官杀", "财", "比劫"}:
            issues.append(_issue("error", "八字", f"{god} 十神分组非法", group))

    try:
        result = analyze_bazi_birth("1990-01-01", 8, 30)
        if len(result.get("pillars", [])) != 4 or len(result.get("bazi", "").split()) != 4:
            issues.append(_issue("error", "八字", "八字样例未生成四柱", str(result.get("bazi"))))
    except Exception as exc:
        issues.append(_issue("error", "八字", "八字样例分析失败", str(exc)))

    return issues


def run_rule_audit():
    """运行完整规则审计。"""
    checks = [
        ("八宫矩阵", audit_palace_hexagram_matrix),
        ("世应规则", audit_shi_ying_rules),
        ("纳甲规则", audit_najia_rules),
        ("六神规则", audit_liushen_rules),
        ("六十四卦象义校准", audit_hexagram_calibration),
        ("起卦法选择器", audit_method_selector_profiles),
        ("八字规则", audit_bazi_rules),
    ]
    issues = []
    for _, check in checks:
        issues.extend(check())

    error_count = sum(1 for item in issues if item["level"] == "error")
    warning_count = sum(1 for item in issues if item["level"] == "warning")
    return {
        "passed": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "issue_count": len(issues),
        "issues": issues,
    }


def format_rule_audit_report(audit_result=None):
    """格式化审计报告，适合 CLI 或维护日志输出。"""
    result = audit_result or run_rule_audit()
    status = "通过" if result["passed"] else "未通过"
    lines = [
        f"规则审计：{status}",
        f"错误：{result['error_count']}；警告：{result['warning_count']}",
    ]
    if not result["issues"]:
        lines.append("纳甲、世应、八宫、六十四卦象义校准、八字规则和起卦法选择器配置均已通过一致性校验。")
        return "\n".join(lines)

    for issue in result["issues"]:
        detail = f"｜{issue['detail']}" if issue.get("detail") else ""
        lines.append(f"[{issue['level']}] {issue['area']}：{issue['message']}{detail}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_rule_audit_report())
