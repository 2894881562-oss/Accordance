# -*- coding: utf-8 -*-
"""传统奇门运筹分析骨架。

定位：提供可读、可审的奇门方位/时机/格局参考。当前实现不是完整
拆补、置闰、超接、符使飞布的专业排盘器，而是先把工程内缺失的
奇门数据结构、九宫盘和现实运筹逻辑搭起来。
"""

import datetime
from typing import Any, Dict, List, Optional

from config.qimen_data import (
    EIGHT_DOOR_ORDER,
    EIGHT_DOORS,
    EIGHT_GOD_ORDER,
    EIGHT_GODS,
    FENGHOU_QIMEN_BOUNDARY,
    NINE_STAR_ORDER,
    NINE_STARS,
    OUTER_PALACE_KEYS,
    QIMEN_PALACES,
    QIMEN_SCENARIO_RULES,
    QIMEN_STEM_MEANING,
    QIMEN_STEM_ORDER,
    TRADITIONAL_QIMEN_BOUNDARY,
)
from config.wuxing_rules import DIZHI_ORDER, WUXING_KE, WUXING_SHENG
from core.qi_context import (
    JIAZI_TABLE,
    get_accurate_day_ganzhi,
    get_day_tiangan,
    get_shichen_by_hour,
    get_shichen_ganzhi,
    get_xunkong,
    get_yueling_by_solar,
    text_to_seed,
)


DIRECTION_NAMES = ["东北", "东南", "西北", "西南", "北", "南", "东", "西", "中"]
SCENARIO_ALIASES = {
    "谈判": "negotiation",
    "协商": "negotiation",
    "竞争": "competition",
    "对峙": "competition",
    "财务": "wealth",
    "财富": "wealth",
    "资源": "wealth",
    "出行": "travel",
    "方位": "travel",
    "事业": "career",
    "工作": "career",
    "学习": "study",
    "文书": "study",
    "健康": "health",
    "综合": "general",
}


def normalize_direction(direction: str = "") -> str:
    """把用户输入的方向规范为八方或中。"""
    text = (direction or "").strip()
    if not text:
        return ""
    for suffix in ("方向", "方位", "方", "位", "正"):
        text = text.replace(suffix, "")
    for name in DIRECTION_NAMES:
        if name in text:
            return name
    return ""


def _rotate(values, shift, reverse=False):
    items = list(reversed(values)) if reverse else list(values)
    shift = shift % len(items)
    return items[shift:] + items[:shift]


def _dun_type(solar):
    # 近似以夏至、冬至为阴阳遁分界。
    after_summer = (solar.month, solar.day) >= (6, 21)
    before_winter = (solar.month, solar.day) < (12, 22)
    return "阴遁" if after_summer and before_winter else "阳遁"


def _ju_number(solar, day_index, shichen_num):
    yueling = get_yueling_by_solar(solar)
    month_index = DIZHI_ORDER.index(yueling) if yueling in DIZHI_ORDER else 0
    base = (day_index + shichen_num + month_index) % 9 + 1
    if _dun_type(solar) == "阴遁":
        return 10 - base
    return base


def _infer_scenario(topic="", mode=""):
    text = f"{topic or ''} {mode or ''}".strip()
    normalized_mode = (mode or "").strip().lower()
    if normalized_mode in QIMEN_SCENARIO_RULES:
        key = normalized_mode
        return {
            "key": key,
            "name": QIMEN_SCENARIO_RULES[key]["name"],
            "hits": [],
            "action": QIMEN_SCENARIO_RULES[key]["action"],
        }

    for alias, key in SCENARIO_ALIASES.items():
        if alias in text:
            rule = QIMEN_SCENARIO_RULES[key]
            return {"key": key, "name": rule["name"], "hits": [alias], "action": rule["action"]}

    scored = []
    for key, rule in QIMEN_SCENARIO_RULES.items():
        hits = [word for word in rule["keywords"] if word in text]
        if hits:
            scored.append((len(hits), key, hits))
    if scored:
        scored.sort(reverse=True)
        _, key, hits = scored[0]
    else:
        key, hits = "general", []

    rule = QIMEN_SCENARIO_RULES[key]
    return {"key": key, "name": rule["name"], "hits": hits, "action": rule["action"]}


def _relation_score(palace_element, door_element):
    if not palace_element or not door_element:
        return 0.0
    if palace_element == door_element:
        return 0.4
    if WUXING_SHENG.get(door_element) == palace_element:
        return 0.5
    if WUXING_SHENG.get(palace_element) == door_element:
        return 0.2
    if WUXING_KE.get(palace_element) == door_element:
        return -0.4
    if WUXING_KE.get(door_element) == palace_element:
        return -0.2
    return 0.0


def _scenario_modifier(door_name, star_name, god_name, scenario_key):
    rule = QIMEN_SCENARIO_RULES.get(scenario_key, QIMEN_SCENARIO_RULES["general"])
    score = 0.0
    reasons = []
    if door_name in rule["prefer_doors"]:
        score += 1.2
        reasons.append(f"{door_name}门合{rule['name']}")
    if door_name in rule["avoid_doors"]:
        score -= 1.3
        reasons.append(f"{door_name}门不利{rule['name']}")
    if star_name in rule["prefer_stars"]:
        score += 0.8
        reasons.append(f"{star_name}合主题")
    if star_name in rule["avoid_stars"]:
        score -= 0.8
        reasons.append(f"{star_name}需防")
    if god_name in rule["prefer_gods"]:
        score += 0.8
        reasons.append(f"{god_name}助局")
    if god_name in rule["avoid_gods"]:
        score -= 0.8
        reasons.append(f"{god_name}添险")
    return score, reasons


def _score_level(score):
    if score >= 5:
        return "大吉可用"
    if score >= 3:
        return "吉"
    if score >= 1:
        return "平中可用"
    if score >= -1:
        return "慎用"
    return "宜避"


def _action_tip(palace, door_name, star_name, god_name, score, scenario, is_current=False):
    if palace["key"] == "center":
        return "中宫只看统筹，不作单独出行或站位方位。"

    door = EIGHT_DOORS[door_name]
    star = NINE_STARS[star_name]
    god = EIGHT_GODS[god_name]
    direction = palace["direction"]
    prefix = f"{direction}方"

    if score >= 3:
        tip = f"{prefix}可作为主动切入方：{door['strategy']}星取{star['meaning']}神取{god['meaning']}"
    elif score >= 1:
        tip = f"{prefix}可作辅助方位：先按{door_name}门之象小步试探，再用现实反馈确认。"
    elif score >= -1:
        tip = f"{prefix}只宜谨慎使用：{door_name}门提示{door['meaning']}，行动前要补足信息。"
    else:
        tip = f"{prefix}不宜作为主动突破口：{door_name}门、{star_name}、{god_name}组合阻力偏重。"

    if is_current:
        tip += "若当前已在此方位，宜先调节节奏或换成推荐方位承接关键动作。"
    return tip


def _build_time_context(solar):
    day_ganzhi = get_accurate_day_ganzhi(solar)
    day_index = JIAZI_TABLE.index(day_ganzhi) if day_ganzhi in JIAZI_TABLE else 0
    shichen_num = get_shichen_by_hour(solar.hour)
    day_gan = get_day_tiangan(solar)
    shichen_ganzhi = get_shichen_ganzhi(day_gan, shichen_num)
    yueling = get_yueling_by_solar(solar)
    xunkong = get_xunkong(day_ganzhi=day_ganzhi)
    dun_type = _dun_type(solar)
    ju_number = _ju_number(solar, day_index, shichen_num)
    return {
        "solar": solar,
        "day_ganzhi": day_ganzhi,
        "day_index": day_index,
        "day_gan": day_gan,
        "shichen_num": shichen_num,
        "shichen_ganzhi": shichen_ganzhi,
        "yueling": yueling,
        "xunkong": xunkong,
        "dun_type": dun_type,
        "ju_number": ju_number,
    }


def _build_board(time_context, scenario, direction=""):
    reverse = time_context["dun_type"] == "阴遁"
    day_index = time_context["day_index"]
    shichen_num = time_context["shichen_num"]
    ju_number = time_context["ju_number"]
    shichen_ganzhi = time_context["shichen_ganzhi"]
    shichen_index = JIAZI_TABLE.index(shichen_ganzhi) if shichen_ganzhi in JIAZI_TABLE else text_to_seed(shichen_ganzhi)

    doors = _rotate(EIGHT_DOOR_ORDER, ju_number + shichen_num - 1, reverse=reverse)
    stars = _rotate(NINE_STAR_ORDER, day_index + ju_number, reverse=reverse)
    gods = _rotate(EIGHT_GOD_ORDER, day_index + shichen_num + ju_number, reverse=reverse)
    stems = _rotate(QIMEN_STEM_ORDER, shichen_index + ju_number, reverse=reverse)
    empty_branches = set(time_context["xunkong"].get("empty_branches", []))
    current_direction = normalize_direction(direction)

    board = []
    outer_index = 0
    for palace_index, palace in enumerate(QIMEN_PALACES):
        stem_name = stems[palace_index % len(stems)]
        stem = QIMEN_STEM_MEANING[stem_name]
        is_current = bool(current_direction and palace["direction"] == current_direction)
        is_empty = bool(set(palace.get("branches", [])) & empty_branches)

        if palace["key"] == "center":
            star_name = "天禽"
            star = NINE_STARS[star_name]
            score = round(star["score"] + stem["score"], 2)
            item = {
                "palace": palace,
                "door": None,
                "star": {"name": star_name, **star},
                "god": None,
                "stem": {"name": stem_name, **stem},
                "is_empty": False,
                "is_current_direction": is_current,
                "scenario_reasons": [],
                "score": score,
                "level": "统筹",
                "action_tip": _action_tip(palace, "", star_name, "", score, scenario, is_current),
            }
            board.append(item)
            continue

        door_name = doors[outer_index]
        star_name = stars[outer_index]
        god_name = gods[outer_index]
        door = EIGHT_DOORS[door_name]
        star = NINE_STARS[star_name]
        god = EIGHT_GODS[god_name]
        modifier, reasons = _scenario_modifier(door_name, star_name, god_name, scenario["key"])
        score = (
            door["score"]
            + star["score"]
            + god["score"]
            + stem["score"]
            + _relation_score(palace["element"], door["element"])
            + modifier
            - (0.8 if is_empty else 0.0)
        )
        score = round(score, 2)

        board.append({
            "palace": palace,
            "door": {"name": door_name, **door},
            "star": {"name": star_name, **star},
            "god": {"name": god_name, **god},
            "stem": {"name": stem_name, **stem},
            "is_empty": is_empty,
            "is_current_direction": is_current,
            "scenario_reasons": reasons,
            "score": score,
            "level": _score_level(score),
            "action_tip": _action_tip(palace, door_name, star_name, god_name, score, scenario, is_current),
        })
        outer_index += 1

    return board


def _candidate_palaces(board):
    outer = [item for item in board if item["palace"]["key"] != "center"]
    ranked = sorted(outer, key=lambda item: item["score"], reverse=True)
    return ranked[:3], sorted(outer, key=lambda item: item["score"])[:3]


def _plain_conclusion(topic, scenario, best_palaces, avoid_palaces):
    best = best_palaces[0]
    avoid = avoid_palaces[0]
    best_palace = best["palace"]
    best_door = best["door"]["name"]
    avoid_palace = avoid["palace"]
    avoid_door = avoid["door"]["name"]
    subject = topic or scenario["name"]
    return (
        f"{subject}宜优先取{best_palace['direction']}方（{best_palace['name']}，{best_door}门，"
        f"{best['level']}，评分{best['score']}），先按“{scenario['action']}”执行。"
        f"{avoid_palace['direction']}方见{avoid_door}门且评分偏低，关键动作不宜从此处硬推。"
        "此为传统奇门运筹参考，仍需以现实信息、时机成本和可执行条件校验。"
    )


def analyze_qimen(
    topic: str = "",
    direction: str = "",
    mode: str = "",
    current: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """生成传统奇门运筹分析结果。"""
    solar = current or datetime.datetime.now()
    scenario = _infer_scenario(topic, mode)
    time_context = _build_time_context(solar)
    board = _build_board(time_context, scenario, direction)
    best_palaces, avoid_palaces = _candidate_palaces(board)
    current_direction = normalize_direction(direction)
    current_palace = next((item for item in board if item["is_current_direction"]), None)

    return {
        "topic": (topic or "").strip() or scenario["name"],
        "input_direction": direction or "",
        "current_direction": current_direction,
        "scenario": scenario,
        "time_context": {
            "solar": solar.strftime("%Y-%m-%d %H:%M"),
            "day_ganzhi": time_context["day_ganzhi"],
            "shichen_ganzhi": time_context["shichen_ganzhi"],
            "shichen_num": time_context["shichen_num"],
            "yueling": time_context["yueling"],
            "xun_name": time_context["xunkong"].get("xun_name", ""),
            "empty_branches": time_context["xunkong"].get("empty_branches", []),
            "dun_type": time_context["dun_type"],
            "ju_number": time_context["ju_number"],
        },
        "board": board,
        "best_palaces": best_palaces,
        "avoid_palaces": avoid_palaces,
        "current_palace": current_palace,
        "operation_logic": [
            "方位运筹：优先选择吉门、吉星、吉神相会且不落空亡的方位承接关键动作。",
            "时机运筹：同一问题换时辰会换盘，本结果只对应当前起局时点。",
            "格局运筹：八门看行动入口，九星看事态性质，八神看助力与风险，三奇六仪看资源与阻力。",
        ],
        "traditional_boundary": TRADITIONAL_QIMEN_BOUNDARY,
        "fenghou_boundary": FENGHOU_QIMEN_BOUNDARY,
        "boundary_note": (
            "当前为工程化简化盘：用近似阴阳遁与局数生成九宫运筹盘，"
            "未实现完整拆补、置闰、超接、符使飞布和历法精算。"
        ),
        "plain_conclusion": _plain_conclusion(topic, scenario, best_palaces, avoid_palaces),
    }


def _format_palace_line(item):
    palace = item["palace"]
    stem = item["stem"]
    if palace["key"] == "center":
        return (
            f"{palace['name']}（{palace['direction']}，{palace['element']}）："
            f"{item['star']['name']}，{stem['name']}{stem['type']}｜{item['level']}｜{item['action_tip']}"
        )

    door = item["door"]
    star = item["star"]
    god = item["god"]
    empty = "｜空亡" if item["is_empty"] else ""
    reasons = f"｜{'、'.join(item['scenario_reasons'])}" if item["scenario_reasons"] else ""
    return (
        f"{palace['name']}（{palace['direction']}，{palace['element']}）："
        f"{door['name']}门/{star['name']}/{god['name']}/{stem['name']}{stem['type']}｜"
        f"{item['level']}｜评分{item['score']}{empty}{reasons}"
    )


def format_qimen_report(result: Dict[str, Any]) -> str:
    """格式化 CLI 报告。"""
    time_info = result["time_context"]
    scenario = result["scenario"]
    lines: List[str] = []
    lines.append(f"主题：{result['topic']}｜场景：{scenario['name']}")
    lines.append(
        f"起局：{time_info['solar']}｜{time_info['day_ganzhi']}日｜"
        f"{time_info['shichen_ganzhi']}时｜{time_info['dun_type']}{time_info['ju_number']}局｜"
        f"{time_info['xun_name']}空{''.join(time_info['empty_branches'])}"
    )
    lines.append("")
    lines.append("【九宫简盘】")
    for item in result["board"]:
        lines.append(_format_palace_line(item))

    lines.append("")
    lines.append("【方位运筹】")
    for index, item in enumerate(result["best_palaces"], 1):
        palace = item["palace"]
        lines.append(
            f"{index}. {palace['direction']}方 {palace['name']}："
            f"{item['door']['name']}门、{item['star']['name']}、{item['god']['name']}，"
            f"{item['level']}，评分{item['score']}。{item['action_tip']}"
        )

    lines.append("")
    lines.append("【慎用方位】")
    for item in result["avoid_palaces"][:2]:
        palace = item["palace"]
        lines.append(
            f"{palace['direction']}方 {palace['name']}：{item['door']['name']}门，"
            f"{item['level']}，评分{item['score']}。{item['action_tip']}"
        )

    if result.get("current_direction"):
        lines.append("")
        lines.append("【当前方位】")
        current_palace = result.get("current_palace")
        if current_palace:
            lines.append(
                f"你输入的方位为{result['current_direction']}，对应{current_palace['palace']['name']}："
                f"{current_palace['level']}，评分{current_palace['score']}。{current_palace['action_tip']}"
            )
        else:
            lines.append(f"你输入的方位为{result['current_direction']}，未定位到可单独行动的外八宫。")

    lines.append("")
    lines.append("【运筹逻辑】")
    lines.extend(result["operation_logic"])
    lines.append("")
    lines.append("【传统与设定边界】")
    lines.append(result["traditional_boundary"])
    lines.append(result["fenghou_boundary"])
    lines.append(result["boundary_note"])
    lines.append("")
    lines.append(f"【简短结论】{result['plain_conclusion']}")
    return "\n".join(lines)
