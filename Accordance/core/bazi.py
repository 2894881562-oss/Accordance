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
SHICHEN_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
SHICHEN_RANGES = {
    1: "23:00-00:59",
    2: "01:00-02:59",
    3: "03:00-04:59",
    4: "05:00-06:59",
    5: "07:00-08:59",
    6: "09:00-10:59",
    7: "11:00-12:59",
    8: "13:00-14:59",
    9: "15:00-16:59",
    10: "17:00-18:59",
    11: "19:00-20:59",
    12: "21:00-22:59",
}

# 节气月分界近似日期，与 qi_context.get_yueling_by_solar 保持同一套工程近似。
JIE_BOUNDARIES = [
    (1, 6, "小寒", "丑"),
    (2, 4, "立春", "寅"),
    (3, 6, "惊蛰", "卯"),
    (4, 5, "清明", "辰"),
    (5, 6, "立夏", "巳"),
    (6, 6, "芒种", "午"),
    (7, 7, "小暑", "未"),
    (8, 7, "立秋", "申"),
    (9, 8, "白露", "酉"),
    (10, 8, "寒露", "戌"),
    (11, 7, "立冬", "亥"),
    (12, 7, "大雪", "子"),
]


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


def _shift_ganzhi(ganzhi, offset):
    gan = ganzhi[0]
    zhi = ganzhi[1]
    return f"{GAN_ORDER[(GAN_ORDER.index(gan) + offset) % 10]}{SHICHEN_BRANCHES[(SHICHEN_BRANCHES.index(zhi) + offset) % 12]}"


def _normalize_gender(gender):
    text = (gender or "").strip()
    if text.startswith("男"):
        return "男"
    if text.startswith("女"):
        return "女"
    return ""


def _solar_age_years(birth, current):
    years = current.year - birth.year
    if (current.month, current.day, current.hour, current.minute) < (birth.month, birth.day, birth.hour, birth.minute):
        years -= 1
    return max(0, years)


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
        solar = datetime.datetime(year, month, day, hour, minute)
    except (TypeError, ValueError) as exc:
        raise ValueError("出生日期格式应为 YYYY-MM-DD，小时为 0-23，分钟为 0-59") from exc
    if solar.year < 2:
        raise ValueError("出生年份不能早于公元 2 年")
    if solar.date() > datetime.date.today():
        raise ValueError("出生日期不能晚于今天")
    return solar


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


def _ten_god_group(ten_god):
    return TEN_GOD_GROUP.get(ten_god, "")


def _build_useful_profile(day_strength, pattern):
    level = day_strength["level"]
    if level == "偏弱":
        scores = {"印": 1.5, "比劫": 1.2, "食伤": -0.8, "财": -1.0, "官杀": -1.2}
        favorable = ["印", "比劫"]
        caution = ["官杀", "财", "食伤"]
        summary = "日主偏弱，先取印比扶身；官杀、财与食伤会形成压力、耗身或泄身，宜先治理边界。"
    elif level == "偏强":
        scores = {"印": -1.2, "比劫": -1.0, "食伤": 1.4, "财": 1.2, "官杀": 1.0}
        favorable = ["食伤", "财", "官杀"]
        caution = ["印", "比劫"]
        summary = "日主偏强，宜取食伤泄秀、财星落地、官杀立规；印比再来容易加厚停滞。"
    else:
        dominant = pattern.get("dominant_group", "")
        scores = {"印": 0.0, "比劫": 0.0, "食伤": 0.0, "财": 0.0, "官杀": 0.0}
        favorable = []
        caution = [dominant] if dominant else []
        summary = (
            "日主中和，不宜简单定死喜忌；以平衡显著主题为主。"
            f"当前命局显著主题为{dominant or '未定'}，岁运遇之要看是否过量。"
        )
    return {
        "level": level,
        "group_scores": scores,
        "favorable_groups": favorable,
        "caution_groups": caution,
        "summary": summary,
        "principle": "用啥靠啥，治啥得啥；可借力的十神也会消耗自身，需治理的十神也可能转化为成果。",
    }


def _evaluate_timing_gods(gan_ten_god, branch_ten_god, useful_profile):
    scores = useful_profile.get("group_scores", {})
    gan_group = _ten_god_group(gan_ten_god)
    branch_group = _ten_god_group(branch_ten_god)
    score = scores.get(gan_group, 0.0) * 0.55 + scores.get(branch_group, 0.0) * 0.45
    score = round(score, 2)

    if score >= 1.0:
        label = "较可用"
        tip = "岁运主题与当前取向相合，可借力推进，但仍需现实落地。"
    elif score >= 0.25:
        label = "可借力"
        tip = "有可用之处，但需要主动筛选条件，避免过度依赖。"
    elif score <= -1.0:
        label = "压力偏重"
        tip = "岁运主题对当前结构形成明显压力，宜先降风险、立边界。"
    elif score <= -0.25:
        label = "需治理"
        tip = "主题并非不能用，但要先治理过量、耗身或牵制。"
    else:
        label = "中性"
        tip = "岁运主题偏中性，关键看现实选择、资源配置和节奏。"

    return {
        "gan_group": gan_group,
        "branch_group": branch_group,
        "score": score,
        "label": label,
        "tip": tip,
        "summary": (
            f"天干{gan_ten_god}属{gan_group or '未知'}，地支主气{branch_ten_god}属{branch_group or '未知'}；"
            f"岁运取向评分{score:+.2f}，判断为{label}。{tip}"
        ),
    }


def _nearest_jie_boundary(solar, forward=True):
    candidates = []
    for year in (solar.year - 1, solar.year, solar.year + 1):
        for month, day, name, branch in JIE_BOUNDARIES:
            candidates.append({
                "datetime": datetime.datetime(year, month, day),
                "name": name,
                "branch": branch,
            })
    candidates.sort(key=lambda item: item["datetime"])

    if forward:
        for item in candidates:
            if item["datetime"] > solar:
                return item
        return candidates[-1]

    previous = candidates[0]
    for item in candidates:
        if item["datetime"] <= solar:
            previous = item
        else:
            break
    return previous


def _build_luck_direction(year_gan, gender):
    normalized = _normalize_gender(gender)
    if not normalized:
        return {
            "gender": "未指定",
            "direction": "未定",
            "step": 0,
            "reason": "未指定性别，暂不判定大运顺逆；输入男/女后可按阳男阴女顺、阴男阳女逆推大运。",
        }

    year_is_yang = GAN_YINYANG.get(year_gan) == "阳"
    forward = (normalized == "男" and year_is_yang) or (normalized == "女" and not year_is_yang)
    return {
        "gender": normalized,
        "direction": "顺行" if forward else "逆行",
        "step": 1 if forward else -1,
        "reason": (
            f"年干{year_gan}属{'阳' if year_is_yang else '阴'}，"
            f"{normalized}命按{'阳男阴女顺' if forward else '阴男阳女逆'}取{('顺行' if forward else '逆行')}。"
        ),
    }


def _build_luck_cycles(solar, pillars, day_gan, gender, useful_profile, current=None, limit=8):
    year_gan = pillars[0]["gan"]
    month_ganzhi = pillars[1]["ganzhi"]
    direction = _build_luck_direction(year_gan, gender)
    step = direction["step"]
    if step == 0:
        return {
            "direction": direction,
            "start_age": None,
            "start_boundary": "",
            "cycles": [],
            "current_cycle": None,
            "summary": direction["reason"],
        }

    boundary = _nearest_jie_boundary(solar, forward=step > 0)
    delta_days = abs((boundary["datetime"] - solar).total_seconds()) / 86400
    start_age = round(delta_days / 3, 1)
    current_dt = current or datetime.datetime.now()
    current_age = _solar_age_years(solar, current_dt)
    cycles = []
    current_cycle = None

    for index in range(limit):
        offset = step * (index + 1)
        ganzhi = _shift_ganzhi(month_ganzhi, offset)
        age_start = round(start_age + index * 10, 1)
        age_end = round(age_start + 10, 1)
        gan_god = get_ten_god(day_gan, ganzhi[0])
        hidden = DIZHI_HIDDEN_STEMS.get(ganzhi[1], [])
        branch_god = get_ten_god(day_gan, hidden[0][0]) if hidden else "未知"
        timing_eval = _evaluate_timing_gods(gan_god, branch_god, useful_profile)
        cycle = {
            "index": index + 1,
            "ganzhi": ganzhi,
            "age_start": age_start,
            "age_end": age_end,
            "calendar_start_year": int(solar.year + age_start),
            "calendar_end_year": int(solar.year + age_end),
            "gan_ten_god": gan_god,
            "branch_main_ten_god": branch_god,
            "useful_evaluation": timing_eval,
            "summary": f"{age_start}-{age_end}岁：{ganzhi}大运，天干{gan_god}，地支主气{branch_god}。",
        }
        if age_start <= current_age < age_end:
            current_cycle = cycle
        cycles.append(cycle)

    return {
        "direction": direction,
        "start_age": start_age,
        "start_boundary": f"{boundary['name']}({boundary['datetime'].strftime('%Y-%m-%d')})",
        "cycles": cycles,
        "current_cycle": current_cycle,
        "summary": (
            f"{direction['reason']} 起运按出生至{boundary['name']}约{delta_days:.1f}天折算，"
            f"约{start_age}岁起运。"
        ),
    }


def _build_current_year_analysis(solar, day_gan, useful_profile, current=None):
    current_dt = current or datetime.datetime.now()
    year_ganzhi = get_year_ganzhi_by_date(current_dt)
    hidden = DIZHI_HIDDEN_STEMS.get(year_ganzhi[1], [])
    hidden_text = "、".join(f"{stem}{get_ten_god(day_gan, stem)}" for stem, _ in hidden)
    gan_god = get_ten_god(day_gan, year_ganzhi[0])
    main_branch_god = get_ten_god(day_gan, hidden[0][0]) if hidden else "未知"
    timing_eval = _evaluate_timing_gods(gan_god, main_branch_god, useful_profile)
    age = _solar_age_years(solar, current_dt)
    return {
        "year": current_dt.year,
        "age": age,
        "ganzhi": year_ganzhi,
        "gan_ten_god": gan_god,
        "branch_main_ten_god": main_branch_god,
        "hidden_ten_gods": hidden_text,
        "useful_evaluation": timing_eval,
        "summary": (
            f"{current_dt.year}年流年{year_ganzhi}，天干为{gan_god}，"
            f"地支主气为{main_branch_god}；当前约{age}岁。"
        ),
    }


def _build_current_timing_analysis(luck_cycles, current_year):
    current_cycle = luck_cycles.get("current_cycle")
    year_eval = current_year.get("useful_evaluation", {})
    if not current_cycle:
        return {
            "combined_score": year_eval.get("score", 0),
            "level": "流年单看",
            "summary": f"当前未定位到大运，仅看流年：{year_eval.get('summary', '')}",
            "action_tip": year_eval.get("tip", ""),
            "details": [year_eval.get("summary", "")],
        }

    cycle_eval = current_cycle.get("useful_evaluation", {})
    combined = round(cycle_eval.get("score", 0) * 0.65 + year_eval.get("score", 0) * 0.35, 2)
    if combined >= 0.9:
        level = "岁运可用"
        action = "当前大运与流年总体可借力，宜把优势落实为计划、交付和资源配置。"
    elif combined >= 0.2:
        level = "有用有压"
        action = "当前岁运有可用处，也有牵制点，宜小步推进并保持复盘。"
    elif combined <= -0.9:
        level = "压力偏重"
        action = "当前岁运压力较重，宜先守底线、降杠杆、稳健康与关系边界。"
    elif combined <= -0.2:
        level = "先治后用"
        action = "当前岁运需先治理过量或耗身之处，再把压力转成成果。"
    else:
        level = "中性待用"
        action = "当前岁运不偏一端，关键在现实判断、节奏控制和持续执行。"

    return {
        "combined_score": combined,
        "level": level,
        "summary": (
            f"当前大运{current_cycle['ganzhi']}为{cycle_eval.get('label', '未评估')}，"
            f"流年{current_year['ganzhi']}为{year_eval.get('label', '未评估')}；"
            f"岁运合看评分{combined:+.2f}，判断为{level}。"
        ),
        "action_tip": action,
        "details": [
            f"大运：{cycle_eval.get('summary', '')}",
            f"流年：{year_eval.get('summary', '')}",
        ],
    }


def _shichen_range(num):
    return SHICHEN_RANGES.get(num, "")


def _build_hour_candidate(day_gan, shichen_num, label, selected=False):
    ganzhi = get_shichen_ganzhi(day_gan, shichen_num)
    ten_god = get_ten_god(day_gan, ganzhi[0])
    return {
        "label": label,
        "shichen_num": shichen_num,
        "range": _shichen_range(shichen_num),
        "ganzhi": ganzhi,
        "ten_god": ten_god,
        "trait": TEN_GOD_TRAITS.get(ten_god, ""),
        "selected": selected,
        "summary": f"{label}{_shichen_range(shichen_num)}：{ganzhi}时，时干{ten_god}，{TEN_GOD_TRAITS.get(ten_god, '')}",
    }


def _current_shichen_window(solar, shichen_num):
    start_hour = (2 * (shichen_num - 1) - 1) % 24
    start = solar.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if shichen_num == 1 and solar.hour < 1:
        start -= datetime.timedelta(days=1)
    if start > solar:
        start -= datetime.timedelta(days=1)
    end = start + datetime.timedelta(hours=2)
    return start, end


def _build_hour_candidates(solar, day_gan):
    shichen_num = get_shichen_by_hour(solar.hour)
    previous_num = 12 if shichen_num == 1 else shichen_num - 1
    next_num = 1 if shichen_num == 12 else shichen_num + 1
    start, end = _current_shichen_window(solar, shichen_num)
    distance = min(
        abs((solar - start).total_seconds()) / 60,
        abs((end - solar).total_seconds()) / 60,
    )
    candidates = [
        _build_hour_candidate(day_gan, previous_num, "前一时辰"),
        _build_hour_candidate(day_gan, shichen_num, "当前采用", selected=True),
        _build_hour_candidate(day_gan, next_num, "后一时辰"),
    ]
    return {
        "current_shichen": SHICHEN_BRANCHES[shichen_num - 1],
        "distance_to_boundary_minutes": round(distance, 1),
        "is_near_boundary": distance <= 20,
        "candidates": candidates,
        "summary": (
            f"当前按{SHICHEN_BRANCHES[shichen_num - 1]}时({_shichen_range(shichen_num)})取时柱。"
            f"距最近时辰边界约{distance:.1f}分钟；"
            f"{'接近边界，可重点对照前后时干气质。' if distance <= 20 else '不接近边界，时辰争议相对较小。'}"
        ),
    }


def _build_plain_conclusion(day_strength, pattern, current_timing=None):
    timing = ""
    if current_timing:
        timing = f"岁运同参为{current_timing['level']}。"
    return (
        f"日主为{day_strength['day_gan']}{day_strength['day_element']}，"
        f"按当前简化评分属{day_strength['level']}。"
        f"格局倾向为{pattern['pattern']}：{pattern['strategy']}"
        f"{timing}"
        "此结果适合做自我观察和关系结构整理，不替代现实选择。"
    )


def analyze_bazi_birth(birth_date, birth_hour, birth_minute=0, gender: Optional[str] = "", current=None):
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
    useful_profile = _build_useful_profile(day_strength, pattern)
    stages = _build_stage_analysis(pillars)
    inner_outer = _build_inner_outer_analysis(pillars)
    relationship_notes = _build_relationship_notes(ten_god_counts["groups"])
    luck_cycles = _build_luck_cycles(solar, pillars, day_gan, gender, useful_profile, current=current)
    current_year = _build_current_year_analysis(solar, day_gan, useful_profile, current=current)
    current_timing = _build_current_timing_analysis(luck_cycles, current_year)
    hour_candidates = _build_hour_candidates(solar, day_gan)

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
        "useful_profile": useful_profile,
        "luck_cycles": luck_cycles,
        "current_year": current_year,
        "current_timing_analysis": current_timing,
        "hour_candidates": hour_candidates,
        "relationship_notes": relationship_notes,
        "plain_conclusion": _build_plain_conclusion(day_strength, pattern, current_timing),
        "boundary_note": (
            "本功能按公历生日、近似节气分界排四柱；年柱以2月4日近似立春，"
            "月柱按节气月建近似，大运起运按近似节气折算，未精确到节气时分，也未细分晚子时换日流派。"
        ),
    }


def format_bazi_report(result: Dict[str, Any], include_plain_conclusion=True):
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
    lines.append("【喜忌取向】")
    useful = result["useful_profile"]
    lines.append(useful["summary"])
    lines.append(f"可借力：{'、'.join(useful['favorable_groups']) or '不固定'}；需治理：{'、'.join(useful['caution_groups']) or '不固定'}。")
    lines.append(useful["principle"])
    lines.append("")
    lines.append("【岁运同参】")
    timing = result["current_timing_analysis"]
    lines.append(timing["summary"])
    lines.append(timing["action_tip"])
    for detail in timing["details"]:
        if detail:
            lines.append(detail)
    lines.append("")
    lines.append("【大运流年】")
    luck = result["luck_cycles"]
    lines.append(luck["summary"])
    for cycle in luck.get("cycles", [])[:8]:
        current_mark = " ← 当前" if luck.get("current_cycle") and cycle["index"] == luck["current_cycle"]["index"] else ""
        eval_text = cycle.get("useful_evaluation", {}).get("label", "")
        lines.append(f"{cycle['summary']}约{cycle['calendar_start_year']}-{cycle['calendar_end_year']}年。{eval_text}{current_mark}")
    current_year = result["current_year"]
    lines.append(current_year["summary"])
    lines.append("")
    lines.append("【临界时辰对照】")
    hour_info = result["hour_candidates"]
    lines.append(hour_info["summary"])
    for candidate in hour_info["candidates"]:
        marker = "（当前采用）" if candidate["selected"] else ""
        lines.append(f"{candidate['summary']}{marker}")
    lines.append("")
    lines.append("【关系双向性】")
    lines.extend(result["relationship_notes"])
    lines.append("")
    if include_plain_conclusion:
        lines.append(f"【简短结论】{result['plain_conclusion']}")
    lines.append(f"【边界】{result['boundary_note']}")
    return "\n".join(lines)
