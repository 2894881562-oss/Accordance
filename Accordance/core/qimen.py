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
    SIX_JIA_DUN,
    THREE_QI,
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
FAVORABLE_DOORS = {"开", "生", "休", "景"}
HARD_DOORS = {"伤", "惊", "死"}
FAVORABLE_STARS = {"天心", "天辅", "天任", "天英", "天冲"}
FAVORABLE_GODS = {"值符", "六合", "太阴", "九天", "九地"}
RISK_GODS = {"白虎", "玄武", "螣蛇"}
TIMING_SIGNAL_WEIGHT = {
    "可执行": 2.0,
    "小步推进": 1.0,
    "先试探": 0.0,
    "暂缓强攻": -2.0,
}
TIMING_RISK_WEIGHT = {
    "压力有限": 0.8,
    "可化解": 0.3,
    "需避锋": -1.0,
    "高风险": -2.0,
}
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


def _build_dunjia_xun(ganzhi):
    """按时干支定位当前六甲旬首和甲所遁之六仪。"""
    if ganzhi not in JIAZI_TABLE:
        rule = SIX_JIA_DUN["甲子"]
        return {"xunshou": "甲子", **rule}
    xun_start = JIAZI_TABLE[(JIAZI_TABLE.index(ganzhi) // 10) * 10]
    rule = SIX_JIA_DUN.get(xun_start, SIX_JIA_DUN["甲子"])
    return {"xunshou": xun_start, **rule}


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


def _apply_dunjia_weights(board, dunjia):
    """把遁甲核心角色写入九宫盘，并轻量修正方位评分。"""
    commander_stem = dunjia["instrument"]
    for item in board:
        stem_name = item["stem"]["name"]
        roles = []
        notes = []
        modifier = 0.0

        if stem_name == commander_stem:
            roles.append("甲遁主帅")
            notes.append(dunjia["role"])
            modifier += 0.6
            if item["palace"]["key"] != "center":
                door_name = item["door"]["name"]
                god_name = item["god"]["name"]
                if door_name in ("开", "生", "休", "杜"):
                    modifier += 0.5
                    notes.append(f"{door_name}门可护核心，不宜过早摊牌。")
                if door_name in ("死", "惊", "伤"):
                    modifier -= 0.8
                    notes.append(f"{door_name}门压主帅，核心目标宜藏不宜攻。")
                if god_name in ("值符", "六合", "太阴", "九地"):
                    modifier += 0.5
                    notes.append(f"{god_name}能护甲，利于暗中蓄势。")
                if god_name in ("白虎", "玄武", "螣蛇"):
                    modifier -= 0.5
                    notes.append(f"{god_name}使藏甲多疑险，需控损与核实信息。")
                if item["is_empty"]:
                    modifier -= 0.6
                    notes.append("藏甲宫逢空亡，主线不宜落空口承诺。")

        if stem_name == "庚":
            roles.append("庚为阻力")
            if commander_stem == "庚":
                modifier -= 0.4
                notes.append("本旬甲申遁庚，主帅伏于阻力之仪，尤其要避开正面硬撞。")
            else:
                modifier -= 0.8
                notes.append("庚为甲之冲克压力，此方不宜暴露底牌。")

        if stem_name in THREE_QI:
            roles.append(f"{stem_name}奇护局")
            modifier += 0.4
            notes.append(f"{stem_name}奇可作外层助力，适合替主线做铺垫。")

        item["dunjia_roles"] = roles
        item["dunjia_notes"] = notes
        item["dunjia_modifier"] = round(modifier, 2)
        if modifier:
            item["score"] = round(item["score"] + modifier, 2)
            if item["palace"]["key"] != "center":
                item["level"] = _score_level(item["score"])


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
        "dunjia": _build_dunjia_xun(shichen_ganzhi),
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

    _apply_dunjia_weights(board, time_context["dunjia"])
    return board


def _candidate_palaces(board):
    outer = [item for item in board if item["palace"]["key"] != "center"]
    ranked = sorted(outer, key=lambda item: item["score"], reverse=True)
    return ranked[:3], sorted(outer, key=lambda item: item["score"])[:3]


def _build_dunjia_profile(board, time_context):
    """整理当前局的遁甲核心信息。"""
    dunjia = time_context["dunjia"]
    commander_stem = dunjia["instrument"]
    commander_palace = next((item for item in board if item["stem"]["name"] == commander_stem), None)
    geng_palace = next((item for item in board if item["stem"]["name"] == "庚"), None)
    three_qi_palaces = [item for item in board if item["stem"]["name"] in THREE_QI]

    commander_score = commander_palace["score"] if commander_palace else 0
    if commander_score >= 3:
        protection_level = "护甲有力"
        core_advice = "核心目标可暗中承接，但外层动作仍宜用门星神较顺的方位铺路。"
    elif commander_score >= 0:
        protection_level = "藏甲可守"
        core_advice = "主线可以保留，但不宜急于摊牌；先以三奇或吉门方位试探。"
    else:
        protection_level = "主帅受压"
        core_advice = "核心目标暂宜隐忍，先避庚方与凶门，改用外围助力化解压力。"

    if commander_stem == "庚":
        pressure_note = "本旬为甲申遁庚，主帅与阻力同仪，越要重视保密、证据和避锋。"
    elif geng_palace:
        pressure_note = (
            f"庚在{geng_palace['palace']['direction']}方{geng_palace['palace']['name']}，"
            "此方代表克甲压力，关键底牌不宜从此处暴露。"
        )
    else:
        pressure_note = "本盘未定位到庚宫，按一般避锋原则处理。"

    guard_text = "、".join(
        f"{item['stem']['name']}奇在{item['palace']['direction']}方"
        for item in sorted(three_qi_palaces, key=lambda palace: palace["score"], reverse=True)
    )

    return {
        "xun_name": dunjia["xun_name"],
        "xunshou": dunjia["xunshou"],
        "instrument": commander_stem,
        "label": dunjia["label"],
        "role": dunjia["role"],
        "strategy": dunjia["strategy"],
        "commander_palace": commander_palace,
        "geng_palace": geng_palace,
        "three_qi_palaces": three_qi_palaces,
        "protection_level": protection_level,
        "core_advice": core_advice,
        "pressure_note": pressure_note,
        "guard_text": guard_text,
    }


def _build_zhifu_zhishi_profile(dunjia_profile):
    """以藏甲宫为参照，给出值符星和值使门的工程化提示。"""
    commander = dunjia_profile.get("commander_palace")
    if not commander:
        return {
            "zhi_fu_star": "",
            "zhi_shi_door": "",
            "summary": "未定位到藏甲宫，暂不推值符值使。",
            "action_basis": "",
            "boundary": "此处为工程化简化盘的值符值使参照，不替代专业奇门排盘。",
        }

    star = commander["star"]
    door = commander.get("door")
    palace = commander["palace"]
    zhi_shi = door["name"] if door else "中宫无门"
    door_text = door["strategy"] if door else "中宫只作统筹，关键动作仍需借外八宫承接。"
    if commander["score"] >= 3:
        command_level = "主令可用"
    elif commander["score"] >= 0:
        command_level = "主令可守"
    else:
        command_level = "主令受压"

    return {
        "zhi_fu_star": star["name"],
        "zhi_shi_door": zhi_shi,
        "palace_direction": palace["direction"],
        "palace_name": palace["name"],
        "command_level": command_level,
        "summary": (
            f"以藏甲宫为参照，值符星取{star['name']}，值使门取{zhi_shi}；"
            f"落{palace['direction']}方{palace['name']}，判断为{command_level}。"
        ),
        "action_basis": f"星主{star['meaning']}门主{door_text}",
        "boundary": "此处为工程化简化盘的值符值使参照，不替代专业奇门排盘。",
    }


def _evaluate_three_qi_palace(item):
    """评估三奇所在宫能否作为外层助力。"""
    palace = item["palace"]
    stem_name = item["stem"]["name"]
    score = item["score"]
    factors = []

    door = item.get("door")
    star = item.get("star")
    god = item.get("god")
    if door:
        if door["name"] in FAVORABLE_DOORS:
            score += 0.7
            factors.append(f"得{door['name']}门")
        elif door["name"] in HARD_DOORS:
            score -= 0.6
            factors.append(f"{door['name']}门带压")
    else:
        factors.append("中宫统筹")

    if star and star["name"] in FAVORABLE_STARS:
        score += 0.5
        factors.append(f"{star['name']}助势")
    if god:
        if god["name"] in FAVORABLE_GODS:
            score += 0.6
            factors.append(f"{god['name']}护局")
        elif god["name"] in RISK_GODS:
            score -= 0.5
            factors.append(f"{god['name']}添险")
    if item.get("is_empty"):
        score -= 0.6
        factors.append("逢空亡")

    score = round(score, 2)
    if score >= 5:
        level = "得门得神"
    elif score >= 3:
        level = "可借力"
    elif score >= 1:
        level = "可铺垫"
    else:
        level = "助力有限"

    role = {
        "乙": "乙奇偏人和、文书、柔性沟通。",
        "丙": "丙奇偏显化、声势、公开表达。",
        "丁": "丁奇偏机巧、暗助、精细突破。",
    }.get(stem_name, "")

    return {
        "stem": stem_name,
        "palace_direction": palace["direction"],
        "palace_name": palace["name"],
        "score": score,
        "level": level,
        "role": role,
        "factors": factors,
        "summary": (
            f"{stem_name}奇在{palace['direction']}方{palace['name']}，{level}，评分{score}。"
            f"{role}{'依据：' + '、'.join(factors) if factors else ''}"
        ),
    }


def _build_three_qi_analysis(board):
    items = [
        _evaluate_three_qi_palace(item)
        for item in board
        if item["stem"]["name"] in THREE_QI
    ]
    items.sort(key=lambda item: item["score"], reverse=True)
    best = items[0] if items else None
    if best:
        summary = f"三奇以{best['stem']}奇最可借，位置在{best['palace_direction']}方，{best['level']}。"
    else:
        summary = "本盘未定位到三奇助力。"
    return {"items": items, "best": best, "summary": summary}


def _build_geng_risk(board, dunjia_profile):
    geng = dunjia_profile.get("geng_palace")
    commander = dunjia_profile.get("commander_palace")
    risks = []
    if not geng:
        return {"level": "未定位", "score": 0, "items": [], "summary": "本盘未定位庚方，按一般避锋原则处理。"}

    risk_score = 0
    same_palace = commander and commander["palace"]["key"] == geng["palace"]["key"]
    if same_palace:
        risk_score += 3
        risks.append("甲庚同宫或同仪：核心与阻力叠在一起，忌正面摊牌。")

    door = geng.get("door")
    god = geng.get("god")
    if door and door["name"] in HARD_DOORS:
        risk_score += 2
        risks.append(f"庚临{door['name']}门：对抗、惊扰或损耗加重。")
    elif door and door["name"] in FAVORABLE_DOORS:
        risk_score += 1
        risks.append(f"庚临{door['name']}门：阻力有可谈可转之处，但底牌仍要藏。")

    if god and god["name"] in RISK_GODS:
        risk_score += 2
        risks.append(f"庚伴{god['name']}：防强硬、暗线、疑虑或信息污染。")
    elif god and god["name"] in FAVORABLE_GODS:
        risks.append(f"庚伴{god['name']}：可借规则、合作或暗助降压。")

    if geng.get("is_empty"):
        risk_score -= 1
        risks.append("庚方逢空：压力未必坐实，但不可因空而轻敌。")

    if risk_score >= 5:
        level = "高风险"
    elif risk_score >= 3:
        level = "需避锋"
    elif risk_score >= 1:
        level = "可化解"
    else:
        level = "压力有限"

    palace = geng["palace"]
    return {
        "level": level,
        "score": risk_score,
        "items": risks,
        "summary": f"庚方在{palace['direction']}方{palace['name']}，判断为{level}。"
    }


def _build_tactical_posture(best_palaces, current_palace, dunjia_profile, three_qi_analysis, geng_risk):
    best = best_palaces[0]
    commander = dunjia_profile.get("commander_palace")
    commander_score = commander["score"] if commander else 0
    best_three_qi = three_qi_analysis.get("best")
    geng_level = geng_risk.get("level", "")

    if commander_score < 0 or geng_level in ("高风险", "需避锋"):
        name = "护主避锋"
        action = "先隐藏核心目标，避免正面硬撞；用三奇或吉门方位做外围铺垫。"
    elif best["score"] >= 5 and commander_score >= 1:
        name = "主动开局"
        action = "可让推荐方位承担关键动作，但核心底牌仍分层释放。"
    elif best_three_qi and best_three_qi["score"] >= 3:
        name = "借奇铺路"
        action = f"先借{best_three_qi['stem']}奇所在{best_three_qi['palace_direction']}方做沟通、展示或暗助。"
    else:
        name = "小步试探"
        action = "先做低成本试探，等门星神和现实反馈同向后再加码。"

    if current_palace:
        if current_palace["palace"]["key"] == best["palace"]["key"]:
            host_guest = "当前方位可作主方承接关键动作。"
        elif current_palace["score"] < 0:
            host_guest = "当前方位不宜做主方，关键动作宜转向推荐方位。"
        else:
            host_guest = "当前方位可作辅助位，主动作仍以推荐方位为准。"
    else:
        host_guest = "未输入当前方位，主客态势按推荐方位与藏甲宫判断。"

    return {
        "name": name,
        "action": action,
        "host_guest": host_guest,
        "summary": f"态势：{name}。{action}{host_guest}",
    }


def _build_action_plan(
    best_palaces,
    avoid_palaces,
    current_palace,
    dunjia_profile,
    zhifu_zhishi,
    three_qi_analysis,
    geng_risk,
    tactical_posture,
):
    """把奇门判断压缩成可执行的分步运筹方案。"""
    best = best_palaces[0]
    second = best_palaces[1] if len(best_palaces) > 1 else best
    avoid = avoid_palaces[0]
    commander = dunjia_profile.get("commander_palace")
    best_three_qi = three_qi_analysis.get("best")
    best_score = best["score"]
    commander_score = commander["score"] if commander else 0
    risk_level = geng_risk.get("level", "")

    if risk_level == "高风险" or (risk_level == "需避锋" and commander_score < 0):
        go_signal = "暂缓强攻"
        threshold = "庚方压力重或主帅受压，先守核心、降风险，不宜直接摊牌。"
    elif best_score >= 5 and commander_score >= 0:
        go_signal = "可执行"
        threshold = "推荐方位承载力强，且藏甲不至失守，可分层推进关键动作。"
    elif best_score >= 3:
        go_signal = "小步推进"
        threshold = "推荐方位可用，但仍需用低成本动作验证现实反馈。"
    else:
        go_signal = "先试探"
        threshold = "全局承载不足，先做信息收集与外围铺垫，暂不加码。"

    phases = []
    if commander:
        palace = commander["palace"]
        phases.append({
            "name": "护甲定底线",
            "direction": palace["direction"],
            "palace": palace["name"],
            "action": (
                f"核心目标先藏于{palace['direction']}方{palace['name']}之象，"
                "只保留必要信息给关键人，不在压力位暴露底牌。"
            ),
            "basis": f"{dunjia_profile['label']}，{dunjia_profile['protection_level']}；{zhifu_zhishi['summary']}",
        })

    if best_three_qi:
        phases.append({
            "name": "借奇铺垫",
            "direction": best_three_qi["palace_direction"],
            "palace": best_three_qi["palace_name"],
            "action": (
                f"先借{best_three_qi['stem']}奇做外围动作：沟通、文书、展示、暗助或信息铺垫，"
                "让主线在不暴露的情况下获得外部支撑。"
            ),
            "basis": best_three_qi["summary"],
        })

    phases.append({
        "name": "取门执行",
        "direction": best["palace"]["direction"],
        "palace": best["palace"]["name"],
        "action": (
            f"关键动作优先取{best['palace']['direction']}方，按{best['door']['name']}门之象执行；"
            f"若条件不足，则转用{second['palace']['direction']}方作备用承接。"
        ),
        "basis": f"{best['door']['name']}门、{best['star']['name']}、{best['god']['name']}，{best['level']}，评分{best['score']}。",
    })

    phases.append({
        "name": "避庚控险",
        "direction": geng_risk.get("summary", ""),
        "palace": "",
        "action": (
            "庚方和最低分方位不承担摊牌、签约、强攻、公开承诺等关键动作；"
            "只用于识别对手、压力源、硬约束和需要证据化处理的问题。"
        ),
        "basis": f"{geng_risk['summary']}最低分方位为{avoid['palace']['direction']}方{avoid['palace']['name']}，{avoid['level']}。",
    })

    if current_palace:
        phases.append({
            "name": "校准当前位",
            "direction": current_palace["palace"]["direction"],
            "palace": current_palace["palace"]["name"],
            "action": (
                "当前方位只按其评分承担相应角色；若与推荐方位不一致，"
                "把当前位作为准备位或辅助位，不让它替代主攻方。"
            ),
            "basis": f"当前方位{current_palace['level']}，评分{current_palace['score']}。",
        })

    phases.append({
        "name": "现实复核",
        "direction": "",
        "palace": "",
        "action": "执行前核对人、钱、时间、证据、权限和退出条件；现实条件不满足时，宁可降级为试探动作。",
        "basis": "奇门只给时空运筹参考，不替代事实、专业意见和个人判断。",
    })

    summary = f"行动信号：{go_signal}。{threshold}{tactical_posture['summary']}"
    return {
        "go_signal": go_signal,
        "threshold": threshold,
        "summary": summary,
        "phases": phases,
    }


def _shichen_window_start(solar, shichen_num=None):
    """返回当前时辰窗口的起点，用于横向比较后续时辰。"""
    shichen_num = shichen_num or get_shichen_by_hour(solar.hour)
    start_hour = (2 * (shichen_num - 1) - 1) % 24
    start = solar.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if shichen_num == 1 and solar.hour < 1:
        start -= datetime.timedelta(days=1)
    if start > solar:
        start -= datetime.timedelta(days=1)
    return start


def _timing_candidate_datetimes(solar):
    base = _shichen_window_start(solar)
    return [
        {"label": "当前时辰", "solar": solar},
        {"label": "下一时辰", "solar": base + datetime.timedelta(hours=2)},
        {"label": "再下一时辰", "solar": base + datetime.timedelta(hours=4)},
    ]


def _timing_level(score):
    if score >= 7:
        return "最佳窗口"
    if score >= 5:
        return "可用窗口"
    if score >= 3:
        return "试探窗口"
    return "暂缓窗口"


def _timing_window_item(label, result):
    best = result["best_palaces"][0]
    commander = result.get("dunjia_profile", {}).get("commander_palace")
    action_plan = result.get("action_plan", {})
    geng_risk = result.get("geng_risk", {})
    posture = result.get("tactical_posture", {})
    time_info = result["time_context"]
    go_signal = action_plan.get("go_signal", "")
    risk_level = geng_risk.get("level", "")
    commander_score = commander["score"] if commander else 0.0
    commander_modifier = max(-1.0, min(1.0, commander_score / 4))
    window_score = (
        best["score"]
        + TIMING_SIGNAL_WEIGHT.get(go_signal, 0.0)
        + TIMING_RISK_WEIGHT.get(risk_level, 0.0)
        + commander_modifier
    )
    window_score = round(window_score, 2)
    return {
        "label": label,
        "solar": time_info["solar"],
        "shichen_ganzhi": time_info["shichen_ganzhi"],
        "dun_type": time_info["dun_type"],
        "ju_number": time_info["ju_number"],
        "best_direction": best["palace"]["direction"],
        "best_palace": best["palace"]["name"],
        "best_door": best["door"]["name"],
        "best_score": best["score"],
        "commander_direction": commander["palace"]["direction"] if commander else "",
        "commander_score": round(commander_score, 2),
        "geng_level": risk_level,
        "go_signal": go_signal,
        "posture": posture.get("name", ""),
        "window_score": window_score,
        "level": _timing_level(window_score),
    }


def _build_timing_windows(topic, direction, mode, solar, current_result):
    """比较当前、下一、再下一时辰，给出简化择时窗口。"""
    items = []
    for candidate in _timing_candidate_datetimes(solar):
        if candidate["label"] == "当前时辰":
            candidate_result = current_result
        else:
            candidate_result = analyze_qimen(
                topic=topic,
                direction=direction,
                mode=mode,
                current=candidate["solar"],
                include_timing=False,
            )
        items.append(_timing_window_item(candidate["label"], candidate_result))

    ranked = sorted(items, key=lambda item: item["window_score"], reverse=True)
    best = ranked[0]
    if best["label"] == "当前时辰":
        summary = (
            f"当前窗口评分最高，可按{best['go_signal']}处理；"
            f"优先取{best['best_direction']}方{best['best_door']}门，仍需避开庚格风险。"
        )
    elif best["label"] == "下一时辰":
        summary = (
            f"更适合等到下一时辰（{best['solar']}，{best['shichen_ganzhi']}时）再承接关键动作；"
            f"当前可先铺垫信息和资源。"
        )
    else:
        summary = (
            f"当前与下一时辰都不宜急推，较佳窗口在再下一时辰"
            f"（{best['solar']}，{best['shichen_ganzhi']}时）；先做准备和风险隔离。"
        )

    return {
        "items": items,
        "ranked": ranked,
        "best": best,
        "summary": summary,
        "boundary": "时机窗口为工程化简化比较，只比较相邻三个时辰盘，不替代完整奇门择时排盘。",
    }


def _plain_conclusion(
    topic,
    scenario,
    best_palaces,
    avoid_palaces,
    dunjia_profile=None,
    tactical_posture=None,
    action_plan=None,
):
    best = best_palaces[0]
    avoid = avoid_palaces[0]
    best_palace = best["palace"]
    best_door = best["door"]["name"]
    avoid_palace = avoid["palace"]
    avoid_door = avoid["door"]["name"]
    subject = topic or scenario["name"]
    dunjia_text = ""
    if dunjia_profile:
        commander = dunjia_profile.get("commander_palace") or {}
        palace = commander.get("palace", {})
        dunjia_text = (
            f"本局{dunjia_profile['label']}，甲藏{palace.get('direction', '未知')}方，"
            f"{dunjia_profile['protection_level']}。"
        )
    return (
        f"{subject}宜优先取{best_palace['direction']}方（{best_palace['name']}，{best_door}门，"
        f"{best['level']}，评分{best['score']}），先按“{scenario['action']}”执行。"
        f"{dunjia_text}"
        f"{'态势取' + tactical_posture['name'] + '。' if tactical_posture else ''}"
        f"{'行动信号为' + action_plan['go_signal'] + '。' if action_plan else ''}"
        f"{avoid_palace['direction']}方见{avoid_door}门且评分偏低，关键动作不宜从此处硬推。"
        "此为传统奇门运筹参考，仍需以现实信息、时机成本和可执行条件校验。"
    )


def analyze_qimen(
    topic: str = "",
    direction: str = "",
    mode: str = "",
    current: Optional[datetime.datetime] = None,
    include_timing: bool = True,
) -> Dict[str, Any]:
    """生成传统奇门运筹分析结果。"""
    solar = current or datetime.datetime.now()
    scenario = _infer_scenario(topic, mode)
    time_context = _build_time_context(solar)
    board = _build_board(time_context, scenario, direction)
    dunjia_profile = _build_dunjia_profile(board, time_context)
    best_palaces, avoid_palaces = _candidate_palaces(board)
    current_direction = normalize_direction(direction)
    current_palace = next((item for item in board if item["is_current_direction"]), None)
    zhifu_zhishi = _build_zhifu_zhishi_profile(dunjia_profile)
    three_qi_analysis = _build_three_qi_analysis(board)
    geng_risk = _build_geng_risk(board, dunjia_profile)
    tactical_posture = _build_tactical_posture(
        best_palaces,
        current_palace,
        dunjia_profile,
        three_qi_analysis,
        geng_risk,
    )
    action_plan = _build_action_plan(
        best_palaces,
        avoid_palaces,
        current_palace,
        dunjia_profile,
        zhifu_zhishi,
        three_qi_analysis,
        geng_risk,
        tactical_posture,
    )

    result = {
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
            "dunjia": time_context["dunjia"],
        },
        "board": board,
        "best_palaces": best_palaces,
        "avoid_palaces": avoid_palaces,
        "current_palace": current_palace,
        "dunjia_profile": dunjia_profile,
        "zhifu_zhishi": zhifu_zhishi,
        "three_qi_analysis": three_qi_analysis,
        "geng_risk": geng_risk,
        "tactical_posture": tactical_posture,
        "action_plan": action_plan,
        "operation_logic": [
            "方位运筹：优先选择吉门、吉星、吉神相会且不落空亡的方位承接关键动作。",
            "时机运筹：同一问题换时辰会换盘，可横向比较当前、下一、再下一时辰的承载力。",
            "格局运筹：八门看行动入口，九星看事态性质，八神看助力与风险，三奇六仪看资源与阻力。",
            "遁甲护核：甲为主帅与核心目标，按当前旬首遁入六仪；先护主线，再借三奇与吉门做外层行动。",
        ],
        "traditional_boundary": TRADITIONAL_QIMEN_BOUNDARY,
        "fenghou_boundary": FENGHOU_QIMEN_BOUNDARY,
        "boundary_note": (
            "当前为工程化简化盘：用近似阴阳遁与局数生成九宫运筹盘，"
            "未实现完整拆补、置闰、超接、符使飞布和历法精算。"
        ),
        "plain_conclusion": _plain_conclusion(
            topic,
            scenario,
            best_palaces,
            avoid_palaces,
            dunjia_profile,
            tactical_posture,
            action_plan,
        ),
    }
    if include_timing:
        timing_windows = _build_timing_windows(topic, direction, mode, solar, result)
        result["timing_windows"] = timing_windows
        result["plain_conclusion"] = f"{result['plain_conclusion']} 时机参考：{timing_windows['summary']}"
    else:
        result["timing_windows"] = {"items": [], "ranked": [], "best": None, "summary": "", "boundary": ""}
    return result


def _format_palace_line(item):
    palace = item["palace"]
    stem = item["stem"]
    roles = f"｜遁甲:{'、'.join(item.get('dunjia_roles', []))}" if item.get("dunjia_roles") else ""
    modifier = item.get("dunjia_modifier", 0)
    modifier_text = f"｜遁甲修正{modifier:+.1f}" if modifier else ""
    if palace["key"] == "center":
        return (
            f"{palace['name']}（{palace['direction']}，{palace['element']}）："
            f"{item['star']['name']}，{stem['name']}{stem['type']}｜{item['level']}"
            f"{roles}{modifier_text}｜{item['action_tip']}"
        )

    door = item["door"]
    star = item["star"]
    god = item["god"]
    empty = "｜空亡" if item["is_empty"] else ""
    reasons = f"｜{'、'.join(item['scenario_reasons'])}" if item["scenario_reasons"] else ""
    return (
        f"{palace['name']}（{palace['direction']}，{palace['element']}）："
        f"{door['name']}门/{star['name']}/{god['name']}/{stem['name']}{stem['type']}｜"
        f"{item['level']}｜评分{item['score']}{empty}{roles}{modifier_text}{reasons}"
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
        f"{time_info['xun_name']}空{''.join(time_info['empty_branches'])}｜"
        f"{time_info['dunjia']['label']}"
    )
    lines.append("")
    lines.append("【九宫简盘】")
    for item in result["board"]:
        lines.append(_format_palace_line(item))

    dunjia = result["dunjia_profile"]
    commander = dunjia.get("commander_palace")
    geng = dunjia.get("geng_palace")
    lines.append("")
    lines.append("【遁甲核心】")
    lines.append(f"{dunjia['label']}：{dunjia['role']}")
    if commander:
        palace = commander["palace"]
        lines.append(
            f"藏甲宫：{palace['direction']}方 {palace['name']}，"
            f"{commander['level']}，评分{commander['score']}。{dunjia['protection_level']}。"
        )
        for note in commander.get("dunjia_notes", [])[:3]:
            lines.append(f"  - {note}")
    if geng:
        palace = geng["palace"]
        lines.append(
            f"庚方压力：{palace['direction']}方 {palace['name']}，"
            f"{geng['level']}，评分{geng['score']}。{dunjia['pressure_note']}"
        )
    lines.append(f"三奇护局：{dunjia['guard_text'] or '本盘三奇仅作背景，未形成明显外层助力。'}")
    lines.append(f"主线策略：{dunjia['strategy']}{dunjia['core_advice']}")

    zhifu = result["zhifu_zhishi"]
    lines.append("")
    lines.append("【值符值使】")
    lines.append(zhifu["summary"])
    if zhifu.get("action_basis"):
        lines.append(zhifu["action_basis"])
    lines.append(zhifu["boundary"])

    three_qi = result["three_qi_analysis"]
    lines.append("")
    lines.append("【三奇助力】")
    lines.append(three_qi["summary"])
    for item in three_qi["items"]:
        factor_text = f"（{'、'.join(item['factors'])}）" if item["factors"] else ""
        lines.append(f"{item['summary']}{factor_text}")

    geng_risk = result["geng_risk"]
    lines.append("")
    lines.append("【庚格风险】")
    lines.append(geng_risk["summary"])
    for risk in geng_risk["items"]:
        lines.append(f"  - {risk}")

    posture = result["tactical_posture"]
    lines.append("")
    lines.append("【主客态势】")
    lines.append(posture["summary"])

    action_plan = result["action_plan"]
    lines.append("")
    lines.append("【行动方案】")
    lines.append(action_plan["summary"])
    for index, phase in enumerate(action_plan["phases"], 1):
        location = f"{phase['direction']}方 {phase['palace']}".strip()
        location_text = f"｜{location}" if location else ""
        lines.append(f"{index}. {phase['name']}{location_text}：{phase['action']}")
        lines.append(f"   依据：{phase['basis']}")

    timing_windows = result.get("timing_windows", {})
    if timing_windows.get("items"):
        lines.append("")
        lines.append("【时机窗口】")
        lines.append(timing_windows["summary"])
        for index, item in enumerate(timing_windows["ranked"], 1):
            lines.append(
                f"{index}. {item['label']}｜{item['solar']}｜{item['shichen_ganzhi']}时｜"
                f"{item['level']}｜窗口评分{item['window_score']}｜行动{item['go_signal']}｜"
                f"取{item['best_direction']}方{item['best_door']}门｜态势{item['posture']}｜庚格{item['geng_level']}"
            )
        lines.append(timing_windows["boundary"])

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
