# -*- coding: utf-8 -*-
"""
六爻神煞子系统

神煞是六爻预测中的重要辅助信息，用于取象和辅助判断吉凶。
神煞不决定吉凶，只作辅助参考。神煞临用神且旺相才有实质作用。

包含：
1. 天乙贵人
2. 文昌贵人
3. 驿马
4. 桃花（咸池）
5. 禄神
6. 华盖
7. 劫煞
8. 灾煞
"""

# ═══════════════════════════════════════════════════════════
# 1. 天乙贵人（以日干/年干查）
# ═══════════════════════════════════════════════════════════

TIANYI_GUIREN = {
    "甲": {"贵人": ["丑", "未"], "口诀": "甲戊庚牛羊"},
    "戊": {"贵人": ["丑", "未"], "口诀": "甲戊庚牛羊"},
    "庚": {"贵人": ["丑", "未"], "口诀": "甲戊庚牛羊"},
    "乙": {"贵人": ["子", "申"], "口诀": "乙己鼠猴乡"},
    "己": {"贵人": ["子", "申"], "口诀": "乙己鼠猴乡"},
    "丙": {"贵人": ["亥", "酉"], "口诀": "丙丁猪鸡位"},
    "丁": {"贵人": ["亥", "酉"], "口诀": "丙丁猪鸡位"},
    "壬": {"贵人": ["卯", "巳"], "口诀": "壬癸兔蛇藏"},
    "癸": {"贵人": ["卯", "巳"], "口诀": "壬癸兔蛇藏"},
    "辛": {"贵人": ["午", "寅"], "口诀": "六辛逢马虎"},
}


def get_tianyi_guiren(day_tiangan):
    """获取天乙贵人地支列表。"""
    info = TIANYI_GUIREN.get(day_tiangan, {})
    return info.get("贵人", [])


def check_line_has_tianyi(line_dizhi, day_tiangan):
    """检查某爻是否临天乙贵人。"""
    guiren_dizhis = get_tianyi_guiren(day_tiangan)
    return line_dizhi in guiren_dizhis


# ═══════════════════════════════════════════════════════════
# 2. 文昌贵人（以日干查）
# ═══════════════════════════════════════════════════════════

WENCHANG_GUIREN = {
    "甲": "巳", "乙": "午",
    "丙": "申", "丁": "酉",
    "戊": "申", "己": "酉",
    "庚": "亥", "辛": "子",
    "壬": "寅", "癸": "卯",
}


def get_wenchang(day_tiangan):
    """获取文昌贵人地支。"""
    return WENCHANG_GUIREN.get(day_tiangan, "")


# ═══════════════════════════════════════════════════════════
# 3. 驿马（以日支/年支查，申子辰在寅，寅午戌在申，巳酉丑在亥，亥卯未在巳）
# ═══════════════════════════════════════════════════════════

YIMA_MAP = {
    "申": "寅", "子": "寅", "辰": "寅",
    "寅": "申", "午": "申", "戌": "申",
    "巳": "亥", "酉": "亥", "丑": "亥",
    "亥": "卯", "卯": "巳", "未": "巳",
}


def get_yima(day_dizhi):
    """获取驿马地支。"""
    return YIMA_MAP.get(day_dizhi, "")


# ═══════════════════════════════════════════════════════════
# 4. 桃花/咸池（以日支查：申子辰在酉，寅午戌在卯，巳酉丑在午，亥卯未在子）
# ═══════════════════════════════════════════════════════════

TAOHUA_MAP = {
    "申": "酉", "子": "酉", "辰": "酉",
    "寅": "卯", "午": "卯", "戌": "卯",
    "巳": "午", "酉": "午", "丑": "午",
    "亥": "子", "卯": "子", "未": "子",
}


def get_taohua(day_dizhi):
    """获取桃花地支。"""
    return TAOHUA_MAP.get(day_dizhi, "")


# ═══════════════════════════════════════════════════════════
# 5. 禄神（以日干查：甲禄寅、乙禄卯、丙戊禄巳、丁己禄午、庚禄申、辛禄酉、壬禄亥、癸禄子）
# ═══════════════════════════════════════════════════════════

LUSHEN_MAP = {
    "甲": "寅", "乙": "卯",
    "丙": "巳", "戊": "巳",
    "丁": "午", "己": "午",
    "庚": "申", "辛": "酉",
    "壬": "亥", "癸": "子",
}


def get_lushen(day_tiangan):
    """获取禄神地支。"""
    return LUSHEN_MAP.get(day_tiangan, "")


# ═══════════════════════════════════════════════════════════
# 6. 华盖（以日支查：寅午戌见戌，巳酉丑见丑，申子辰见辰，亥卯未见未）
# ═══════════════════════════════════════════════════════════

HUAGAI_MAP = {
    "寅": "戌", "午": "戌", "戌": "戌",
    "巳": "丑", "酉": "丑", "丑": "丑",
    "申": "辰", "子": "辰", "辰": "辰",
    "亥": "未", "卯": "未", "未": "未",
}


def get_huagai(day_dizhi):
    """获取华盖地支。"""
    return HUAGAI_MAP.get(day_dizhi, "")


# ═══════════════════════════════════════════════════════════
# 7. 劫煞（以日支查：寅午戌在亥，巳酉丑在寅，申子辰在巳，亥卯未在申）
# ═══════════════════════════════════════════════════════════

JIESHA_MAP = {
    "寅": "亥", "午": "亥", "戌": "亥",
    "巳": "寅", "酉": "寅", "丑": "寅",
    "申": "巳", "子": "巳", "辰": "巳",
    "亥": "申", "卯": "申", "未": "申",
}


def get_jiesha(day_dizhi):
    """获取劫煞地支。"""
    return JIESHA_MAP.get(day_dizhi, "")


# ═══════════════════════════════════════════════════════════
# 8. 灾煞（驿马前三辰：申子辰在午，寅午戌在子，巳酉丑在卯，亥卯未在酉）
# ═══════════════════════════════════════════════════════════

ZAISHA_MAP = {
    "申": "午", "子": "午", "辰": "午",
    "寅": "子", "午": "子", "戌": "子",
    "巳": "卯", "酉": "卯", "丑": "卯",
    "亥": "酉", "卯": "酉", "未": "酉",
}


def get_zaisha(day_dizhi):
    """获取灾煞地支。"""
    return ZAISHA_MAP.get(day_dizhi, "")


# ═══════════════════════════════════════════════════════════
# 综合神煞查询
# ═══════════════════════════════════════════════════════════

SHENSHA_DEFINITIONS = {
    "天乙贵人": {"type": "吉", "meaning": "贵人相助，逢凶化吉，遇事有人帮"},
    "文昌贵人": {"type": "吉", "meaning": "文星照命，利学业考试、文书契约"},
    "驿马": {"type": "中性", "meaning": "走动奔波、出行变动，临吉神主有利出行，临凶神主奔波劳碌"},
    "桃花": {"type": "中性", "meaning": "异性缘、人缘、交际。临吉神主良缘，临凶神主酒色是非"},
    "禄神": {"type": "吉", "meaning": "食禄俸禄，利财运事业，得食禄之养"},
    "华盖": {"type": "中性", "meaning": "孤独、清高、才艺。利学术研究，不利社交应酬"},
    "劫煞": {"type": "凶", "meaning": "破财损耗、意外失脱，宜多加防范"},
    "灾煞": {"type": "凶", "meaning": "灾祸横生、突发变故，病讼血光之象"},
}


def check_all_shensha(line_dizhi, day_tiangan, day_dizhi):
    """
    检查某爻是否命中各种神煞。

    参数：
        line_dizhi: 爻的地支
        day_tiangan: 日天干
        day_dizhi: 日地支

    返回：
        list[dict]: 命中的神煞列表，每项包含名称、类型、含义
    """
    hits = []

    # 天乙贵人（按日干）
    if line_dizhi in get_tianyi_guiren(day_tiangan):
        hits.append({"name": "天乙贵人", "type": "吉", "meaning": SHENSHA_DEFINITIONS["天乙贵人"]["meaning"]})

    # 文昌贵人（按日干）
    if line_dizhi == get_wenchang(day_tiangan):
        hits.append({"name": "文昌贵人", "type": "吉", "meaning": SHENSHA_DEFINITIONS["文昌贵人"]["meaning"]})

    # 禄神（按日干）
    if line_dizhi == get_lushen(day_tiangan):
        hits.append({"name": "禄神", "type": "吉", "meaning": SHENSHA_DEFINITIONS["禄神"]["meaning"]})

    # 驿马（按日支）
    if line_dizhi == get_yima(day_dizhi):
        hits.append({"name": "驿马", "type": "中性", "meaning": SHENSHA_DEFINITIONS["驿马"]["meaning"]})

    # 桃花（按日支）
    if line_dizhi == get_taohua(day_dizhi):
        hits.append({"name": "桃花", "type": "中性", "meaning": SHENSHA_DEFINITIONS["桃花"]["meaning"]})

    # 华盖（按日支）
    if line_dizhi == get_huagai(day_dizhi):
        hits.append({"name": "华盖", "type": "中性", "meaning": SHENSHA_DEFINITIONS["华盖"]["meaning"]})

    # 劫煞（按日支）
    if line_dizhi == get_jiesha(day_dizhi):
        hits.append({"name": "劫煞", "type": "凶", "meaning": SHENSHA_DEFINITIONS["劫煞"]["meaning"]})

    # 灾煞（按日支）
    if line_dizhi == get_zaisha(day_dizhi):
        hits.append({"name": "灾煞", "type": "凶", "meaning": SHENSHA_DEFINITIONS["灾煞"]["meaning"]})

    return hits


def analyze_shensha_summary(zhuanggua_result):
    """
    对整个装卦结果进行神煞分析。

    返回：
        dict: {
            "summary": 摘要文本,
            "details": 每爻神煞详情列表,
            "key_hints": 关键提示,
        }
    """
    lines = zhuanggua_result.get("lines", [])
    day_ganzhi = zhuanggua_result.get("day_ganzhi", "甲子")
    day_tiangan = day_ganzhi[0] if len(day_ganzhi) >= 2 else "甲"
    day_dizhi = zhuanggua_result.get("day_dizhi", "子")

    details = []
    key_hints = []

    important_positions = set()
    for line in lines:
        if line.get("is_shi") or line.get("is_ying") or line.get("is_dong"):
            important_positions.add(line["position"])

    for line in lines:
        hits = check_all_shensha(line.get("dizhi", ""), day_tiangan, day_dizhi)
        if hits:
            detail = {
                "position": line["position"],
                "position_name": line["position_name"],
                "liuqin": line.get("liuqin", ""),
                "dizhi": line.get("dizhi", ""),
                "is_important": line["position"] in important_positions,
                "shensha_hits": hits,
            }
            details.append(detail)

            if line["position"] in important_positions:
                for hit in hits:
                    prefix = "吉" if hit["type"] == "吉" else ("凶" if hit["type"] == "凶" else "中")
                    key_hints.append(
                        f"{line['position_name']}{line.get('liuqin', '')}"
                        f"临{hit['name']}（{prefix}）：{hit['meaning']}"
                    )

    if not details:
        return {
            "summary": "本卦诸爻未中主要神煞，以五行生克与用神分析为主。",
            "details": [],
            "key_hints": [],
        }

    summary_parts = []
    for detail in details[:5]:
        shensha_names = "、".join(h["name"] for h in detail["shensha_hits"])
        marker = "★" if detail["is_important"] else ""
        summary_parts.append(
            f"{marker}{detail['position_name']}{detail['liuqin']}"
            f"{detail['dizhi']}：临{shensha_names}"
        )

    return {
        "summary": "；".join(summary_parts),
        "details": details,
        "key_hints": key_hints,
    }
