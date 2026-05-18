# -*- coding: utf-8 -*-
"""解卦核心逻辑。"""

from config.hexagram_data import HEXAGRAM_DATA, JI_XIONG_LEVEL
from config.wuxing_rules import WUXING_SHENG, WUXING_KE, WUXING_WANG_SHUAI
from config.bagua_data import BAGUA_DATA
from core.divination import calculate_bian_gua


def _join_relation(sheng_relation, ke_relation, bihe_relation=""):
    relation_list = []
    if sheng_relation:
        relation_list.append(sheng_relation)
    if ke_relation:
        relation_list.append(ke_relation)
    if bihe_relation:
        relation_list.append(bihe_relation)
    return "；".join(relation_list) if relation_list else "上下卦五行无直接生克关系，宜结合卦意与旺衰综合判断"


def interpret_hexagram(hexagram_info):
    """六爻重卦解卦核心逻辑。"""
    upper_num = hexagram_info["upper_num"]
    lower_num = hexagram_info["lower_num"]
    lunar_info = hexagram_info["lunar_info"]
    dong_yao = hexagram_info["dong_yao"]
    upper_gua = hexagram_info["upper_gua"]
    lower_gua = hexagram_info["lower_gua"]

    hexagram_detail = HEXAGRAM_DATA.get(
        (upper_num, lower_num),
        {
            "name": f"{upper_gua['name']}{lower_gua['name']}",
            "core_meaning": upper_gua["core_meaning"] + lower_gua["core_meaning"],
            "ji_xiong": "中中卦",
            "gua_ci": "卦辞暂缺，后续补充",
            "yao_ci": ["初爻暂缺", "二爻暂缺", "三爻暂缺", "四爻暂缺", "五爻暂缺", "上爻暂缺"],
        },
    )

    upper_element = upper_gua["element"]
    lower_element = lower_gua["element"]
    season = lunar_info.get("season", "春")
    wang_shuai_map = WUXING_WANG_SHUAI.get(season, {})
    upper_wang_shuai = wang_shuai_map.get(upper_element, "平")
    lower_wang_shuai = wang_shuai_map.get(lower_element, "平")

    power_map = {"旺": 3.0, "相": 2.0, "休": 1.0, "囚": 0.5, "死": 0.2, "平": 1.0}
    upper_power = power_map.get(upper_wang_shuai, 1.0)
    lower_power = power_map.get(lower_wang_shuai, 1.0)

    sheng_relation = ""
    ke_relation = ""
    bihe_relation = ""
    has_sheng = False
    has_ke = False

    if WUXING_SHENG[upper_element] == lower_element:
        has_sheng = True
        if upper_power >= 2:
            sheng_relation = f"上卦{upper_gua['name']}旺相生扶下卦{lower_gua['name']}，前因滋养后果，事情顺势发展"
        else:
            sheng_relation = f"上卦{upper_gua['name']}生扶下卦{lower_gua['name']}，但上卦力量不足，助力有限"
    elif WUXING_SHENG[lower_element] == upper_element:
        has_sheng = True
        if lower_power >= 2:
            sheng_relation = f"下卦{lower_gua['name']}旺相生扶上卦{upper_gua['name']}，结果反哺当下，宜固本培元"
        else:
            sheng_relation = f"下卦{lower_gua['name']}生扶上卦{upper_gua['name']}，但下卦力量不足，助力有限"

    if WUXING_KE[upper_element] == lower_element:
        has_ke = True
        if upper_power >= lower_power * 1.5:
            ke_relation = f"上卦{upper_gua['name']}强力克制下卦{lower_gua['name']}，当下明显阻碍结果，需突破阻力"
        elif upper_power < lower_power:
            ke_relation = f"上卦{upper_gua['name']}弱克下卦{lower_gua['name']}，克制力不足，反易被结果牵制"
        else:
            ke_relation = f"上卦{upper_gua['name']}克制下卦{lower_gua['name']}，当下阻碍结果，需处理阻力"
    elif WUXING_KE[lower_element] == upper_element:
        has_ke = True
        if lower_power >= upper_power * 1.5:
            ke_relation = f"下卦{lower_gua['name']}强力克制上卦{upper_gua['name']}，结果明显反噬当下，需谨慎行事"
        elif lower_power < upper_power:
            ke_relation = f"下卦{lower_gua['name']}弱克上卦{upper_gua['name']}，反噬力有限，但仍需留意后续压力"
        else:
            ke_relation = f"下卦{lower_gua['name']}克制上卦{upper_gua['name']}，结果反噬当下，需谨慎行事"

    if upper_element == lower_element:
        bihe_relation = f"上下卦五行比和，同属{upper_element}，力量同气相求，宜稳扎稳打"

    sheng_ke_text = _join_relation(sheng_relation, ke_relation, bihe_relation)

    ji_xiong = hexagram_detail.get("ji_xiong", "中中卦")
    ji_xiong_score = JI_XIONG_LEVEL.get(ji_xiong, 3)

    weak_states = ["囚", "死"]
    medium_states = ["休"]
    strong_states = ["旺", "相"]
    upper_is_weak = upper_wang_shuai in weak_states
    lower_is_weak = lower_wang_shuai in weak_states
    upper_is_medium = upper_wang_shuai in medium_states
    lower_is_medium = lower_wang_shuai in medium_states
    upper_is_strong = upper_wang_shuai in strong_states
    lower_is_strong = lower_wang_shuai in strong_states

    if ji_xiong_score >= 4:
        if has_ke and (upper_is_weak or lower_is_weak):
            decision_suggest = "卦象基调偏吉，可推进，但当前存在五行克制与旺衰不足，不宜激进冒进；宜借助合作、资源整合与稳步推进来化解阻力"
        elif has_ke:
            decision_suggest = "卦象基调偏吉，可主动推进，但上下卦存在克制关系，推进时需注意冲突、压力与后续反噬"
        elif has_sheng and (upper_is_strong or lower_is_strong):
            decision_suggest = "卦象基调偏吉，且有生扶助力，适合积极推进，可顺势行动并主动争取机会"
        elif upper_is_medium or lower_is_medium:
            decision_suggest = "卦象基调偏吉，整体可推进，但当前气势不算极旺，宜稳中求进，避免急躁冒进"
        else:
            decision_suggest = "卦象基调偏吉，整体可推进，但仍需结合现实条件，以稳中求进为宜"
    elif ji_xiong_score == 3:
        if has_sheng:
            decision_suggest = "卦象基调平稳，且有生扶之象，适合稳中求进，逐步推进，不宜急躁"
        elif has_ke:
            decision_suggest = "卦象基调平稳，但存在克制关系，宜先处理阻碍，再考虑推进"
        elif upper_is_strong or lower_is_strong:
            decision_suggest = "卦象基调中平，但当前有得令之处，可小步推进，宜保持谨慎，不宜过度扩张"
        else:
            decision_suggest = "卦象基调中平，事宜守正持中，稳中求进，不宜冒进"
    else:
        if has_sheng and (upper_is_strong or lower_is_strong):
            decision_suggest = "卦象基调偏弱，但仍有生扶与得令之处，可小步试探，不宜大举行动"
        elif has_ke:
            decision_suggest = "卦象基调偏弱，且存在克制关系，当前阻力较明显，宜先收敛、观察、修正问题，不宜强行推进"
        else:
            decision_suggest = "卦象基调偏弱，事宜隐忍待机，以静制动，不宜妄动"

    dong_yao_meaning = {
        1: "初爻：事情初始阶段、根基、内部变化",
        2: "二爻：事情发展阶段、人际、环境变化",
        3: "三爻：事情中段、行动、自身变化",
        4: "四爻：事情转折、外部、上级变化",
        5: "五爻：事情高峰、结果、核心变化",
        6: "上爻：事情终局、收尾、外部变化",
    }
    dong_yao_tip = f"动爻在第{dong_yao}爻，{dong_yao_meaning.get(dong_yao, '为事情变化的核心节点')}"

    bian_upper, bian_lower = calculate_bian_gua(upper_num, lower_num, dong_yao)
    default_bian_name = f"{BAGUA_DATA[bian_upper]['name']}{BAGUA_DATA[bian_lower]['name']}"
    bian_detail = HEXAGRAM_DATA.get((bian_upper, bian_lower), {})
    bian_gua_tip = (
        f"变卦为{bian_detail.get('name', default_bian_name)}"
        f"（{bian_detail.get('ji_xiong', '中中卦')}），代表事情的后续趋势："
        f"{'、'.join(bian_detail.get('core_meaning', ['变卦暂缺'])[:3])}"
    )

    yao_ci_list = hexagram_detail.get("yao_ci") or ["初爻暂缺", "二爻暂缺", "三爻暂缺", "四爻暂缺", "五爻暂缺", "上爻暂缺"]
    yao_ci = yao_ci_list[dong_yao - 1] if 0 <= dong_yao - 1 < len(yao_ci_list) else "动爻爻辞暂缺"
    yao_ci_tip = f"动爻爻辞：{yao_ci}"

    return {
        "gua_name": hexagram_detail["name"],
        "gua_ci": hexagram_detail["gua_ci"],
        "core_meaning": hexagram_detail["core_meaning"],
        "ji_xiong": ji_xiong,
        "ji_xiong_score": ji_xiong_score,
        "qian_yin_hou_guo": f"上卦{upper_gua['full_name']}为前因/当下，下卦{lower_gua['full_name']}为后果/未来",
        "sheng_ke_analysis": sheng_ke_text,
        "wang_shuai_analysis": f"上卦{upper_gua['name']}当季{upper_wang_shuai}，下卦{lower_gua['name']}当季{lower_wang_shuai}",
        "dong_yao_tip": dong_yao_tip,
        "yao_ci_tip": yao_ci_tip,
        "bian_gua_tip": bian_gua_tip,
        "naja_analysis": "",
        "decision_suggest": decision_suggest,
        "naja_info": hexagram_info.get("naja_info"),
    }


def interpret_three_yao(three_yao_info):
    """三爻快占解卦逻辑。"""
    gua_info = three_yao_info["gua_info"]
    lunar_info = three_yao_info["lunar_info"]
    season = lunar_info.get("season", "春")
    element = gua_info["element"]
    wang_shuai = WUXING_WANG_SHUAI.get(season, {}).get(element, "平")

    core_tip = f"得{gua_info['full_name']}卦{gua_info['gua_hua']}，五行属{element}，当季{wang_shuai}"
    meaning_tip = f"核心意象：{'、'.join(gua_info['core_meaning'])}"
    direction_tip = f"有利方位：{gua_info['position']}方，对应颜色：{gua_info['color']}"
    weather_tip = f"对应天时：{gua_info['weather']}"
    wu_xiang_tip = f"对应物象：{'、'.join(gua_info['wu_xiang'])}"

    if wang_shuai in ("旺", "相"):
        suggest = "事宜积极推进，利主动，利往对应方位行事"
    elif wang_shuai in ("休", "囚"):
        suggest = "事宜守成，不宜冒进，以稳为主"
    else:
        suggest = "事宜隐忍待机，不宜妄动，静待时机"

    return {
        "core_tip": core_tip,
        "meaning_tip": meaning_tip,
        "direction_tip": direction_tip,
        "weather_tip": weather_tip,
        "wu_xiang_tip": wu_xiang_tip,
        "suggest": suggest,
    }
