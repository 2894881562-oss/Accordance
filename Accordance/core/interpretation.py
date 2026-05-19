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

    # --- 应期分析 ---
    timing = _analyze_timing(zhuanggua_result, yongshen_system, dong_line)
    if timing:
        parts.append(timing)

    # --- 综合结论 ---
    combined_score = yong_score + bian_score * 0.6
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

    # 用神安静应期（没有旬空/月破时才提示）
    if not has_xk_or_yp and yong_lines and not any(l.get("is_dong") for l in yong_lines):
        for line in yong_lines[:1]:
            dizhi = line.get("dizhi", "")
            tips.append(f"用神安静，待逢值（{dizhi}）或逢冲之日/月为应期")

    return "；".join(tips) if tips else ""


def _build_category_conclusion(category, yongshen_name, score, yong_lines,
                                yuan_lines, ji_lines, bian_relation,
                                shi_line, dong_line, timing=""):
    """根据问事类别生成具体结论断语。"""
    has_yong = bool(yong_lines)
    yong_strong = any(l.get("strength_score", 0) >= 2 for l in yong_lines) if yong_lines else False
    yong_weak = all(l.get("strength_score", 0) < 0 for l in yong_lines) if yong_lines else True
    yuan_strong = any(l.get("strength_score", 0) >= 2 for l in yuan_lines) if yuan_lines else False
    ji_strong = any(l.get("strength_score", 0) >= 2 for l in ji_lines) if ji_lines else False
    has_huike = bian_relation == "回头克"
    has_huisheng = bian_relation == "回头生"

    # 婚恋需要优先判断（女占婚恋用官鬼，但不能走官职逻辑）
    if "婚恋" in category:
        base = ""
        if yong_strong and score >= 2:
            base = "用神旺相，感情有利，可主动推进关系发展"
        elif yong_weak:
            base = "用神衰弱，感情近期难有突破，宜顺其自然"
        elif has_huike:
            base = "动变回头克，感情须防反复与矛盾激化，宜多沟通少争执"
        elif has_huisheng:
            base = "动变回头生，感情后势有回暖迹象，可耐心经营"
        elif score >= 0:
            base = "用神力量中平，感情宜稳中求进，不宜操之过急"
        else:
            base = "用神受制偏弱，感情宜保持距离观察，不宜贸然表白或决定"
        if timing:
            base += f"。{timing}"
        return base

    if "财货" in category or "妻财" == yongshen_name:
        base = ""
        if yong_strong and yuan_strong and not ji_strong:
            base = "财爻旺相得生，求财有利，宜把握时机主动出击"
        elif yong_strong and ji_strong:
            base = "财爻虽旺但忌神亦强，求财有竞争消耗，宜快进快出不宜久持"
        elif yong_weak and ji_strong:
            base = "财爻衰弱忌神猖獗，破耗之象明显，求财不利，守成为上，暂勿投资"
        elif not has_yong:
            base = "财爻不现，求财需待时机。若伏神得生则待出现之月可图，若伏神受克则难成"
        elif has_huisheng:
            base = "动变回头生扶，求财后势有补益，可小步试探，待势头明朗再加码"
        elif has_huike:
            base = "动变回头克，求财须防后续反噬，不可贪多冒进，见好即收"
        elif score >= 3:
            base = "用神证据偏强，求财有利，可按计划推进"
        elif score >= 0:
            base = "用神力量中平，求财宜稳中求进，不宜大举投入"
        else:
            base = "用神受制偏弱，求财不利，宜守不宜攻，静待时机"
        if timing:
            base += f"。{timing}"
        return base

    if "官职" in category or "官鬼" == yongshen_name:
        base = ""
        if yong_strong and not ji_strong:
            base = "官爻旺相，事业有利，升迁有望，宜积极争取"
        elif yong_strong and ji_strong:
            base = "官爻旺但忌神来克，事业有竞争压力，需防小人暗算"
        elif yong_weak:
            base = "官爻衰弱，事业近期难有起色，宜韬光养晦，待机而发"
        elif has_huike:
            base = "动变回头克，事业须防后续变故，不可轻易跳槽或扩张"
        elif has_huisheng:
            base = "动变回头生，事业后势有贵人扶持，坚持可成"
        elif score >= 2:
            base = "用神证据偏有利，事业可按计划推进"
        elif score >= -1:
            base = "用神力量中平，事业宜稳守，不宜冒险"
        else:
            base = "用神受制较重，事业宜守不宜攻，待时运好转再图"
        if timing:
            base += f"。{timing}"
        return base

    if "文书" in category or "父母" == yongshen_name:
        base = ""
        if yong_strong:
            base = "父母爻旺相，文书考试之事有利，宜认真准备积极应试"
        elif yong_weak:
            base = "父母爻衰弱，文书考试之事需加倍努力，不可掉以轻心"
        elif score >= 1:
            base = "用神证据偏有利，文书契约之事可按程序推进"
        else:
            base = "用神受制偏弱，文书之事恐有波折，宜仔细核对避免疏漏"
        if timing:
            base += f"。{timing}"
        return base

    if "子女" in category or "子孙" == yongshen_name:
        base = ""
        if yong_strong:
            base = "子孙爻旺相，子女/娱乐/医疗之事有利，福神得力可解忧"
        elif yong_weak:
            base = "子孙爻衰弱，子女之事或有隐忧，需多加关注"
        elif score >= 1:
            base = "用神证据偏有利，所问之事可乐观以待"
        else:
            base = "用神受制偏弱，宜谨慎行事，多做准备"
        if timing:
            base += f"。{timing}"
        return base

    # 泛问 / 默认
    base = ""
    if score >= 4:
        base = "用神旺相有力，原神生扶到位，所问之事可积极推进，顺势而为"
    elif score >= 1.5:
        base = "用神有根，整体可推进，但需注意忌神干扰与动变风险，稳中求进"
    elif score >= -1:
        base = "用神力量中平，吉凶参半，宜结合现实条件审慎决策，不宜冒进"
    elif score >= -3:
        base = "用神偏弱受制，阻力较大，宜先收敛观察、补足短板，不宜强推"
    else:
        base = "用神受制严重，所问之事不宜妄动，以静制动、隐忍待机为上"
    if timing:
        base += f"。{timing}"
    return base


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

    # --- 生成具体断语 ---
    specific_judgment = _build_specific_judgment(
        zhuanggua_result, yongshen_system, bian_line_relation,
        tiyong_info, dong_yao, question_text, hexagram_detail,
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
        "nayin_summary": nayin_summary,
        "liushen_zhihua_summary": liushen_zhihua_summary,
        "external_omen_tip": external_omen_result["tip"],
        "external_omen_level": external_omen_result["level"],
        # 断语
        "specific_judgment": specific_judgment,
        "judgment_detail": specific_judgment["detail"],
        "judgment_conclusion": specific_judgment["conclusion"],
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
        yao_desc = "".join(["⚊" if y == 1 else "⚋" for y in yao_list])
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
