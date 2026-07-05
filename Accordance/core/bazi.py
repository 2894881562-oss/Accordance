# -*- coding: utf-8 -*-
"""四柱八字基础分析引擎。

定位：提供可读、可审的命理结构整理，重点在四柱、十神、五行关系、
阶段提示与格局倾向。算法使用现有节气近似模块，不做精确节气时分排盘。
"""

import datetime
from typing import Any, Dict, List, Optional

from config.bazi_data import (
    DIZHI_HIDDEN_STEMS,
    GAN_ORDER,
    GAN_YINYANG,
    MONTH_BRANCH_ORDER,
    MONTH_START_GAN,
    PATTERN_GROUP_LABEL,
    RELATIONSHIP_DUALITY,
    STAGE_RANGES,
    TEN_GOD_GROUP,
    TEN_GOD_MEANING,
    TEN_GOD_TRAITS,
)
from config.wuxing_rules import DIZHI_WUXING, TIANGAN_WUXING, WUXING_KE, WUXING_SHENG, WUXING_WANG_SHUAI
from core.qi_context import (
    get_accurate_day_ganzhi,
    get_season_by_yueling,
    get_shichen_by_hour,
    get_shichen_ganzhi,
    get_year_ganzhi_by_date,
    get_yueling_by_solar,
)


PILLAR_NAMES = ["年柱", "月柱", "日柱", "时柱"]
ELEMENTS = ["木", "火", "土", "金", "水"]


def _source_element(target_element):
    for source, target in WUXING_SHENG.items():
        if target == target_element:
            return source
    return "土"


def _ke_source_element(target_element):
    for source, target in WUXING_KE.items():
        if target == target_element:
            return source
    return "土"


def calculate_month_ganzhi(solar):
    """按节气月建和五虎遁近似计算月柱。"""
    year_ganzhi = get_year_ganzhi_by_date(solar)
    year_gan = year_ganzhi[0]
    month_branch = get_yueling_by_solar(solar)
    start_gan = MONTH_START_GAN.get(year_gan, "丙")
    offset = MONTH_BRANCH_ORDER.index(month_branch)
    month_gan = GAN_ORDER[(GAN_ORDER.index(start_gan) + offset) % 10]
    return f"{month_gan}{month_branch}"


def parse_birth_datetime(birth_date, birth_hour, birth_minute=0):
    """解析公历出生日期时间。"""
    if not birth_date:
        raise ValueError("八字分析需要填写公历出生日期")
    if birth_hour is None:
        raise ValueError("八字分析需要填写出生小时（0-23）")

    try:
        year, month, day = [int(part) for part in str(birth_date).split("-")]
        hour = int(birth_hour)
        minute = int(birth_minute or 0)
        return datetime.datetime(year, month, day, hour, minute)
    except (TypeError, ValueError) as exc:
        raise ValueError("出生日期格式应为 YYYY-MM-DD，小时为 0-23，分钟为 0-59") from exc


def get_ten_god(day_gan, target_gan):
    """以日干为中心计算目标天干的十神。"""
    if target_gan == day_gan:
        return "比肩"

    day_element = TIANGAN_WUXING.get(day_gan)
    target_element = TIANGAN_WUXING.get(target_gan)
    if not day_element or not target_element:
        return "未知"

    same_yinyang = GAN_YINYANG.get(day_gan) == GAN_YINYANG.get(target_gan)

    if target_element == day_element:
        return "比肩" if same_yinyang else "劫财"
    if WUXING_SHENG.get(target_element) == day_element:
        return "偏印" if same_yinyang else "正印"
    if WUXING_SHENG.get(day_element) == target_element:
        return "食神" if same_yinyang else "伤官"
    if WUXING_KE.get(target_element) == day_element:
        return "七杀" if same_yinyang else "正官"
    if WUXING_KE.get(day_element) == target_element:
        return "偏财" if same_yinyang else "正财"

    return "未知"


def build_four_pillars(solar):
    """生成四柱干支。"""
    year_ganzhi = get_year_ganzhi_by_date(solar)
    month_ganzhi = calculate_month_ganzhi(solar)
    day_ganzhi = get_accurate_day_ganzhi(solar)
    shichen_num = get_shichen_by_hour(solar.hour)
    hour_ganzhi = get_shichen_ganzhi(day_ganzhi[0], shichen_num)

    return [
        {"name": "年柱", "ganzhi": year_ganzhi},
        {"name": "月柱", "ganzhi": month_ganzhi},
        {"name": "日柱", "ganzhi": day_ganzhi},
        {"name": "时柱", "ganzhi": hour_ganzhi},
    ]


def _enrich_pillar(pillar, day_gan):
    gan = pillar["ganzhi"][0]
    zhi = pillar["ganzhi"][1]
    stem_god = "日主" if pillar["name"] == "日柱" else get_ten_god(day_gan, gan)
    hidden = []
    for hidden_gan, weight in DIZHI_HIDDEN_STEMS.get(zhi, []):
        hidden.append({
            "stem": hidden_gan,
            "weight": weight,
            "element": TIANGAN_WUXING.get(hidden_gan, ""),
            "ten_god": get_ten_god(day_gan, hidden_gan),
        })

    main_hidden = hidden[0] if hidden else {}
    core_god = stem_god if stem_god != "日主" else main_hidden.get("ten_god", "日主")
    return {
        **pillar,
        "gan": gan,
        "zhi": zhi,
        "gan_element": TIANGAN_WUXING.get(gan, ""),
        "zhi_element": DIZHI_WUXING.get(zhi, ""),
        "gan_yinyang": GAN_YINYANG.get(gan, ""),
        "stem_ten_god": stem_god,
        "hidden_stems": hidden,
        "core_ten_god": core_god,
    }


def _build_element_balance(pillars):
    balance = {element: 0.0 for element in ELEMENTS}
    for pillar in pillars:
        gan_element = pillar.get("gan_element")
        if gan_element in balance:
            balance[gan_element] += 1.0
        for hidden in pillar.get("hidden_stems", []):
            element = hidden.get("element")
            if element in balance:
                balance[element] += float(hidden.get("weight", 0))

    return {key: round(value, 2) for key, value in balance.items()}


def _build_ten_god_counts(pillars):
    counts: Dict[str, float] = {}
    group_counts = {"印": 0.0, "食伤": 0.0, "官杀": 0.0, "财": 0.0, "比劫": 0.0}

    for pillar in pillars:
        stem_god = pillar.get("stem_ten_god")
        if stem_god and stem_god != "日主":
            counts[stem_god] = counts.get(stem_god, 0.0) + 1.0
            group = TEN_GOD_GROUP.get(stem_god)
            if group:
                group_counts[group] += 1.0
        for hidden in pillar.get("hidden_stems", []):
            god = hidden.get("ten_god")
            weight = float(hidden.get("weight", 0))
            counts[god] = counts.get(god, 0.0) + weight
            group = TEN_GOD_GROUP.get(god)
            if group:
                group_counts[group] += weight

    return {
        "ten_gods": {key: round(value, 2) for key, value in sorted(counts.items(), key=lambda item: item[0])},
        "groups": {key: round(value, 2) for key, value in group_counts.items()},
    }


def _analyze_day_master(day_gan, yueling, element_balance):
    day_element = TIANGAN_WUXING.get(day_gan, "土")
    season = get_season_by_yueling(yueling)
    season_status = WUXING_WANG_SHUAI.get(season, {}).get(day_element, "平")
    season_score = {
        "旺": 1.8,
        "相": 1.2,
        "休": 0.0,
        "囚": -0.8,
        "死": -1.2,
        "平": 0.0,
    }.get(season_status, 0.0)

    source = _source_element(day_element)
    output = WUXING_SHENG.get(day_element, day_element)
    wealth = WUXING_KE.get(day_element, day_element)
    officer = _ke_source_element(day_element)

    support_score = element_balance.get(day_element, 0) + element_balance.get(source, 0) * 0.9
    pressure_score = (
        element_balance.get(output, 0) * 0.75
        + element_balance.get(wealth, 0) * 0.8
        + element_balance.get(officer, 0) * 1.0
    )
    score = round(support_score - pressure_score + season_score, 2)

    if score >= 2.5:
        level = "偏强"
        advice = "宜让才华、责任和资源流动起来，避免印比过厚造成停滞。"
    elif score <= -2.0:
        level = "偏弱"
        advice = "宜先补印比根基，重学习、同伴、休整与稳定资源，不宜硬扛压力。"
    else:
        level = "中和"
        advice = "宜看具体十神组合取平衡，不必简单按强弱二分。"

    return {
        "day_gan": day_gan,
        "day_element": day_element,
        "yueling": yueling,
        "season": season,
        "season_status": season_status,
        "support_score": round(support_score, 2),
        "pressure_score": round(pressure_score, 2),
        "score": score,
        "level": level,
        "advice": advice,
    }


def _format_hidden(hidden_stems):
    return "、".join(
        f"{item['stem']}{item['ten_god']}({item['weight']:.1f})"
        for item in hidden_stems
    )


def _build_stage_analysis(pillars):
    stages = []
    for pillar in pillars:
        name = pillar["name"]
        core_god = pillar.get("core_ten_god", "日主")
        stages.append({
            "pillar": name,
            "age_range": STAGE_RANGES[name],
            "core_ten_god": core_god,
            "summary": (
                f"{name}主{STAGE_RANGES[name]}，核心十神取{core_god}。"
                f"{TEN_GOD_MEANING.get(core_god, '需结合全局判断')}"
            ),
        })
    return stages


def _build_inner_outer_analysis(pillars):
    year = next(item for item in pillars if item["name"] == "年柱")
    hour = next(item for item in pillars if item["name"] == "时柱")
    year_god = year.get("stem_ten_god", "")
    hour_god = hour.get("stem_ten_god", "")
    return {
        "inner": {
            "pillar": year["ganzhi"],
            "ten_god": year_god,
            "trait": TEN_GOD_TRAITS.get(year_god, ""),
        },
        "outer": {
            "pillar": hour["ganzhi"],
            "ten_god": hour_god,
            "trait": TEN_GOD_TRAITS.get(hour_god, ""),
        },
        "summary": (
            f"年干{year['gan']}为{year_god}，可作深层驱动力参考：{TEN_GOD_TRAITS.get(year_god, '')}"
            f"时干{hour['gan']}为{hour_god}，可作外在呈现参考：{TEN_GOD_TRAITS.get(hour_god, '')}"
            "此法只适合作辅助观察，尤其不能单独反推出生时辰。"
        ),
    }


def _build_pattern_analysis(day_strength, ten_god_counts):
    groups = ten_god_counts["groups"]
    dominant_group, dominant_score = max(groups.items(), key=lambda item: item[1])
    strength_level = day_strength["level"]
    label = PATTERN_GROUP_LABEL.get(dominant_group, dominant_group)

    if strength_level == "偏强":
        if dominant_group in ("印", "比劫"):
            pattern = f"治{label}"
            strategy = f"{dominant_group}偏重且日主不弱，宜用输出、责任或资源配置来疏导，避免只靠自身或庇护。"
        else:
            pattern = f"用{label}"
            strategy = f"日主能承载{dominant_group}，可把它作为发展抓手。用啥靠啥，靠的是{dominant_group}对应的人事物。"
    elif strength_level == "偏弱":
        if dominant_group in ("印", "比劫"):
            pattern = f"用{label}"
            strategy = f"日主偏弱，{dominant_group}能补身，可先靠学习、支持系统或同伴根基。"
        else:
            pattern = f"治{label}"
            strategy = f"{dominant_group}形成压力或消耗，宜先降压、立边界、补根基，再谈发挥。治啥得啥，先能驾驭才谈取得。"
    else:
        pattern = f"调{label}"
        strategy = f"日主中和，{dominant_group}为显著主题，重点在平衡使用与约束，不宜只取治或只取用。"

    top_gods = sorted(
        ten_god_counts["ten_gods"].items(),
        key=lambda item: item[1],
        reverse=True,
    )[:3]

    return {
        "dominant_group": dominant_group,
        "dominant_score": round(dominant_score, 2),
        "pattern": pattern,
        "strategy": strategy,
        "top_ten_gods": top_gods,
        "note": "格局这里只给工程化倾向，不做传统命局定格的最终裁断。",
    }


def _build_relationship_notes(groups):
    ordered = sorted(groups.items(), key=lambda item: item[1], reverse=True)
    notes = []
    for group, score in ordered:
        if score <= 0:
            continue
        notes.append(f"{group}({score:.1f})：{RELATIONSHIP_DUALITY[group]}")
    return notes


def _build_plain_conclusion(day_strength, pattern):
    return (
        f"日主为{day_strength['day_gan']}{day_strength['day_element']}，"
        f"按当前简化评分属{day_strength['level']}。"
        f"格局倾向为{pattern['pattern']}：{pattern['strategy']}"
        "此结果适合做自我观察和关系结构整理，不替代现实选择。"
    )


def analyze_bazi_birth(birth_date, birth_hour, birth_minute=0, gender: Optional[str] = ""):
    """按公历出生日期时间生成八字结构分析。"""
    solar = parse_birth_datetime(birth_date, birth_hour, birth_minute)
    raw_pillars = build_four_pillars(solar)
    day_gan = raw_pillars[2]["ganzhi"][0]
    pillars = [_enrich_pillar(pillar, day_gan) for pillar in raw_pillars]
    yueling = get_yueling_by_solar(solar)
    element_balance = _build_element_balance(pillars)
    ten_god_counts = _build_ten_god_counts(pillars)
    day_strength = _analyze_day_master(day_gan, yueling, element_balance)
    pattern = _build_pattern_analysis(day_strength, ten_god_counts)
    stages = _build_stage_analysis(pillars)
    inner_outer = _build_inner_outer_analysis(pillars)
    relationship_notes = _build_relationship_notes(ten_god_counts["groups"])

    return {
        "birth": {
            "date": solar.strftime("%Y-%m-%d"),
            "time": solar.strftime("%H:%M"),
            "gender": gender or "未指定",
            "calendar": "公历",
        },
        "pillars": pillars,
        "bazi": " ".join(item["ganzhi"] for item in pillars),
        "day_master": day_strength,
        "element_balance": element_balance,
        "ten_god_counts": ten_god_counts,
        "stage_analysis": stages,
        "inner_outer": inner_outer,
        "pattern_analysis": pattern,
        "relationship_notes": relationship_notes,
        "plain_conclusion": _build_plain_conclusion(day_strength, pattern),
        "boundary_note": (
            "本功能按公历生日、近似节气分界排四柱；年柱以2月4日近似立春，"
            "月柱按节气月建近似，未精确到节气时分，也未细分晚子时换日流派。"
        ),
    }


def format_bazi_report(result: Dict[str, Any]):
    """格式化 CLI 报告。"""
    lines: List[str] = []
    lines.append(f"八字：{result['bazi']}")
    lines.append(f"出生：{result['birth']['date']} {result['birth']['time']}（{result['birth']['calendar']}）")
    lines.append("")
    lines.append("【四柱十神】")
    for pillar in result["pillars"]:
        hidden = _format_hidden(pillar["hidden_stems"])
        lines.append(
            f"{pillar['name']} {pillar['ganzhi']}：天干{pillar['gan']}{pillar['stem_ten_god']}，"
            f"地支{pillar['zhi']}藏干[{hidden}]"
        )
    lines.append("")
    lines.append("【日主强弱】")
    dm = result["day_master"]
    lines.append(
        f"日主{dm['day_gan']}{dm['day_element']}，月令{dm['yueling']}，季节状态{dm['season_status']}；"
        f"扶身{dm['support_score']}，耗克{dm['pressure_score']}，综合{dm['score']}，判断{dm['level']}。{dm['advice']}"
    )
    lines.append("")
    lines.append("【阶段提示】")
    for stage in result["stage_analysis"]:
        lines.append(stage["summary"])
    lines.append("")
    lines.append("【内外气质】")
    lines.append(result["inner_outer"]["summary"])
    lines.append("")
    lines.append("【格局倾向】")
    pattern = result["pattern_analysis"]
    lines.append(f"{pattern['pattern']}：{pattern['strategy']}{pattern['note']}")
    lines.append("")
    lines.append("【关系双向性】")
    lines.extend(result["relationship_notes"])
    lines.append("")
    lines.append(f"【简短结论】{result['plain_conclusion']}")
    lines.append(f"【边界】{result['boundary_note']}")
    return "\n".join(lines)
