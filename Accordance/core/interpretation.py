# -*- coding: utf-8 -*-
"""解卦核心逻辑。整合京房纳甲、梅花易数体用、互错综卦等多维分析。"""

from config.hexagram_data import HEXAGRAM_DATA, JI_XIONG_LEVEL
from config.hexagram_calibration import get_hexagram_calibration, build_calibration_tip
from config.wuxing_rules import (
    WUXING_SHENG, WUXING_KE, WUXING_WANG_SHUAI,
)
from config.bagua_data import (
    BAGUA_DATA, TIYONG_SHENG_KE_XIANG,
)
from config.naja_data import (
    LIUQIN_XIANGYI, LIUSHEN_XIANGYI,
)
from config.yijing_philosophy import (
    build_human_guidance, get_hexagram_wisdom, get_situation_advice,
    HUMAN_AGENCY_REMINDER,
)
from config.daxiang_data import get_daxiang
from config.tuanzhuan_data import get_tuanzhuan
from config.shensha_data import analyze_shensha_summary
from config.traditional_sources import build_source_trace, build_reality_check
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
    analyze_dong_yao_pattern, analyze_hexagram_liuhe_liuchong,
    select_primary_yongshen, analyze_guashen,
)


def _join_relation(sheng_relation, ke_relation, bihe_relation=""):
    relation_list = []
    if sheng_relation:
        relation_list.append(sheng_relation)
    if ke_relation:
        relation_list.append(ke_relation)
    if bihe_relation:
        relation_list.append(bihe_relation)
    return "；".join(relation_list) if relation_list else "上下卦五行无直接生克关系"


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
        f"互之错：{hu_cuo_name}"
        f"（{hu_cuo_detail.get('ji_xiong', '中中卦')}）"
        f"{'、'.join(hu_cuo_detail.get('core_meaning', ['暂缺'])[:2])}；"
        f"互之综：{hu_zong_name}"
        f"（{hu_zong_detail.get('ji_xiong', '中中卦')}）"
        f"{'、'.join(hu_zong_detail.get('core_meaning', ['暂缺'])[:2])}"
    )


def analyze_external_omen(omen_text):
    """梅花易数外应（克应）简析。"""
    text = (omen_text or "").strip()
    if not text:
        return {"level": "未记录", "tip": ""}

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
        advice = "外应偏吉，可作为生扶、比和、贵人象的旁证"
    elif bad_hits and not good_hits:
        level = "偏凶"
        advice = "外应偏凶，应重点检查卦中克、破、空亡与动爻压力"
    elif good_hits and bad_hits:
        level = "吉凶相杂"
        advice = "外应吉凶并见，有转机也有干扰"
    else:
        level = "平"
        advice = "外应无明显吉凶关键词"

    hits = good_hits + bad_hits
    hit_text = f"命中外应词：{'、'.join(hits)}。" if hits else ""
    return {"level": level, "tip": f"外应：{text}。{hit_text}{advice}"}


def _build_specific_judgment(zhuanggua_result, yongshen_system, bian_line_relation,
                              tiyong_info, dong_yao, question_text, hexagram_detail):
    """
    生成具体的传统断语。

    整合用神系统、动变回头生克、世应关系、体用生克、
    月日影响，输出精准的传统六爻断语，杜绝模糊空泛。
    """
    parts = []
    yongshen_name = yongshen_system.get("yongshen_name", "世爻")
    yongshen_element = yongshen_system.get("yongshen_element", "土")
    yong_score = yongshen_system.get("score", 0)
    bian_score = bian_line_relation.get("score", 0)
    bian_relation = bian_line_relation.get("relation", "")
    inference = yongshen_system.get("inference", {})
    category = inference.get("category", "泛问")

    lines = zhuanggua_result.get("lines", [])
    shi_line = next((l for l in lines if l.get("is_shi")), None)
    dong_line = lines[dong_yao - 1] if dong_yao and 1 <= dong_yao <= 6 else None

    # --- 用神状态 ---
    yong_lines = yongshen_system.get("yong_lines", [])
    if yong_lines:
        best_yong = max(yong_lines, key=lambda l: l.get("strength_score", -99))
        yong_status = best_yong.get("strength_level", "平稳")
        yong_cs = best_yong.get("changsheng", "")
        yong_pos = best_yong.get("position_name", "")
        yong_status_text = f"用神{yongshen_name}现于{yong_pos}，{yong_status}（{yong_cs}）"
        if best_yong.get("line_status"):
            yong_status_text += f"，见{'、'.join(best_yong['line_status'])}"
        if best_yong.get("is_dong"):
            yong_status_text += "，发动"
        if best_yong.get("is_shi"):
            yong_status_text += "，持世"
    else:
        fushen = yongshen_system.get("fushen", {})
        if fushen.get("has_fushen"):
            yong_status_text = f"用神{yongshen_name}本卦不现，伏神待查"
        else:
            yong_status_text = f"用神{yongshen_name}不现，以世应动爻代断"

    parts.append(yong_status_text)

    # --- 原神 ---
    yuan_lines = yongshen_system.get("yuan_lines", [])
    if yuan_lines:
        best_yuan = max(yuan_lines, key=lambda l: l.get("strength_score", -99))
        yuan_element = yongshen_system.get("yuan_element", "")
        if best_yuan.get("strength_score", 0) >= 2:
            parts.append(f"原神({yuan_element})有力，{'发动来生' if best_yuan.get('is_dong') else '可生用神'}")
        elif best_yuan.get("strength_score", 0) >= 0:
            parts.append(f"原神({yuan_element})平平，生扶之力有限")
        else:
            parts.append(f"原神({yuan_element})衰弱受制，无力生用神")

    # --- 忌神 ---
    ji_lines = yongshen_system.get("ji_lines", [])
    if ji_lines:
        worst_ji = max(ji_lines, key=lambda l: l.get("strength_score", -99))
        ji_element = yongshen_system.get("ji_element", "")
        if worst_ji.get("strength_score", 0) >= 2:
            parts.append(f"忌神({ji_element})旺相{'发动来克' if worst_ji.get('is_dong') else '克用神'}，需防阻碍")
        elif worst_ji.get("strength_score", 0) >= 0:
            parts.append(f"忌神({ji_element})平平，克制之力有限")
        else:
            parts.append(f"忌神({ji_element})衰弱，不足以伤用神")

    # --- 动变 ---
    if bian_relation == "回头生":
        parts.append("动变回头生，后势有回补助力")
    elif bian_relation == "回头克":
        parts.append("动变回头克，需防后续反噬与资源消耗")
    elif bian_relation == "化泄":
        parts.append("动变化泄，付出多而回报少")
    elif bian_relation == "化比和":
        parts.append("动变比和，事情延续性较强")

    # --- 世爻 ---
    if shi_line and dong_line and shi_line.get("position") == dong_yao:
        parts.append("世爻发动，自身必有变动")
    if shi_line:
        shi_cs = shi_line.get("changsheng", "")
        if shi_cs in ("长生", "临官", "帝旺"):
            parts.append(f"世爻得{shi_cs}，自身状态良好")
        elif shi_cs in ("死", "墓", "绝"):
            parts.append(f"世爻处{shi_cs}，自身力量不足，宜静养待机")

    # --- 体用 ---
    tiyong_relation = tiyong_info.get("relation", "")
    if tiyong_relation == "用生体":
        parts.append("体用：用生体，外界助我，有进益之喜")
    elif tiyong_relation == "用克体":
        parts.append("体用：用克体，受人牵制，诸事难成")
    elif tiyong_relation == "体生用":
        parts.append("体用：体生用，泄气耗力，付出多回报少")
    elif tiyong_relation == "体克用":
        parts.append("体用：体克用，辛苦费力但能成事")
    elif tiyong_relation == "比和":
        parts.append("体用：比和，五行相同，百事顺遂")

    # --- 世应关系 ---
    ying_line = next((l for l in lines if l.get("is_ying")), None)
    if shi_line and ying_line:
        shi_ying_relations = _build_shi_ying_analysis(shi_line, ying_line, dong_line)
        if shi_ying_relations:
            parts.append(shi_ying_relations)

    # --- 卦象特殊格局 ---
    hexagram_pattern = _analyze_hexagram_pattern(zhuanggua_result, hexagram_detail)
    if hexagram_pattern:
        parts.append(hexagram_pattern)

    # --- 独发独静分析 ---
    dong_pattern = analyze_dong_yao_pattern(zhuanggua_result, dong_yao)
    pattern_score_mod = 0.0
    if dong_pattern and dong_pattern.get("pattern") != "六爻俱静":
        parts.append(dong_pattern["significance"])
        pattern_score_mod = dong_pattern.get("score_mod", 0)

    # --- 六合六冲分析 ---
    hex_name = hexagram_detail.get("name", "")
    liuhe_chong = analyze_hexagram_liuhe_liuchong(hex_name)
    liuhe_chong_score_mod = 0.0
    if liuhe_chong:
        parts.append(f"卦象格局：{liuhe_chong['pattern']}——{liuhe_chong['analysis']}")
        liuhe_chong_score_mod = liuhe_chong.get("score_mod", 0)

    # --- 应期分析 ---
    timing = _analyze_timing(zhuanggua_result, yongshen_system, dong_line)
    if timing:
        parts.append(timing)

    # --- 综合结论 ---
    combined_score = yong_score + bian_score * 0.6 + pattern_score_mod + liuhe_chong_score_mod
    if shi_line and dong_line:
        if dong_line.get("liuqin") == yongshen_name:
            combined_score += 1.0
        if dong_line.get("is_shi"):
            combined_score += 0.5

    # 按问事类别给出具体断语
    conclusion = _build_category_conclusion(
        category, yongshen_name, combined_score, yong_lines,
        yuan_lines, ji_lines, bian_relation, shi_line, dong_line,
        timing,
    )

    return {
        "detail": "；".join(parts),
        "conclusion": conclusion,
        "combined_score": round(combined_score, 1),
        "timing": timing,
    }


def _analyze_timing(zhuanggua_result, yongshen_system, dong_line):
    """分析应期（时间判断）。"""
    tips = []
    yong_lines = yongshen_system.get("yong_lines", [])
    fushen = yongshen_system.get("fushen", {})

    has_xk_or_yp = False
    # 旬空应期
    for line in (yong_lines or []):
        if line.get("is_xunkong"):
            dizhi = line.get("dizhi", "")
            tips.append(f"用神逢{dizhi}旬空，待出空（{dizhi}填实）之日/月为应期")
            has_xk_or_yp = True
            break

    # 月破应期
    for line in (yong_lines or []):
        if line.get("is_yuepo"):
            dizhi = line.get("dizhi", "")
            tips.append(f"用神逢{dizhi}月破，待出破或逢合之日/月为应期")
            has_xk_or_yp = True
            break

    # 伏神应期
    if not yong_lines and fushen.get("has_fushen"):
        items = fushen.get("items", [])
        if items:
            fushen_dizhi = items[0].get("fushen_dizhi", "")
            relation = items[0].get("relation", "")
            if "得扶" in relation or "同气" in relation:
                tips.append(f"伏神{fushen_dizhi}得飞神生扶，待{fushen_dizhi}出现之日/月为应期")
            elif "受压" in relation or "泄气" in relation:
                tips.append(f"伏神{fushen_dizhi}受飞神所制，需待冲去飞神之日/月方能出现")

    # 动爻应期
    if dong_line:
        dong_dizhi = dong_line.get("dizhi", "")
        if dong_line.get("line_status"):
            if "旬空" in dong_line.get("line_status", []):
                tips.append(f"动爻逢{dong_dizhi}旬空，出空之日/月为发动应期")

    # 用神入墓应期
    if not has_xk_or_yp and yong_lines:
        for line in yong_lines[:1]:
            cs = line.get("changsheng", "")
            dizhi = line.get("dizhi", "")
            if cs == "墓":
                tips.append(f"用神入墓于{dizhi}，待冲墓（冲{dizhi}）之日/月方能出墓为应期")
                has_xk_or_yp = True
                break

    # 用神被合应期
    if not has_xk_or_yp and yong_lines:
        for line in yong_lines[:1]:
            dizhi = line.get("dizhi", "")
            month_rels = line.get("month_relations", [])
            day_rels = line.get("day_relations", [])
            if "合" in month_rels:
                from config.wuxing_rules import DIZHI_HE
                he_target = DIZHI_HE.get(dizhi, "")
                tips.append(f"用神{dizhi}与月建相合，待冲开合局（冲{he_target}或冲{dizhi}）之日/月为应期")
                has_xk_or_yp = True
                break
            if "合" in day_rels:
                from config.wuxing_rules import DIZHI_HE
                he_target = DIZHI_HE.get(dizhi, "")
                tips.append(f"用神{dizhi}与日辰相合，短期被绊住，待冲开之日为应期")
                has_xk_or_yp = True
                break

    # 用神绝处逢生应期
    if not has_xk_or_yp and yong_lines:
        for line in yong_lines[:1]:
            cs = line.get("changsheng", "")
            if cs == "绝":
                tips.append("用神处绝地，然绝处逢生——待长生之地或原神旺相之时为转机")
                has_xk_or_yp = True
                break

    # 用神安静应期（没有旬空/月破时才提示）
    if not has_xk_or_yp and yong_lines and not any(l.get("is_dong") for l in yong_lines):
        for line in yong_lines[:1]:
            dizhi = line.get("dizhi", "")
            tips.append(f"用神安静，待逢值（{dizhi}出现）或逢冲之日/月为应期")

    # 动爻被合应期（动逢合则绊住）
    if dong_line and not has_xk_or_yp:
        dong_dizhi = dong_line.get("dizhi", "")
        day_rels = dong_line.get("day_relations", [])
        month_rels = dong_line.get("month_relations", [])
        if "合" in day_rels:
            tips.append(f"动爻{dong_dizhi}被日辰合住，暂时不能发力，待冲开之日为发动应期")
        elif "合" in month_rels:
            tips.append(f"动爻{dong_dizhi}被月建合住，当月难发力，待次月冲开为应期")

    return "；".join(tips) if tips else ""


def _build_shi_ying_analysis(shi_line, ying_line, dong_line):
    """分析世应关系。"""
    shi_dizhi = shi_line.get("dizhi", "")
    ying_dizhi = ying_line.get("dizhi", "")
    shi_lq = shi_line.get("liuqin", "")
    ying_lq = ying_line.get("liuqin", "")

    from config.wuxing_rules import DIZHI_CHONG, DIZHI_HE, DIZHI_XING, WUXING_SHENG, WUXING_KE
    relations = []
    if DIZHI_CHONG.get(shi_dizhi) == ying_dizhi:
        relations.append("世应相冲，双方立场对立，事情多有冲突")
    if DIZHI_HE.get(shi_dizhi) == ying_dizhi:
        relations.append("世应相合，双方关系融洽，事情易成")

    shi_el = shi_line.get("dizhi_wuxing", "")
    ying_el = ying_line.get("dizhi_wuxing", "")
    if WUXING_SHENG.get(ying_el) == shi_el:
        relations.append("应生世，对方主动来助，于我有益")
    elif WUXING_KE.get(ying_el) == shi_el:
        relations.append("应克世，对方给我压力，需谨慎应对")
    elif WUXING_SHENG.get(shi_el) == ying_el:
        relations.append("世生应，我主动付出，耗力为他人")
    elif WUXING_KE.get(shi_el) == ying_el:
        relations.append("世克应，我能掌控局面")
    elif shi_el == ying_el:
        relations.append("世应同气，双方势均力敌")

    if shi_lq == ying_lq:
        relations.append(f"世应同为{shi_lq}，所求之事与此六亲密切相关")

    return "；".join(relations) if relations else ""


def _analyze_hexagram_pattern(zhuanggua_result, hexagram_detail):
    """分析卦象特殊格局：六合卦、六冲卦、归魂卦、游魂卦等。"""
    patterns = []
    palace_role = zhuanggua_result.get("palace_role", "")

    if palace_role == "归魂":
        patterns.append("此为归魂卦，事有归根复命之象。问出行宜归，问失物易回，问事业宜守不宜变")
    elif palace_role == "游魂":
        patterns.append("此为游魂卦，事有飘荡不定之象。变动较多，需明确方向再行动，不宜贸然决定")

    # 八纯卦（六冲卦）
    hexagram_name = hexagram_detail.get("name", "")
    pure_hexagrams = {"乾为天", "兑为泽", "离为火", "震为雷", "巽为风", "坎为水", "艮为山", "坤为地"}
    if hexagram_name in pure_hexagrams:
        patterns.append("此为八纯六冲卦，事多散乱不长久。宜速决不宜拖延，长期之事需防变动反复")

    return "；".join(patterns) if patterns else ""


def _build_category_conclusion(category, yongshen_name, score, yong_lines,
                                yuan_lines, ji_lines, bian_relation,
                                shi_line, dong_line, timing=""):
    """根据问事类别生成具体结论断语，融入传统六爻断卦用语与人为本考量。"""
    has_yong = bool(yong_lines)
    yong_strong = any(l.get("strength_score", 0) >= 2 for l in yong_lines) if yong_lines else False
    yong_weak = all(l.get("strength_score", 0) < 0 for l in yong_lines) if yong_lines else True
    yong_appears = any(not (l.get("line_status") or l.get("is_xunkong")) for l in yong_lines) if yong_lines else False
    yuan_strong = any(l.get("strength_score", 0) >= 2 for l in yuan_lines) if yuan_lines else False
    ji_strong = any(l.get("strength_score", 0) >= 2 for l in ji_lines) if ji_lines else False
    has_huike = bian_relation == "回头克"
    has_huisheng = bian_relation == "回头生"
    has_huaxie = bian_relation == "化泄"
    shi_yong_tongwei = shi_line and yong_lines and shi_line.get("liuqin") == yongshen_name

    def _append_timing(text):
        return f"{text}。{timing}" if timing else text

    # ── 疾病病象（官鬼为病，子孙为医药）──
    if "疾病病象" in category:
        if not has_yong:
            base = "病象官鬼不现，未必是大病之象，但不可据此掉以轻心。宜以现实症状和检查结果为准"
        elif yong_strong and not ji_strong:
            base = "官鬼病象旺而子孙制鬼不显，病势或压力较重。宜尽快检查、就医，不宜拖延或自行硬扛"
        elif yong_strong and ji_strong:
            base = "官鬼病象虽旺，但子孙制鬼有力，治疗、药物或休养能起作用。按医嘱处理，忌反复更改方案"
        elif yong_weak:
            base = "官鬼病象偏弱，当前压力可控。仍需观察症状变化，保持规律作息，不可因卦象轻忽现实风险"
        elif has_huike:
            base = "动变回头克病象，有制病之机。若现实治疗方向明确，可坚持观察效果"
        elif has_huisheng:
            base = "动变回头生病象，需防症状反复或压力加重。宜提前复查，少冒险消耗"
        else:
            base = "病象中平，吉凶未定。应以检查、医嘱和身体反馈为第一依据，卦象只作提醒"
        return _append_timing(base)

    # ── 医药治疗（子孙为医药福神）──
    if "医药治疗" in category:
        if yong_strong and yong_appears:
            base = "子孙医药福神旺相，治疗、药物、休养方向较有利。宜按计划执行，观察阶段性反馈"
        elif yong_strong and not yong_appears:
            base = "子孙有力但见空破，药效或恢复有延迟。宜复核方案、耐心等待，不宜频繁换法"
        elif yong_weak:
            base = "子孙医药之力偏弱，治疗效果可能慢或不足。宜请专业医生复核，补足检查与护理"
        elif has_huike:
            base = "动变回头克子孙，治疗过程需防反复、药物不合或执行中断。应及时反馈给医生"
        elif has_huisheng:
            base = "动变回头生子孙，后续恢复力增强。坚持正规处理，勿因短期好转自行停药停治"
        else:
            base = "医药象中平，重在现实执行。按医嘱、检查结果和身体反馈推进"
        return _append_timing(base)

    # ── 寻物失物（妻财为物象）──
    if "寻物" in category:
        if yong_strong and yong_appears:
            base = "财爻物象有根，物品仍有找回希望。先在最后出现的小范围内，按卦象方位、遮挡处和收纳处细查"
        elif not has_yong:
            base = "财爻不现，物象隐伏。宜看伏神、卦身与动爻，先回想最后经手路径，范围过大则改用六爻详占"
        elif yong_strong and not yong_appears:
            base = "物象虽有根但逢空破，可能被遮住、夹住、收纳或暂时离开视线。待出空、填破或冲开之时更易发现"
        elif yong_weak:
            base = "财爻物象偏弱，找回难度较大。优先确认是否已被移动、借走、丢弃或超出原搜索范围"
        elif has_huike:
            base = "动变回头克财，物品有损坏、转移或被他物压制之象。查被压住、袋中夹层和移动路线"
        else:
            base = "寻物象中平，先缩小范围再找。不要边找边扩大区域，按最后见到处逐层排查"
        return _append_timing(base)

    # ── 出行行人（子孙为平安顺遂）──
    if "出行" in category:
        if yong_strong and yong_appears and not ji_strong:
            base = "子孙平安象有力，出行整体可行。仍需核对天气、路况、票务与时间余量"
        elif yong_strong and ji_strong:
            base = "平安象有力但阻力同现，行程可走但会有竞争、延误或手续压力。宜预留备选方案"
        elif yong_weak:
            base = "子孙平安象偏弱，出行宜谨慎。若遇天气、身体、票务或路况不稳，宁可延后或改线"
        elif has_huike:
            base = "动变回头克子孙，途中需防反复、延误或小故障。提前检查车辆、证件与时间安排"
        elif has_huisheng:
            base = "动变回头生子孙，先有不顺后有缓解。按计划推进时保留余量即可"
        else:
            base = "出行象中平，可走但不宜赶急。先把现实风险排查清楚"
        return _append_timing(base)

    # ── 财货运（妻财为用神）──
    if "财货" in category or "妻财" == yongshen_name:
        if yong_strong and yuan_strong and not ji_strong:
            base = "财爻旺相得原神生扶，求财大有利。宜把握时机主动出击，但需见好即收、不可过度贪婪"
        elif yong_strong and ji_strong:
            base = "财爻虽旺但忌神同强，求财有竞争消耗之象。宜速战速决、不宜久持长线，注意合伙中的利益分配"
        elif yong_weak and ji_strong:
            base = "财爻衰弱而忌神猖獗，破耗之象明显。守成为上，暂勿投资扩张，先控制支出、巩固现金流"
        elif not has_yong:
            base = "财爻不现于卦中，求财时机未到。宜耐心等待，切忌急于求成。若伏神有气得扶，则待出伏之日可图"
        elif has_huike:
            base = "动变回头克财，求财须防前赚后赔。宜小步试探，见利即收，不可贪多冒进"
        elif has_huisheng:
            base = "动变回头生扶财爻，求财后势有补益。可循序渐进投入，待势头明朗后再加码"
        elif has_huaxie:
            base = "动变化泄财气，投入多而回报薄，或赚到手的钱因事消耗。宜精打细算、控制成本"
        elif shi_yong_tongwei and yong_strong:
            base = "财爻持世旺相，求财主动有利，自身就是财富的源头。自信果断地去做，但莫忘合法合规"
        elif score >= 3:
            base = "用神证据偏强，求财总体有利。可按计划推进，但需关注忌神动向与动变风险"
        elif score >= 0:
            base = "用神力量中平，求财宜稳中求进。不宜大举投入，以小步试探为好"
        else:
            base = "用神受制偏弱，求财不顺利。宜守不宜攻，以节省开支、稳固现有资源为主，静待时运好转"
        return _append_timing(base)

    # ── 官职事业运（官鬼为用神）──
    if "官职" in category or "官鬼" == yongshen_name:
        if "婚恋" in category:
            # 女占婚恋的官鬼处理，已在上面婚恋分支处理
            pass
        else:
            if yong_strong and yuan_strong and not ji_strong:
                base = "官爻旺相得原神生扶，事业运佳、升迁有望。宜积极争取机会，展现能力，但戒骄戒躁"
            elif yong_strong and ji_strong:
                base = "官爻虽旺但忌神亦强，事业有竞争压力，或遇小人阻碍。宜低调行事，以实力服人而非正面冲突"
            elif yong_weak:
                base = "官爻衰弱，事业近期难有突破。不宜跳槽或创业，宜韬光养晦、提升自我，待机而发"
            elif has_huike:
                base = "动变回头克官，事业须防后续变故或上级不满。做好分内之事、留好工作记录，不可轻易冒险"
            elif has_huisheng:
                base = "动变回头生官，事业后势有贵人扶持或机会再现。坚持下去可成，但不可松懈"
            elif score >= 2:
                base = "用神证据偏有利，事业可按计划推进。专心致志、稳扎稳打"
            elif score >= -1:
                base = "用神力量中平，事业宜求稳。不急功近利，也不妄自菲薄，踏实做好每一件小事"
            else:
                base = "用神受制较重，事业宜守不宜攻。不轻易辞职或转换方向，待自身状态与时机更好时再图进取"
            return _append_timing(base)

    # ── 婚恋感情 ──
    if "婚恋" in category:
        if yong_strong and yong_appears and score >= 2:
            base = "用神旺相有根，感情发展有利。可主动推进关系、增进了解，但水到渠成比强求更长久"
        elif yong_strong and not yong_appears:
            base = "用神旺但逢空破，感情表面不错却有隐忧。多沟通了解彼此真实想法，勿只看表面"
        elif yong_weak:
            base = "用神衰弱，感情近期难有实质性突破。宜顺其自然、先做好自己，不必强求结果"
        elif has_huike:
            base = "动变回头克，感情须防反复与矛盾激化。沟通比冷战好，坦诚比猜忌好，给对方也给自已空间"
        elif has_huisheng:
            base = "动变回头生，感情后势有回暖迹象。耐心经营、真诚相待，不可急于求成"
        elif score >= 0:
            base = "用神力量中平，感情宜顺其自然。不被一时情绪左右，以平常心相待"
        else:
            base = "用神受制偏弱，感情之事暂时不宜主动强求。先观己身、修身养性，好的感情需要双方都准备好的时机"
        return _append_timing(base)

    # ── 文书考试（父母为用神）──
    if "文书" in category or "父母" == yongshen_name:
        if yong_strong and yuan_strong:
            base = "父母爻旺相得生，文书、考试、契约之事大吉。宜认真准备、积极应试，踏实付出必有收获"
        elif yong_strong:
            base = "父母爻旺相，文书考试基本有利。但原神不显，需要更加努力，不可仅寄希望于运气"
        elif yong_weak:
            base = "父母爻衰弱，文书考试需加倍用功。不要找捷径，扎实的学习和准备是唯一的保障"
        elif has_huike:
            base = "动变回头克父母爻，考试或文书办理可能出现意外。提早准备、留出余量时间，做好备选方案"
        elif score >= 1:
            base = "用神证据偏有利，文书考试之事可按计划推进。保持平常心、稳定发挥"
        else:
            base = "用神受制偏弱，文书之事恐有波折。仔细核对材料、避免疏漏，考试则需加倍努力"
        return _append_timing(base)

    # ── 子女福神（子孙为用神）──
    if "子女" in category or "子孙" == yongshen_name:
        if yong_strong:
            base = "子孙爻旺相，子女之事顺利，福神得力可解灾厄。医药、娱乐、创意类事务也有利"
        elif yong_weak:
            base = "子孙爻衰弱，子女之事或有隐忧。多加关注陪伴，但不必过度焦虑，耐心是最佳良药"
        elif has_huike:
            base = "动变回头克子孙，须防子女健康或情绪波动。提前关注、及时沟通，防患于未然"
        elif score >= 1:
            base = "用神证据偏有利，所问之事可乐观以待。但乐不忘忧，保持适度警觉"
        else:
            base = "用神受制偏弱，宜谨慎行事、多做准备。小心驶得万年船"
        return _append_timing(base)

    # ── 泛问 / 综合断语 ──
    if score >= 4:
        base = "用神旺相有力，原神生扶到位，忌神不兴，所问之事可积极推进、顺势而为。但即使大吉，也需保持谦卑敬畏之心——骄兵必败，天道忌盈"
    elif score >= 1.5:
        base = "用神有根，整体可推进。但需注意忌神干扰与动变风险，稳中求进、步步为营。保持警觉比盲目乐观更重要"
    elif score >= -1:
        base = "用神力量中平，吉凶参半。此时最考验人的判断力和耐心——不急不躁、审慎决策，做好两手准备"
    elif score >= -3:
        base = "用神偏弱受制，阻力较大。宜先收敛观察、补足短板。这不是放弃，而是为更好的时机积蓄力量"
    else:
        base = "用神受制严重，强行推进恐有损失。以静制动、隐忍待机不是懦弱，而是对时势的尊重。守得云开见月明"
    return _append_timing(base)


def interpret_hexagram(hexagram_info):
    """六爻重卦解卦核心逻辑。"""
    upper_num = hexagram_info["upper_num"]
    lower_num = hexagram_info["lower_num"]
    lunar_info = hexagram_info["lunar_info"]
    dong_yao = hexagram_info["dong_yao"]
    upper_gua = hexagram_info["upper_gua"]
    lower_gua = hexagram_info["lower_gua"]
    question_text = hexagram_info.get("question", "")
    external_omen = hexagram_info.get("external_omen", "")

    # --- 六十四卦信息 ---
    hexagram_detail = HEXAGRAM_DATA.get(
        (upper_num, lower_num),
        {
            "name": f"{upper_gua['name']}{lower_gua['name']}",
            "core_meaning": upper_gua["core_meaning"] + lower_gua["core_meaning"],
            "ji_xiong": "中中卦",
            "gua_ci": "卦辞暂缺",
            "yao_ci": ["初爻暂缺"] * 6,
        },
    )

    # --- 五行生克与旺衰 ---
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

    if WUXING_SHENG[upper_element] == lower_element:
        if upper_power >= 2:
            sheng_relation = f"上卦{upper_gua['name']}生扶下卦{lower_gua['name']}，顺势发展"
        else:
            sheng_relation = f"上卦{upper_gua['name']}生扶下卦{lower_gua['name']}，但上卦力不足"
    elif WUXING_SHENG[lower_element] == upper_element:
        if lower_power >= 2:
            sheng_relation = f"下卦{lower_gua['name']}生扶上卦{upper_gua['name']}，结果反哺当下"
        else:
            sheng_relation = f"下卦{lower_gua['name']}生扶上卦{upper_gua['name']}，但下卦力不足"

    if WUXING_KE[upper_element] == lower_element:
        if upper_power >= lower_power * 1.5:
            ke_relation = f"上卦{upper_gua['name']}强力克下卦{lower_gua['name']}，当下阻碍结果"
        elif upper_power < lower_power:
            ke_relation = f"上卦{upper_gua['name']}弱克下卦{lower_gua['name']}，反易被牵制"
        else:
            ke_relation = f"上卦{upper_gua['name']}克下卦{lower_gua['name']}，当下阻碍结果"
    elif WUXING_KE[lower_element] == upper_element:
        if lower_power >= upper_power * 1.5:
            ke_relation = f"下卦{lower_gua['name']}强力克上卦{upper_gua['name']}，结果反噬当下"
        elif lower_power < upper_power:
            ke_relation = f"下卦{lower_gua['name']}弱克上卦{upper_gua['name']}，反噬有限"
        else:
            ke_relation = f"下卦{lower_gua['name']}克上卦{upper_gua['name']}，结果反噬当下"

    if upper_element == lower_element:
        bihe_relation = f"上下卦五行比和，同属{upper_element}，同气相求"

    sheng_ke_text = _join_relation(sheng_relation, ke_relation, bihe_relation)
    ji_xiong = hexagram_detail.get("ji_xiong", "中中卦")
    ji_xiong_score = JI_XIONG_LEVEL.get(ji_xiong, 3)
    hexagram_calibration = get_hexagram_calibration(hexagram_detail["name"])
    calibration_tip = build_calibration_tip(hexagram_detail["name"])

    # --- 动爻与变卦 ---
    dong_yao_meaning = {
        1: "初爻动，事情初始阶段有变",
        2: "二爻动，人际/环境层面有变",
        3: "三爻动，自身/行动层面有变",
        4: "四爻动，外部/上级层面有变",
        5: "五爻动，核心/高峰阶段有变",
        6: "上爻动，终局/收尾阶段有变",
    }
    dong_yao_tip = dong_yao_meaning.get(dong_yao, f"第{dong_yao}爻发动")

    bian_upper, bian_lower = calculate_bian_gua(upper_num, lower_num, dong_yao)
    default_bian_name = f"{BAGUA_DATA[bian_upper]['name']}{BAGUA_DATA[bian_lower]['name']}"
    bian_detail = HEXAGRAM_DATA.get((bian_upper, bian_lower), {})
    bian_gua_tip = (
        f"变卦：{bian_detail.get('name', default_bian_name)}"
        f"（{bian_detail.get('ji_xiong', '中中卦')}）→ "
        f"{'、'.join(bian_detail.get('core_meaning', ['暂缺'])[:3])}"
    )

    yao_ci_list = hexagram_detail.get("yao_ci") or ["暂缺"] * 6
    yao_ci = yao_ci_list[dong_yao - 1] if 0 <= dong_yao - 1 < len(yao_ci_list) else "暂缺"
    yao_ci_tip = f"动爻爻辞：{yao_ci}"

    # --- 互卦 ---
    hu_upper, hu_lower = calculate_hugua(upper_num, lower_num)
    hu_detail = HEXAGRAM_DATA.get((hu_upper, hu_lower), {})
    hu_name = hu_detail.get("name", f"{BAGUA_DATA[hu_upper]['name']}{BAGUA_DATA[hu_lower]['name']}")
    hu_tip = (
        f"互卦：{hu_name}"
        f"（{hu_detail.get('ji_xiong', '中中卦')}）→ "
        f"{'、'.join(hu_detail.get('core_meaning', ['暂缺'])[:3])}"
    )
    hu_cuo_zong_tip = _build_hu_cuo_zong_text(hu_upper, hu_lower)

    # --- 错卦 ---
    cuo_upper, cuo_lower = calculate_cuogua(upper_num, lower_num)
    cuo_detail = HEXAGRAM_DATA.get((cuo_upper, cuo_lower), {})
    cuo_name = cuo_detail.get("name", f"{BAGUA_DATA[cuo_upper]['name']}{BAGUA_DATA[cuo_lower]['name']}")
    cuo_tip = (
        f"错卦：{cuo_name}"
        f"（{cuo_detail.get('ji_xiong', '中中卦')}）→ "
        f"{'、'.join(cuo_detail.get('core_meaning', ['暂缺'])[:3])}"
    )

    # --- 综卦 ---
    zong_upper, zong_lower = calculate_zonggua(upper_num, lower_num)
    zong_detail = HEXAGRAM_DATA.get((zong_upper, zong_lower), {})
    zong_name = zong_detail.get("name", f"{BAGUA_DATA[zong_upper]['name']}{BAGUA_DATA[zong_lower]['name']}")
    zong_tip = (
        f"综卦：{zong_name}"
        f"（{zong_detail.get('ji_xiong', '中中卦')}）→ "
        f"{'、'.join(zong_detail.get('core_meaning', ['暂缺'])[:3])}"
    )

    # --- 体用分析 ---
    tiyong_info = identify_tiyong(upper_num, lower_num, dong_yao)
    tiyong_tip = _build_tiyong_text(tiyong_info)

    # --- 装卦 ---
    solar = lunar_info.get("solar")
    zhuanggua_result = zhuang_gua_complete(upper_num, lower_num, solar=solar, lunar_info=lunar_info)
    if dong_yao and 1 <= dong_yao <= 6:
        zhuanggua_result["lines"][dong_yao - 1]["is_dong"] = True
    refresh_line_strengths(zhuanggua_result)

    bian_zhuanggua_result = zhuang_gua_complete(bian_upper, bian_lower, solar=solar, lunar_info=lunar_info)
    bian_line_relation = analyze_bian_line_relation(zhuanggua_result, bian_zhuanggua_result, dong_yao)

    # --- 六亲格局 ---
    liuqin_summary = analyze_liuqin_summary(zhuanggua_result, dong_yao=dong_yao)
    yongshen_system = analyze_yongshen_system(zhuanggua_result, question_text=question_text, dong_yao=dong_yao)
    yongshen_name = yongshen_system["yongshen_name"]
    dizhi_relation_summary = analyze_dizhi_relation_summary(
        zhuanggua_result, dong_yao=dong_yao, yongshen_name=yongshen_name)
    nayin_summary = analyze_nayin_summary(zhuanggua_result)
    liushen_zhihua_summary = analyze_liushen_zhihua_summary(zhuanggua_result)
    line_strength_summary = analyze_line_strength_summary(zhuanggua_result)
    zhuanggua_table = format_zhuanggua_table(zhuanggua_result, dong_yao=dong_yao)
    external_omen_result = analyze_external_omen(external_omen)
    traditional_evidence_chain = build_traditional_evidence_chain(
        zhuanggua_result, yongshen_system, bian_line_relation)
    source_trace = build_source_trace(zhuanggua_result, yongshen_system, bian_line_relation)
    reality_check = build_reality_check(
        yongshen_system.get("inference", {}).get("category", ""),
        yongshen_name,
    )

    # --- 生成具体断语 ---
    specific_judgment = _build_specific_judgment(
        zhuanggua_result, yongshen_system, bian_line_relation,
        tiyong_info, dong_yao, question_text, hexagram_detail,
    )

    # ── 人本哲学指引 ──
    human_guidance = build_human_guidance(
        hexagram_name=hexagram_detail["name"],
        ji_xiong=ji_xiong,
        shang_gua_name=upper_gua["name"],
        xia_gua_name=lower_gua["name"],
    )

    # ── 大象传 ──
    daxiang_data = get_daxiang(hexagram_detail["name"])

    # ── 彖传 ──
    tuanzhuan_data = get_tuanzhuan(hexagram_detail["name"])

    # ── 卦身 ──
    guashen_analysis = analyze_guashen(zhuanggua_result)

    # ── 神煞 ──
    shensha_analysis = analyze_shensha_summary(zhuanggua_result)

    # 世爻六亲
    shishen_liuqin = get_shishen_liuqin(zhuanggua_result)
    shishen_info = LIUQIN_XIANGYI.get(shishen_liuqin, {})

    # 动爻六亲解读
    dong_yao_liuqin_tip = ""
    if dong_yao and 1 <= dong_yao <= 6:
        dong_line = zhuanggua_result["lines"][dong_yao - 1]
        dong_lq = dong_line["liuqin"]
        dong_ls = dong_line["liushen"]
        dong_lq_info = LIUQIN_XIANGYI.get(dong_lq, {})
        dong_ls_info = LIUSHEN_XIANGYI.get(dong_ls, {})
        dong_yao_liuqin_tip = (
            f"动爻{dong_lq}发动（临{dong_ls}），"
            f"{dong_lq_info.get('description', '')}。"
            f"{dong_ls}：{dong_ls_info.get('description', '')}"
        )

    liuqin_interpretation = _interpret_liuqin_pattern(zhuanggua_result, dong_yao)

    return {
        "gua_name": hexagram_detail["name"],
        "gua_ci": hexagram_detail["gua_ci"],
        "core_meaning": hexagram_detail["core_meaning"],
        "hexagram_calibration": hexagram_calibration,
        "calibration_tip": calibration_tip,
        "ji_xiong": ji_xiong,
        "ji_xiong_score": ji_xiong_score,
        # 五行
        "qian_yin_hou_guo": f"上卦{upper_gua['full_name']}（前因/当下）→ 下卦{lower_gua['full_name']}（后果/未来）",
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
        # 纳甲
        "zhuanggua_table": zhuanggua_table,
        "zhuanggua_result": zhuanggua_result,
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
        "source_trace": source_trace,
        "reality_check": reality_check,
        "nayin_summary": nayin_summary,
        "liushen_zhihua_summary": liushen_zhihua_summary,
        "external_omen_tip": external_omen_result["tip"],
        "external_omen_level": external_omen_result["level"],
        # 断语
        "specific_judgment": specific_judgment,
        "judgment_detail": specific_judgment["detail"],
        "judgment_conclusion": specific_judgment["conclusion"],
        # 人本哲学
        "human_guidance": human_guidance,
        "human_agency_reminder": HUMAN_AGENCY_REMINDER,
        # 大象传
        "daxiang": daxiang_data["daxiang"],
        "daxiang_shangxia": daxiang_data["shangxia_xiang"],
        "daxiang_junzi": daxiang_data["junzi_jiao"],
        # 彖传
        "tuanzhuan": tuanzhuan_data["tuanzhuan"],
        "tuanzhuan_core": tuanzhuan_data["core_idea"],
        # 卦身
        "guashen_analysis": guashen_analysis,
        "guashen_summary": guashen_analysis["summary"],
        # 神煞
        "shensha_analysis": shensha_analysis,
        "shensha_summary": shensha_analysis["summary"],
        "shensha_key_hints": shensha_analysis["key_hints"],
        "naja_analysis": zhuanggua_table,
        "naja_info": zhuanggua_result,
        "decision_suggest": specific_judgment["conclusion"],
    }


def _build_tiyong_text(tiyong_info):
    """构建体用分析文本（精简版）。"""
    ti = tiyong_info
    text = (
        f"体卦：{ti['ti_gua_full']}（{ti['ti_element']}）— 代表求测者\n"
        f"用卦：{ti['yong_gua_full']}（{ti['yong_element']}）— 代表所问之事\n"
        f"体用关系：{ti['relation']} — {ti['relation_desc']}"
    )
    yong_name = ti["yong_gua_name"]
    if yong_name in TIYONG_SHENG_KE_XIANG:
        xiang = TIYONG_SHENG_KE_XIANG[yong_name]
        if "用生体" in ti["relation"]:
            text += f"\n所主吉事：{xiang.get('sheng_ti', '')}"
        elif "用克体" in ti["relation"]:
            text += f"\n所主凶事：{xiang.get('ke_ti', '')}"
        elif "体生用" in ti["relation"]:
            text += f"\n泄气事项：{xiang.get('ke_ti', '')}"
    return text


def _interpret_liuqin_pattern(zhuanggua_result, dong_yao=None):
    """分析六亲格局（精简版）。"""
    lines = zhuanggua_result["lines"]
    tips = []

    shi_line = next((l for l in lines if l["is_shi"]), None)
    if shi_line:
        cs = shi_line["changsheng"]
        lq = shi_line["liuqin"]
        if cs in ("长生", "临官", "帝旺"):
            tips.append(f"世爻{lq}得{cs}，自身根基扎实")
        elif cs in ("死", "墓", "绝"):
            tips.append(f"世爻{lq}处{cs}，自身力量不足")
        if shi_line.get("line_status"):
            tips.append(f"世爻见{'、'.join(shi_line['line_status'])}")

    if dong_yao and 1 <= dong_yao <= 6:
        dong_line = lines[dong_yao - 1]
        dong_lq = dong_line["liuqin"]
        dong_ls = dong_line["liushen"]
        if dong_lq == "子孙" and dong_line["changsheng"] in ("长生", "帝旺"):
            tips.append("子孙旺动，福神有力可解灾厄")
        if dong_lq == "妻财" and dong_line["changsheng"] in ("长生", "帝旺"):
            tips.append("妻财旺动，求财有利")
        if dong_lq == "官鬼" and dong_line["changsheng"] in ("长生", "帝旺"):
            tips.append("官鬼旺动，注意事业压力或健康")
        if dong_lq == "兄弟" and dong_line["changsheng"] in ("帝旺",):
            tips.append("兄弟旺动，竞争加剧，注意口舌破财")
        if dong_ls == "白虎":
            tips.append("动临白虎，事态急迫宜果断")
        elif dong_ls == "青龙":
            tips.append("动临青龙，有喜庆贵人相助")
        if dong_line.get("line_status"):
            tips.append(f"动爻见{'、'.join(dong_line['line_status'])}")
        if dong_line.get("liushen_effect"):
            tips.append(dong_line["liushen_effect"])

    return "；".join(tips) if tips else "六亲格局平稳"


def _build_single_gua_tiyong_text(gua_info, yao_list, wang_shuai):
    """三爻快占的单卦分析。"""
    if not yao_list:
        return ""
    yang_count = sum(1 for y in yao_list if y == 1)
    yin_count = len(yao_list) - yang_count
    position_names = ["初爻", "二爻", "三爻"]
    active_positions = [position_names[i] for i, y in enumerate(yao_list) if y == 1]
    quiet_positions = [position_names[i] for i, y in enumerate(yao_list) if y == 0]

    if wang_shuai in ("旺", "相"):
        season_tip = "卦体得令有力"
    elif wang_shuai in ("休",):
        season_tip = "卦体休气，宜守中待势"
    else:
        season_tip = "卦体失令，行动力量不足"

    if yang_count > yin_count:
        yao_tip = "阳多阴少，用在主动推进"
    elif yin_count > yang_count:
        yao_tip = "阴多阳少，用在收敛等待"
    else:
        yao_tip = "阴阳相停，宜先分清主次"

    active_text = "、".join(active_positions) if active_positions else "无"
    quiet_text = "、".join(quiet_positions) if quiet_positions else "无"
    return f"单卦{gua_info['full_name']}（{gua_info['element']}），{season_tip}；{yao_tip}；阳爻：{active_text}，阴爻：{quiet_text}"


def interpret_three_yao(three_yao_info):
    """三爻快占解卦逻辑。"""
    gua_info = three_yao_info["gua_info"]
    lunar_info = three_yao_info["lunar_info"]
    season = lunar_info.get("season", "春")
    element = gua_info["element"]
    wang_shuai = WUXING_WANG_SHUAI.get(season, {}).get(element, "平")

    core_tip = f"得{gua_info['full_name']}卦（{gua_info['gua_hua']}），五行属{element}，当季{wang_shuai}"
    meaning_tip = f"意象：{'、'.join(gua_info['core_meaning'])}"
    direction_tip = f"方位：{gua_info['position']}方  颜色：{gua_info['color']}"
    weather_tip = f"天时：{gua_info['weather']}"
    wu_xiang_tip = f"物象：{'、'.join(gua_info['wu_xiang'])}"

    if wang_shuai in ("旺", "相"):
        suggest = "卦体得令，宜积极推进，利主动行事"
    elif wang_shuai in ("休", "囚"):
        suggest = "卦体气平，宜守成，不宜冒进"
    else:
        suggest = "卦体失令，宜隐忍待机，静待时机"

    tiyong_note = ""
    single_tiyong_tip = ""
    yao_list = three_yao_info.get("yao_list", [])
    if yao_list:
        yao_desc = "".join(["——" if y == 1 else "— —" for y in yao_list])
        yao_text = "".join(["阳" if y == 1 else "阴" for y in yao_list])
        tiyong_note = f"爻象：{yao_desc}（{yao_text}）"
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
