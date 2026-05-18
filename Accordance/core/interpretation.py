# -*- coding: utf-8 -*-
"""解卦核心逻辑。整合京房纳甲、梅花易数体用、互错综卦等多维分析。"""

from config.hexagram_data import HEXAGRAM_DATA, JI_XIONG_LEVEL
from config.wuxing_rules import (
    WUXING_SHENG, WUXING_KE, WUXING_WANG_SHUAI,
)
from config.bagua_data import (
    BAGUA_DATA, TIYONG_SHENG_KE_XIANG,
)
from config.naja_data import (
    LIUQIN_XIANGYI, LIUSHEN_XIANGYI,
)
from core.divination import (
    calculate_bian_gua, calculate_hugua, calculate_cuogua,
    calculate_zonggua, identify_tiyong,
)
from core.zhuanggua import (
    zhuang_gua_complete, format_zhuanggua_table,
    analyze_liuqin_summary, get_shishen_liuqin,
    analyze_dizhi_relation_summary, analyze_nayin_summary,
    analyze_liushen_zhihua_summary,
    refresh_line_strengths, analyze_yongshen_system,
    analyze_line_strength_summary, analyze_bian_line_relation,
    build_traditional_evidence_chain,
)


def _join_relation(sheng_relation, ke_relation, bihe_relation=""):
    relation_list = []
    if sheng_relation:
        relation_list.append(sheng_relation)
    if ke_relation:
        relation_list.append(ke_relation)
    if bihe_relation:
        relation_list.append(bihe_relation)
    return "；".join(relation_list) if relation_list else "上下卦五行无直接生克关系，宜结合卦意与旺衰综合判断"


def _hexagram_name(upper_num, lower_num):
    detail = HEXAGRAM_DATA.get((upper_num, lower_num), {})
    return detail.get("name", f"{BAGUA_DATA[upper_num]['name']}{BAGUA_DATA[lower_num]['name']}")


def _build_hu_cuo_zong_text(hu_upper, hu_lower):
    hu_cuo_upper, hu_cuo_lower = calculate_cuogua(hu_upper, hu_lower)
    hu_zong_upper, hu_zong_lower = calculate_zonggua(hu_upper, hu_lower)

    hu_cuo_detail = HEXAGRAM_DATA.get((hu_cuo_upper, hu_cuo_lower), {})
    hu_zong_detail = HEXAGRAM_DATA.get((hu_zong_upper, hu_zong_lower), {})

    hu_cuo_name = _hexagram_name(hu_cuo_upper, hu_cuo_lower)
    hu_zong_name = _hexagram_name(hu_zong_upper, hu_zong_lower)

    return (
        f"互卦之错卦为{hu_cuo_name}"
        f"（{hu_cuo_detail.get('ji_xiong', '中中卦')}），提示隐藏因素的反面压力："
        f"{'、'.join(hu_cuo_detail.get('core_meaning', ['互错暂缺'])[:3])}；"
        f"互卦之综卦为{hu_zong_name}"
        f"（{hu_zong_detail.get('ji_xiong', '中中卦')}），提示过程中的换位视角："
        f"{'、'.join(hu_zong_detail.get('core_meaning', ['互综暂缺'])[:3])}"
    )


def analyze_external_omen(omen_text):
    """梅花易数外应（克应）简析。"""
    text = (omen_text or "").strip()
    if not text:
        return {
            "level": "未记录",
            "tip": "未记录明显外应，仍以卦象、体用、动爻与月日关系为主。",
        }

    auspicious_words = [
        "笑", "喜", "吉", "好消息", "赞", "明亮", "阳光", "清风",
        "香", "鸟鸣", "音乐", "贵人", "顺利", "开门", "来电",
    ]
    inauspicious_words = [
        "哭", "吵", "骂", "摔", "碎", "跌", "坏", "断", "停电",
        "黑", "臭", "惊", "警报", "堵", "关门", "噪音", "病",
    ]

    good_hits = [word for word in auspicious_words if word in text]
    bad_hits = [word for word in inauspicious_words if word in text]

    if good_hits and not bad_hits:
        level = "偏吉"
        advice = "外应偏吉，可作为卦象中生扶、比和、贵人象的旁证。"
    elif bad_hits and not good_hits:
        level = "偏凶"
        advice = "外应偏凶，应重点检查卦中克、破、空亡与动爻压力。"
    elif good_hits and bad_hits:
        level = "吉凶相杂"
        advice = "外应吉凶并见，说明事情有转机也有干扰，不宜只取单一象。"
    else:
        level = "平"
        advice = "外应未命中明显吉凶关键词，可作为环境背景记录。"

    hits = good_hits + bad_hits
    hit_text = f"命中外应词：{'、'.join(hits)}。" if hits else ""
    return {
        "level": level,
        "tip": f"外应记录：{text}。{hit_text}{advice}",
    }


def _merge_traditional_decision(base_suggest, yongshen_system, bian_line_relation, external_omen_result):
    """把用神系统与动变回头生克纳入最终建议。"""
    evidence_score = float(yongshen_system.get("score", 0)) + float(bian_line_relation.get("score", 0))
    notes = []

    if evidence_score >= 5:
        notes.append("纳甲证据链偏强，用神、原神或动变后势能形成助力，可在现实条件允许时主动推进")
    elif evidence_score >= 2:
        notes.append("纳甲证据链略偏有力，但仍需按步骤推进，避免只凭卦象一次性押注")
    elif evidence_score <= -5:
        notes.append("纳甲证据链受制较重，用神与动变后势不足，当前不宜强推")
    elif evidence_score <= -2:
        notes.append("纳甲证据链偏弱，宜先补资源、避冲突、等时机，不宜急进")
    else:
        notes.append("纳甲证据链中平，应以现实证据、成本收益与可逆性来定取舍")

    relation = bian_line_relation.get("relation", "")
    if relation == "回头克":
        notes.append("动爻化回头克，尤其要防后续反噬、合同责任和资源消耗")
    elif relation == "回头生":
        notes.append("动爻化回头生，后续有补益迹象，但仍须看用神是否受空破")

    omen_level = external_omen_result.get("level", "")
    if omen_level == "偏凶":
        notes.append("外应偏凶，只作为旁证，执行前应加一道风险核验")
    elif omen_level == "偏吉":
        notes.append("外应偏吉，可作旁证，但不可替代现实判断")

    return f"{base_suggest}。{'；'.join(notes)}"


def interpret_hexagram(hexagram_info):
    """六爻重卦解卦核心逻辑（增强版：整合纳甲、体用、互错综卦）。"""
    upper_num = hexagram_info["upper_num"]
    lower_num = hexagram_info["lower_num"]
    lunar_info = hexagram_info["lunar_info"]
    dong_yao = hexagram_info["dong_yao"]
    upper_gua = hexagram_info["upper_gua"]
    lower_gua = hexagram_info["lower_gua"]
    question_text = hexagram_info.get("question", "")
    external_omen = hexagram_info.get("external_omen", "")

    # --- 1. 六十四卦信息 ---
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

    # --- 2. 五行生克与旺衰 ---
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

    # --- 3. 决策建议 ---
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

    # --- 4. 动爻与变卦 ---
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

    # --- 5. 互卦 ---
    hu_upper, hu_lower = calculate_hugua(upper_num, lower_num)
    hu_detail = HEXAGRAM_DATA.get((hu_upper, hu_lower), {})
    hu_name = hu_detail.get("name", f"{BAGUA_DATA[hu_upper]['name']}{BAGUA_DATA[hu_lower]['name']}")
    hu_tip = (
        f"互卦为{hu_name}"
        f"（{hu_detail.get('ji_xiong', '中中卦')}），揭示事情发展过程中的隐藏因素："
        f"{'、'.join(hu_detail.get('core_meaning', ['互卦暂缺'])[:3])}"
    )
    hu_cuo_zong_tip = _build_hu_cuo_zong_text(hu_upper, hu_lower)

    # --- 6. 错卦 ---
    cuo_upper, cuo_lower = calculate_cuogua(upper_num, lower_num)
    cuo_detail = HEXAGRAM_DATA.get((cuo_upper, cuo_lower), {})
    cuo_name = cuo_detail.get("name", f"{BAGUA_DATA[cuo_upper]['name']}{BAGUA_DATA[cuo_lower]['name']}")
    cuo_tip = (
        f"错卦为{cuo_name}"
        f"（{cuo_detail.get('ji_xiong', '中中卦')}），从相反角度审视："
        f"{'、'.join(cuo_detail.get('core_meaning', ['错卦暂缺'])[:3])}"
    )

    # --- 7. 综卦 ---
    zong_upper, zong_lower = calculate_zonggua(upper_num, lower_num)
    zong_detail = HEXAGRAM_DATA.get((zong_upper, zong_lower), {})
    zong_name = zong_detail.get("name", f"{BAGUA_DATA[zong_upper]['name']}{BAGUA_DATA[zong_lower]['name']}")
    zong_tip = (
        f"综卦为{zong_name}"
        f"（{zong_detail.get('ji_xiong', '中中卦')}），换位思考的视角："
        f"{'、'.join(zong_detail.get('core_meaning', ['综卦暂缺'])[:3])}"
    )

    # --- 8. 体用分析（梅花易数）---
    tiyong_info = identify_tiyong(upper_num, lower_num, dong_yao)
    tiyong_tip = _build_tiyong_text(tiyong_info)

    # --- 9. 装卦（京房纳甲）---
    solar = lunar_info.get("solar")
    zhuanggua_result = zhuang_gua_complete(
        upper_num,
        lower_num,
        solar=solar,
        lunar_info=lunar_info,
    )
    if dong_yao and 1 <= dong_yao <= 6:
        zhuanggua_result["lines"][dong_yao - 1]["is_dong"] = True
    refresh_line_strengths(zhuanggua_result)

    bian_zhuanggua_result = zhuang_gua_complete(
        bian_upper,
        bian_lower,
        solar=solar,
        lunar_info=lunar_info,
    )
    bian_line_relation = analyze_bian_line_relation(
        zhuanggua_result,
        bian_zhuanggua_result,
        dong_yao,
    )

    # --- 10. 六亲格局 ---
    liuqin_summary = analyze_liuqin_summary(zhuanggua_result, dong_yao=dong_yao)
    yongshen_system = analyze_yongshen_system(
        zhuanggua_result,
        question_text=question_text,
        dong_yao=dong_yao,
    )
    yongshen_name = yongshen_system["yongshen_name"]
    dizhi_relation_summary = analyze_dizhi_relation_summary(
        zhuanggua_result,
        dong_yao=dong_yao,
        yongshen_name=yongshen_name,
    )
    nayin_summary = analyze_nayin_summary(zhuanggua_result)
    liushen_zhihua_summary = analyze_liushen_zhihua_summary(zhuanggua_result)
    line_strength_summary = analyze_line_strength_summary(zhuanggua_result)
    zhuanggua_table = format_zhuanggua_table(zhuanggua_result, dong_yao=dong_yao)
    external_omen_result = analyze_external_omen(external_omen)
    traditional_evidence_chain = build_traditional_evidence_chain(
        zhuanggua_result,
        yongshen_system,
        bian_line_relation,
    )
    decision_suggest = _merge_traditional_decision(
        decision_suggest,
        yongshen_system,
        bian_line_relation,
        external_omen_result,
    )

    # 世爻六亲
    shishen_liuqin = get_shishen_liuqin(zhuanggua_result)
    shishen_info = LIUQIN_XIANGYI.get(shishen_liuqin, {})

    # 动爻六亲解读
    dong_yao_liuqin_tip = ""
    if dong_yao and 1 <= dong_yao <= 6:
        dong_line = zhuanggua_result["lines"][dong_yao - 1]
        dong_lq = dong_line["liuqin"]
        dong_ls = dong_line["liushen"]
        dong_cs = dong_line["changsheng"]
        dong_lq_info = LIUQIN_XIANGYI.get(dong_lq, {})
        dong_ls_info = LIUSHEN_XIANGYI.get(dong_ls, {})
        dong_yao_liuqin_tip = (
            f"动爻{dong_lq}发动（临{dong_ls}，处{dong_cs}之地），"
            f"{dong_lq_info.get('description', '')}。"
            f"六神{dong_ls}：{dong_ls_info.get('description', '')}"
        )

    # 六亲吉象解读
    liuqin_interpretation = _interpret_liuqin_pattern(zhuanggua_result, dong_yao)

    return {
        # 基础
        "gua_name": hexagram_detail["name"],
        "gua_ci": hexagram_detail["gua_ci"],
        "core_meaning": hexagram_detail["core_meaning"],
        "ji_xiong": ji_xiong,
        "ji_xiong_score": ji_xiong_score,
        # 五行
        "qian_yin_hou_guo": f"上卦{upper_gua['full_name']}为前因/当下，下卦{lower_gua['full_name']}为后果/未来",
        "sheng_ke_analysis": sheng_ke_text,
        "wang_shuai_analysis": f"上卦{upper_gua['name']}当季{upper_wang_shuai}，下卦{lower_gua['name']}当季{lower_wang_shuai}",
        # 动变
        "dong_yao_tip": dong_yao_tip,
        "yao_ci_tip": yao_ci_tip,
        "bian_gua_tip": bian_gua_tip,
        # 互错综
        "hu_gua_tip": hu_tip,
        "hu_cuo_zong_tip": hu_cuo_zong_tip,
        "cuo_gua_tip": cuo_tip,
        "zong_gua_tip": zong_tip,
        # 体用
        "tiyong_info": tiyong_info,
        "tiyong_tip": tiyong_tip,
        # 纳甲装卦
        "zhuanggua_table": zhuanggua_table,
        "zhuanggua_result": zhuanggua_result,
        "bian_zhuanggua_result": bian_zhuanggua_result,
        # 六亲
        "liuqin_summary": liuqin_summary,
        "shishen_liuqin": shishen_liuqin,
        "shishen_info": shishen_info,
        "yongshen_name": yongshen_name,
        "yongshen_system": yongshen_system,
        "yongshen_system_summary": yongshen_system["summary"],
        "dong_yao_liuqin_tip": dong_yao_liuqin_tip,
        "liuqin_interpretation": liuqin_interpretation,
        "dizhi_relation_summary": dizhi_relation_summary,
        "line_strength_summary": line_strength_summary,
        "bian_line_relation": bian_line_relation,
        "bian_line_relation_tip": bian_line_relation["summary"],
        "traditional_evidence_chain": traditional_evidence_chain,
        "nayin_summary": nayin_summary,
        "liushen_zhihua_summary": liushen_zhihua_summary,
        "external_omen_tip": external_omen_result["tip"],
        "external_omen_level": external_omen_result["level"],
        # 决策
        "decision_suggest": decision_suggest,
        # 兼容旧字段
        "naja_analysis": zhuanggua_table,
        "naja_info": zhuanggua_result,
    }


def _build_tiyong_text(tiyong_info):
    """构建体用分析文本。"""
    ti = tiyong_info
    text = (
        f"体卦：{ti['ti_gua_full']}（{ti['ti_element']}）— 代表求测者/主体\n"
        f"用卦：{ti['yong_gua_full']}（{ti['yong_element']}）— 代表所问之事/外部\n"
        f"体用关系：{ti['relation']}\n"
        f"判断：{ti['relation_desc']}"
    )

    # 体用生克所主具体事项
    yong_name = ti["yong_gua_name"]
    if yong_name in TIYONG_SHENG_KE_XIANG:
        xiang = TIYONG_SHENG_KE_XIANG[yong_name]
        if "用生体" in ti["relation"]:
            text += f"\n具体所主吉事：{xiang.get('sheng_ti', '')}"
        elif "用克体" in ti["relation"]:
            text += f"\n具体所主凶事：{xiang.get('ke_ti', '')}"
        elif "体生用" in ti["relation"]:
            text += f"\n泄气事项：{xiang.get('ke_ti', '')}"

    return text


def _interpret_liuqin_pattern(zhuanggua_result, dong_yao=None):
    """
    分析六亲格局。

    重点分析：
    1. 世爻六亲与旺衰
    2. 动爻六亲变化
    3. 六亲组合关系
    """
    lines = zhuanggua_result["lines"]
    tips = []

    shi_line = None
    for line in lines:
        if line["is_shi"]:
            shi_line = line
            break

    if shi_line:
        cs = shi_line["changsheng"]
        lq = shi_line["liuqin"]
        power = shi_line.get("changsheng_power", 0)
        if cs in ("长生", "临官", "帝旺"):
            tips.append(f"世爻{lq}得{cs}（力值{power:+g}），自身状态良好，根基扎实")
        elif cs in ("死", "墓", "绝"):
            tips.append(f"世爻{lq}处{cs}（力值{power:+g}），自身力量不足，宜先静养待机")
        if shi_line.get("line_status"):
            tips.append(f"世爻见{'、'.join(shi_line['line_status'])}，主体力量需打折看")

    if dong_yao and 1 <= dong_yao <= 6:
        dong_line = lines[dong_yao - 1]
        dong_lq = dong_line["liuqin"]

        if dong_lq == "子孙" and dong_line["changsheng"] in ("长生", "帝旺"):
            tips.append("动爻子孙旺动，福神有力，可化解灾厄")
        if dong_lq == "妻财" and dong_line["changsheng"] in ("长生", "帝旺"):
            tips.append("动爻妻财旺动，财爻得位，求财有利")
        if dong_lq == "官鬼" and dong_line["changsheng"] in ("长生", "帝旺"):
            tips.append("动爻官鬼旺动，需注意事业压力或健康问题")
        if dong_lq == "父母" and dong_line["changsheng"] in ("帝旺",):
            tips.append("动爻父母旺动，文书、考试、契约之事有利")
        if dong_lq == "兄弟" and dong_line["changsheng"] in ("帝旺",):
            tips.append("动爻兄弟旺动，竞争加剧，注意口舌破财")

        # 六神提示
        ls = dong_line["liushen"]
        if ls == "白虎":
            tips.append("动临白虎，事态急迫，宜果断处理")
        elif ls == "青龙":
            tips.append("动临青龙，有喜庆贵人相助之象")
        if dong_line.get("line_status"):
            tips.append(f"动爻见{'、'.join(dong_line['line_status'])}，应期与实际力量需谨慎判断")
        if dong_line.get("liushen_effect"):
            tips.append(dong_line["liushen_effect"])

    return "；".join(tips) if tips else "六亲格局平稳，无明显特殊变化"


def _build_single_gua_tiyong_text(gua_info, yao_list, wang_shuai):
    """三爻快占的单卦体用：以卦体旺衰与三爻阴阳分布为核心。"""
    if not yao_list:
        return ""

    yang_count = sum(1 for yao in yao_list if yao == 1)
    yin_count = len(yao_list) - yang_count
    position_names = ["初爻", "二爻", "三爻"]
    active_positions = [
        position_names[index]
        for index, yao in enumerate(yao_list)
        if yao == 1
    ]
    quiet_positions = [
        position_names[index]
        for index, yao in enumerate(yao_list)
        if yao == 0
    ]

    if wang_shuai in ("旺", "相"):
        season_tip = "卦体得令，单卦之体有力"
    elif wang_shuai in ("休",):
        season_tip = "卦体休气，宜守中待势"
    else:
        season_tip = "卦体失令，行动力量不足"

    if yang_count > yin_count:
        yao_tip = "阳多于阴，用在主动、外放、推进"
    elif yin_count > yang_count:
        yao_tip = "阴多于阳，用在收敛、承载、等待"
    else:
        yao_tip = "阴阳相停，宜先分清主次再动"

    active_text = "、".join(active_positions) if active_positions else "无"
    quiet_text = "、".join(quiet_positions) if quiet_positions else "无"
    return (
        f"单卦体为{gua_info['full_name']}（{gua_info['element']}），{season_tip}；"
        f"{yao_tip}；阳爻在{active_text}，阴爻在{quiet_text}"
    )


def interpret_three_yao(three_yao_info):
    """三爻快占解卦逻辑（增强版：增加体用与互卦分析）。"""
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

    # 体用分析（三爻快占用单卦，以旺衰论吉凶、以物象断事情）
    tiyong_note = ""
    single_tiyong_tip = ""
    yao_list = three_yao_info.get("yao_list", [])
    if yao_list:
        yao_desc = "".join(["⚊" if y == 1 else "⚋" for y in yao_list])
        tiyong_note = f"爻象：{yao_desc}（{'阳' if yao_list[0] == 1 else '阴'}{'阳' if yao_list[1] == 1 else '阴'}{'阳' if yao_list[2] == 1 else '阴'}）"
        if wang_shuai in ("旺", "相"):
            tiyong_note += "，当季得令，卦象有力"
        elif wang_shuai in ("囚", "死"):
            tiyong_note += "，当季失令，卦象力弱"
        single_tiyong_tip = _build_single_gua_tiyong_text(gua_info, yao_list, wang_shuai)

    external_omen_result = analyze_external_omen(three_yao_info.get("external_omen", ""))

    return {
        "core_tip": core_tip,
        "meaning_tip": meaning_tip,
        "direction_tip": direction_tip,
        "weather_tip": weather_tip,
        "wu_xiang_tip": wu_xiang_tip,
        "suggest": suggest,
        "tiyong_note": tiyong_note,
        "single_tiyong_tip": single_tiyong_tip,
        "external_omen_tip": external_omen_result["tip"],
        "external_omen_level": external_omen_result["level"],
    }
