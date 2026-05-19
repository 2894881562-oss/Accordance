# -*- coding: utf-8 -*-
"""
六爻完整装卦引擎

按照京房纳甲筮法规则，对六爻卦进行完整装卦：
1. 定卦宫、五行
2. 安世应
3. 纳甲（配天干地支）
4. 排六亲
5. 布六神
6. 算十二长生

参考经典：《火珠林》《卜筮正宗》《增删卜易》
"""

from config.bagua_data import (
    BAGUA_NAME_TO_NUM, NUM_TO_GUA_NAME, PALACE_WUXING, PALACE_HEXAGRAMS,
)
from config.naja_data import (
    BAGUA_NAJIA, BAGUA_SHI_YING, LIUQIN_RULE,
    LIUSHEN_ORDER, LIUSHEN_START, LIUSHEN_XIANGYI,
    LIUQIN_XIANGYI, YONGSHEN_QUERY,
    NAYIN_TABLE, NAYIN_WUXING as NAYIN_NAME_TO_WUXING,
    CHANGSHENG_POWER,
)
from config.wuxing_rules import (
    WUXING_SHENG, WUXING_KE, DIZHI_WUXING,
    TIANGAN_WUXING, SHIER_CHANGSHENG_ORDER,
    WUXING_SHIER_CHANGSHENG, DIZHI_ORDER,
    DIZHI_CHONG, DIZHI_HE, DIZHI_HAI, DIZHI_XING,
)
from config.hexagram_data import HEXAGRAM_DATA
from core.qi_context import (
    get_accurate_day_ganzhi, get_day_tiangan, get_day_dizhi, get_xunkong,
)


PALACE_ROLE_NAMES = ["本宫六世", "一世", "二世", "三世", "四世", "五世", "游魂", "归魂"]

LIUQIN_KEYWORD_RULES = [
    {
        "category": "财货经营",
        "yongshen": "妻财",
        "keywords": [
            "求财", "钱", "财", "收入", "工资", "奖金", "投资", "股票", "基金",
            "订单", "客户", "买卖", "交易", "货物", "资产", "利润", "价格",
            "寻物", "丢", "失物", "钱包", "手机", "物品",
        ],
        "reason": "财货、交易、失物多以妻财为用神。",
    },
    {
        "category": "官职压力",
        "yongshen": "官鬼",
        "keywords": [
            "求官", "官运", "升职", "晋升", "职位", "求职", "面试", "工作",
            "事业", "领导", "上级", "官司", "诉讼", "法律", "考试录用",
            "疾病", "病", "灾", "风险", "压力", "丈夫", "男友", "男朋友",
        ],
        "reason": "官职、约束、病灾、诉讼与女占配偶多以官鬼为用神。",
    },
    {
        "category": "文书长辈",
        "yongshen": "父母",
        "keywords": [
            "考试", "学业", "论文", "证书", "合同", "文书", "签证", "申请",
            "资料", "简历", "房屋", "车", "车船", "长辈", "父亲", "母亲",
            "老师", "录取", "手续",
        ],
        "reason": "文书、考试、房车、长辈庇护多以父母为用神。",
    },
    {
        "category": "子女解忧",
        "yongshen": "子孙",
        "keywords": [
            "子女", "孩子", "儿子", "女儿", "晚辈", "学生", "宠物", "娱乐",
            "旅游", "休闲", "开心", "医药", "医生", "治疗", "平安", "解忧",
            "生产", "怀孕",
        ],
        "reason": "子女、医药、娱乐、福神解忧多以子孙为用神。",
    },
    {
        "category": "同辈竞争",
        "yongshen": "兄弟",
        "keywords": [
            "兄弟", "姐妹", "朋友", "同事", "同学", "同辈", "伙伴", "合伙",
            "团队", "股东", "竞争", "对手", "分担", "借钱",
        ],
        "reason": "同辈、朋友、合伙、竞争多以兄弟为用神。",
    },
]


# ------------------------------------------------------------
# 1. 卦宫查询
# ------------------------------------------------------------

def get_hexagram_palace(upper_num, lower_num):
    """
    查找六爻卦所属八宫和五行。

    返回：
        dict: {
            "palace_name": 宫名（如"乾"、"坎"等）,
            "palace_wuxing": 宫五行（金/木/水/火/土）,
            "hexagram_key": 卦的上下卦编号,
        }
    """
    for palace_name, hex_list in PALACE_HEXAGRAMS.items():
        if (upper_num, lower_num) in hex_list:
            palace_index = hex_list.index((upper_num, lower_num))
            return {
                "palace_name": palace_name,
                "palace_wuxing": PALACE_WUXING[palace_name],
                "hexagram_key": (upper_num, lower_num),
                "palace_index": palace_index,
                "palace_role": PALACE_ROLE_NAMES[palace_index],
            }
    return {
        "palace_name": "未知",
        "palace_wuxing": "土",
        "hexagram_key": (upper_num, lower_num),
        "palace_index": -1,
        "palace_role": "未知",
    }


def get_pure_palace_hexagram(palace_name):
    """返回某宫八纯卦的上下卦编号。"""
    palace_list = PALACE_HEXAGRAMS.get(palace_name, [])
    if palace_list:
        return palace_list[0]
    gua_num = BAGUA_NAME_TO_NUM.get(palace_name, 8)
    return gua_num, gua_num


# ------------------------------------------------------------
# 2. 世应查询
# ------------------------------------------------------------

def get_shi_ying(hexagram_name):
    """
    查询卦的世应爻位。

    参数：
        hexagram_name: 卦名（如"乾为天"、"天山遁"等）

    返回：
        dict: {"shi": 世爻位置, "ying": 应爻位置}
    """
    if hexagram_name in BAGUA_SHI_YING:
        return BAGUA_SHI_YING[hexagram_name]
    return {"shi": 0, "ying": 0}


# ------------------------------------------------------------
# 3. 纳甲（配干支）
# ------------------------------------------------------------

def _get_hexagram_palace_guaming(upper_num, lower_num):
    """
    获取卦所属八宫的八纯卦名（用于纳甲配支）。

    算法：
    1. 先从八宫卦表中查找卦所在宫
    2. 八纯卦即为该宫的第一卦
    """
    palace_info = get_hexagram_palace(upper_num, lower_num)
    palace_name = palace_info["palace_name"]

    # 八纯卦名映射
    pure_hexagram_names = {
        "乾": "乾为天", "兑": "兑为泽", "离": "离为火", "震": "震为雷",
        "巽": "巽为风", "坎": "坎为水", "艮": "艮为山", "坤": "坤为地",
    }
    return pure_hexagram_names.get(palace_name, "未知"), palace_name


def get_najia_for_line(upper_num, lower_num, line_position):
    """
    获取某一爻的纳甲干支。

    参数：
        upper_num, lower_num: 上下卦编号
        line_position: 爻位（1=初爻, 2=二爻, ..., 6=上爻）

    返回：
        str: 纳甲干支（如"甲子"、"壬午"等）
    """
    najia_list = get_najia_all_lines(upper_num, lower_num)
    if 1 <= line_position <= 6:
        return najia_list[line_position - 1]
    return "未知"


def get_najia_all_lines(upper_num, lower_num):
    """
    获取卦的全部6爻纳甲干支。

    返回：
        list[str]: [初爻纳甲, 二爻纳甲, ..., 上爻纳甲]
    """
    lower_gua_name = NUM_TO_GUA_NAME.get(lower_num, "")
    upper_gua_name = NUM_TO_GUA_NAME.get(upper_num, "")

    lower_najia = BAGUA_NAJIA.get(lower_gua_name, [])
    upper_najia = BAGUA_NAJIA.get(upper_gua_name, [])
    if len(lower_najia) < 6 or len(upper_najia) < 6:
        return ["未知"] * 6

    return lower_najia[:3] + upper_najia[3:]


# ------------------------------------------------------------
# 4. 六亲计算
# ------------------------------------------------------------

def get_liuqin_for_line(ganzhi, palace_wuxing):
    """
    根据纳甲干支和卦宫五行，计算该爻的六亲。

    规则：
    以卦宫五行为"我"：
    - 生我者 → 父母
    - 克我者 → 官鬼
    - 我生者 → 子孙
    - 我克者 → 妻财
    - 同我者 → 兄弟

    参数：
        ganzhi: 纳甲干支（如"甲子"）
        palace_wuxing: 卦宫五行（金/木/水/火/土）

    返回：
        str: 六亲名称
    """
    if not ganzhi or len(ganzhi) < 2:
        return "未知"

    dizhi = ganzhi[1]
    dizhi_element = DIZHI_WUXING.get(dizhi, "土")

    # 以宫五行（我）与爻地支五行的关系定六亲
    if WUXING_SHENG.get(dizhi_element) == palace_wuxing:
        return "父母"  # 爻地支生宫 → 生我者父母
    if WUXING_SHENG.get(palace_wuxing) == dizhi_element:
        return "子孙"  # 宫生爻地支 → 我生者子孙
    if WUXING_KE.get(dizhi_element) == palace_wuxing:
        return "官鬼"  # 爻地支克宫 → 克我者官鬼
    if WUXING_KE.get(palace_wuxing) == dizhi_element:
        return "妻财"  # 宫克爻地支 → 我克者妻财
    if palace_wuxing == dizhi_element:
        return "兄弟"  # 比和者兄弟

    return "未知"


def get_liuqin_all_lines(upper_num, lower_num, palace_wuxing):
    """
    获取卦的全部6爻六亲。

    返回：
        list[str]: [初爻六亲, 二爻六亲, ..., 上爻六亲]
    """
    najia_list = get_najia_all_lines(upper_num, lower_num)
    return [get_liuqin_for_line(nj, palace_wuxing) for nj in najia_list]


# ------------------------------------------------------------
# 5. 六神排布
# ------------------------------------------------------------

def arrange_liushen_for_hexagram(solar=None):
    """
    按日天干排布六神（从初爻到上爻）。

    参数：
        solar: datetime.datetime 对象，默认为当前时间

    返回：
        list[str]: [初爻六神, 二爻六神, ..., 上爻六神]
    """
    day_gan = get_day_tiangan(solar)
    start_index = LIUSHEN_START.get(day_gan, 0)

    result = []
    for i in range(6):
        shen_index = (start_index + i) % 6
        result.append(LIUSHEN_ORDER[shen_index])

    return result


# ------------------------------------------------------------
# 6. 十二长生计算
# ------------------------------------------------------------

def get_changsheng_for_line(ganzhi):
    """
    计算某爻纳甲干支的十二长生状态。

    参数：
        ganzhi: 纳甲干支（如"甲子"）

    返回：
        str: 十二长生状态名称
    """
    if not ganzhi or len(ganzhi) < 2:
        return "未知"

    tiangan = ganzhi[0]
    dizhi = ganzhi[1]

    # 按天干五行分类
    tiangan_wuxing_group = {
        "甲": "甲木", "乙": "乙木",
        "丙": "丙火", "丁": "丁火",
        "戊": "戊土", "己": "己土",
        "庚": "庚金", "辛": "辛金",
        "壬": "壬水", "癸": "癸水",
    }

    group = tiangan_wuxing_group.get(tiangan, "甲木")
    if group not in WUXING_SHIER_CHANGSHENG:
        return "未知"

    start_dizhi = WUXING_SHIER_CHANGSHENG[group]
    if start_dizhi not in DIZHI_ORDER:
        return "未知"

    start_index = DIZHI_ORDER.index(start_dizhi)
    if dizhi not in DIZHI_ORDER:
        return "未知"

    target_index = DIZHI_ORDER.index(dizhi)

    # 阳干顺行，阴干逆行
    if tiangan in ["甲", "丙", "戊", "庚", "壬"]:
        offset = (target_index - start_index) % 12
    else:
        offset = (start_index - target_index) % 12

    return SHIER_CHANGSHENG_ORDER[offset]


def get_changsheng_all_lines(upper_num, lower_num):
    """
    获取卦的全部6爻十二长生状态。

    返回：
        list[str]: [初爻十二长生, ..., 上爻十二长生]
    """
    najia_list = get_najia_all_lines(upper_num, lower_num)
    return [get_changsheng_for_line(nj) for nj in najia_list]


# ------------------------------------------------------------
# 7. 旬空、月破、日破、刑冲合害、纳音、六神制化
# ------------------------------------------------------------

def get_dizhi_relations(dizhi_a, dizhi_b):
    """返回两个地支之间的刑冲合害关系。"""
    if not dizhi_a or not dizhi_b or dizhi_a == "?" or dizhi_b == "?":
        return []

    relations = []
    if dizhi_a == dizhi_b:
        relations.append("同支")
        if dizhi_b in DIZHI_XING.get(dizhi_a, []):
            relations.append("自刑")

    if DIZHI_CHONG.get(dizhi_a) == dizhi_b:
        relations.append("冲")
    if DIZHI_HE.get(dizhi_a) == dizhi_b:
        relations.append("合")
    if DIZHI_HAI.get(dizhi_a) == dizhi_b:
        relations.append("害")
    if dizhi_b in DIZHI_XING.get(dizhi_a, []) or dizhi_a in DIZHI_XING.get(dizhi_b, []):
        if "自刑" not in relations:
            relations.append("刑")

    return relations


def _build_line_status(dizhi, xunkong_info, yueling, day_dizhi):
    status = []
    empty_branches = xunkong_info.get("empty_branches", [])
    if dizhi in empty_branches:
        status.append("旬空")
    if yueling and DIZHI_CHONG.get(yueling) == dizhi:
        status.append("月破")
    if day_dizhi and DIZHI_CHONG.get(day_dizhi) == dizhi:
        status.append("日破")
    return status


def _build_relation_text(relations):
    return "、".join(relations) if relations else "无"


def _analyze_liushen_zhihua(line_wuxing, liushen_name):
    liushen_info = LIUSHEN_XIANGYI.get(liushen_name, {})
    liushen_wuxing = liushen_info.get("wuxing", "")
    if not line_wuxing or not liushen_wuxing:
        return {
            "liushen_wuxing": liushen_wuxing,
            "effect": "六神五行不明，暂不作制化判断",
            "score": 0,
        }

    liushen_jixiong = liushen_info.get("ji_xiong", "")
    is_auspicious = liushen_jixiong in ("吉", "半吉")
    is_inauspicious = liushen_jixiong in ("凶", "半凶")

    if line_wuxing == liushen_wuxing:
        effect = f"{liushen_name}与爻支同属{line_wuxing}，神爻同气，象意较纯"
        score = 1
    elif WUXING_SHENG.get(line_wuxing) == liushen_wuxing:
        effect = f"爻支{line_wuxing}生{liushen_name}{liushen_wuxing}，六神得生，象意增强"
        score = 2 if is_auspicious else -2 if is_inauspicious else 1
    elif WUXING_SHENG.get(liushen_wuxing) == line_wuxing:
        effect = f"{liushen_name}{liushen_wuxing}生爻支{line_wuxing}，神意转为助爻"
        score = 1 if is_auspicious else -1 if is_inauspicious else 0
    elif WUXING_KE.get(line_wuxing) == liushen_wuxing:
        effect = f"爻支{line_wuxing}克{liushen_name}{liushen_wuxing}，六神受制"
        score = -2 if is_auspicious else 2 if is_inauspicious else 0
    elif WUXING_KE.get(liushen_wuxing) == line_wuxing:
        effect = f"{liushen_name}{liushen_wuxing}克爻支{line_wuxing}，六神压制爻事"
        score = -2 if is_inauspicious else -1
    else:
        effect = "六神与爻支五行关系平平"
        score = 0

    return {
        "liushen_wuxing": liushen_wuxing,
        "effect": effect,
        "score": score,
    }


def get_liuqin_element(liuqin_name, palace_wuxing):
    """根据卦宫五行反推出某六亲对应的五行。"""
    if liuqin_name == "兄弟":
        return palace_wuxing
    if liuqin_name == "子孙":
        return WUXING_SHENG.get(palace_wuxing, palace_wuxing)
    if liuqin_name == "妻财":
        return WUXING_KE.get(palace_wuxing, palace_wuxing)
    if liuqin_name == "父母":
        for source, target in WUXING_SHENG.items():
            if target == palace_wuxing:
                return source
    if liuqin_name == "官鬼":
        for source, target in WUXING_KE.items():
            if target == palace_wuxing:
                return source
    return palace_wuxing


def _sheng_source(target_wuxing):
    for source, target in WUXING_SHENG.items():
        if target == target_wuxing:
            return source
    return "土"


def _ke_source(target_wuxing):
    for source, target in WUXING_KE.items():
        if target == target_wuxing:
            return source
    return "土"


def _chou_god_element(yuan_element, ji_element):
    for element in WUXING_SHENG:
        if WUXING_SHENG.get(element) == ji_element and WUXING_KE.get(element) == yuan_element:
            return element
    return _sheng_source(ji_element)


def _format_line_brief(line, include_strength=True):
    status = "、".join(line.get("line_status", [])) or "无空破"
    text = (
        f"{line['position_name']}{line['liuqin']}{line['dizhi']}"
        f"({line['dizhi_wuxing']}，{line['changsheng']})"
    )
    if line.get("is_shi"):
        text += "世"
    if line.get("is_ying"):
        text += "应"
    if line.get("is_dong"):
        text += "动"
    if include_strength:
        text += f"，{line.get('strength_level', '未评')} {line.get('strength_score', 0):+.1f}"
    return f"{text}，{status}"


def _context_power(line, context_dizhi, context_name):
    if not context_dizhi:
        return 0.0, []

    line_element = line.get("dizhi_wuxing", "")
    context_element = DIZHI_WUXING.get(context_dizhi, "")
    line_dizhi = line.get("dizhi", "")
    score = 0.0
    reasons = []
    is_month = context_name == "月建"
    same_branch_score = 2.5 if is_month else 2.0
    sheng_score = 1.8 if is_month else 1.3
    same_element_score = 1.2 if is_month else 0.9
    ke_score = 1.8 if is_month else 1.3

    if line_dizhi == context_dizhi:
        score += same_branch_score
        reasons.append(f"临{context_name}+{same_branch_score:g}")
    elif context_element == line_element:
        score += same_element_score
        reasons.append(f"{context_name}同五行+{same_element_score:g}")
    elif WUXING_SHENG.get(context_element) == line_element:
        score += sheng_score
        reasons.append(f"{context_name}生爻+{sheng_score:g}")
    elif WUXING_SHENG.get(line_element) == context_element:
        score -= 0.6 if is_month else 0.4
        reasons.append(f"爻生{context_name}泄气")
    elif WUXING_KE.get(context_element) == line_element:
        score -= ke_score
        reasons.append(f"{context_name}克爻-{ke_score:g}")
    elif WUXING_KE.get(line_element) == context_element:
        score -= 0.3 if is_month else 0.2
        reasons.append(f"爻克{context_name}耗力")

    relations = get_dizhi_relations(line_dizhi, context_dizhi)
    if "合" in relations:
        score += 0.6 if is_month else 0.4
        reasons.append(f"与{context_name}合")
    if "冲" in relations:
        score -= 1.0 if is_month else 0.8
        reasons.append(f"与{context_name}冲")
    if "刑" in relations:
        score -= 0.7 if is_month else 0.5
        reasons.append(f"与{context_name}刑")
    if "害" in relations:
        score -= 0.6 if is_month else 0.4
        reasons.append(f"与{context_name}害")

    return score, reasons


def calculate_line_strength(line, yueling="", day_dizhi=""):
    """综合十二长生、月日、空破、动静与六神制化量化爻力。"""
    score = float(line.get("changsheng_power", 0))
    reasons = [f"十二长生{line.get('changsheng', '未知')}{score:+g}"]

    liushen_score = float(line.get("liushen_effect_score", 0)) * 0.6
    if liushen_score:
        score += liushen_score
        reasons.append(f"六神制化{liushen_score:+.1f}")

    month_score, month_reasons = _context_power(line, yueling, "月建")
    day_score, day_reasons = _context_power(line, day_dizhi, "日辰")
    score += month_score + day_score
    reasons.extend(month_reasons)
    reasons.extend(day_reasons)

    if line.get("is_xunkong"):
        empty_penalty = 1.2 if line.get("is_dong") else 2.0
        score -= empty_penalty
        reasons.append(f"旬空-{empty_penalty:g}")
    if line.get("is_yuepo"):
        score -= 3.0
        reasons.append("月破-3")
    if line.get("is_ripo"):
        score -= 2.4
        reasons.append("日破-2.4")
    if line.get("is_dong"):
        score += 0.8
        reasons.append("发动+0.8")

    if score >= 4:
        level = "旺相有力"
    elif score >= 2:
        level = "偏旺可用"
    elif score > -1:
        level = "平稳待用"
    elif score > -3:
        level = "偏弱受制"
    else:
        level = "衰弱难用"

    return {
        "score": round(score, 1),
        "level": level,
        "reasons": reasons,
    }


def refresh_line_strengths(zhuanggua_result):
    """刷新每爻综合力量，动爻标记后应重新调用一次。"""
    yueling = zhuanggua_result.get("yueling", "")
    day_dizhi = zhuanggua_result.get("day_dizhi", "")
    for line in zhuanggua_result.get("lines", []):
        strength = calculate_line_strength(line, yueling=yueling, day_dizhi=day_dizhi)
        line["strength_score"] = strength["score"]
        line["strength_level"] = strength["level"]
        line["strength_reasons"] = strength["reasons"]
    return zhuanggua_result


def infer_yongshen_from_question(question_text, fallback="世爻"):
    """按问题语义推断用神，保留命中依据供输出解释。"""
    text = (question_text or "").strip()
    if not text:
        return {
            "primary": fallback,
            "secondary": "",
            "category": "未说明",
            "reason": "问题未说明具体门类，先以世爻代表自身/当日主体，再结合应爻、动爻参断。",
            "keywords": [],
        }

    marriage_words = ["婚姻", "感情", "恋爱", "复合", "结婚", "对象", "伴侣"]
    if any(word in text for word in marriage_words):
        if any(word in text for word in ["女占", "女方", "女生", "女士", "丈夫", "男友", "男朋友"]):
            return {
                "primary": "官鬼",
                "secondary": "妻财",
                "category": "婚恋女占",
                "reason": "女占婚恋以官鬼为夫星，同时兼看世应关系。",
                "keywords": [word for word in marriage_words if word in text],
            }
        if any(word in text for word in ["男占", "男方", "男生", "男士", "妻子", "女友", "女朋友"]):
            return {
                "primary": "妻财",
                "secondary": "官鬼",
                "category": "婚恋男占",
                "reason": "男占婚恋以妻财为妻财星，同时兼看世应关系。",
                "keywords": [word for word in marriage_words if word in text],
            }
        return {
            "primary": "官鬼",
            "secondary": "妻财",
            "category": "婚恋未分性别",
            "reason": "婚恋未说明性别，传统上男看妻财、女看官鬼；本次先以官鬼为主，并提示兼看妻财与世应。",
            "keywords": [word for word in marriage_words if word in text],
        }

    best_rule = None
    best_hits = []
    best_score = 0
    for index, rule in enumerate(LIUQIN_KEYWORD_RULES):
        hits = [word for word in rule["keywords"] if word in text]
        exact_bonus = 0
        for category, yongshen in YONGSHEN_QUERY.items():
            if category in text and yongshen == rule["yongshen"]:
                exact_bonus += 3
        score = len(hits) + exact_bonus - index * 0.01
        if score > best_score:
            best_score = score
            best_rule = rule
            best_hits = hits

    if best_rule:
        return {
            "primary": best_rule["yongshen"],
            "secondary": "",
            "category": best_rule["category"],
            "reason": best_rule["reason"],
            "keywords": best_hits,
        }

    return {
        "primary": fallback,
        "secondary": "",
        "category": "泛问",
        "reason": "未命中特定门类，先以世爻代表自身/主体，并以应爻、动爻为主。",
        "keywords": [],
    }


# ------------------------------------------------------------
# 8. 完整装卦主函数
# ------------------------------------------------------------

def zhuang_gua_complete(upper_num, lower_num, solar=None, lunar_info=None):
    """
    六爻完整装卦。

    对给定的六爻卦执行完整的京房纳甲装卦，
    返回每爻的完整信息。

    参数：
        upper_num: 上卦编号 (1-8)
        lower_num: 下卦编号 (1-8)
        solar: datetime.datetime，用于日干支和六神
        lunar_info: get_lunar_time() 返回值，用于月建、月破

    返回：
        dict: {
            "hexagram_name": 卦名,
            "palace_name": 宫名,
            "palace_wuxing": 宫五行,
            "shi_ying": {"shi": int, "ying": int},
            "lines": [
                {
                    "position": 1-6,
                    "position_name": "初爻"等,
                    "najia": "甲子",
                    "dizhi": "子",
                    "dizhi_wuxing": "水",
                    "tiangan": "甲",
                    "tiangan_wuxing": "木",
                    "liuqin": "父母",
                    "liushen": "青龙",
                    "changsheng": "长生",
                    "is_shi": bool,
                    "is_ying": bool,
                    "is_dong": bool,  # 需要外部设置
                },
                ...
            ],
            "liushen_by_day": [六神列表],
        }
    """
    # 卦名
    hex_detail = HEXAGRAM_DATA.get(
        (upper_num, lower_num),
        {"name": f"{NUM_TO_GUA_NAME[upper_num]}{NUM_TO_GUA_NAME[lower_num]}"},
    )
    hexagram_name = hex_detail.get("name", "未知卦")

    # 卦宫
    palace_info = get_hexagram_palace(upper_num, lower_num)
    palace_name = palace_info["palace_name"]
    palace_wuxing = palace_info["palace_wuxing"]
    palace_role = palace_info.get("palace_role", "未知")

    # 世应
    shi_ying_info = get_shi_ying(hexagram_name)
    shi_pos = shi_ying_info.get("shi", 0)
    ying_pos = shi_ying_info.get("ying", 0)

    # 纳甲
    najia_list = get_najia_all_lines(upper_num, lower_num)

    # 六亲
    liuqin_list = get_liuqin_all_lines(upper_num, lower_num, palace_wuxing)

    # 六神
    liushen_list = arrange_liushen_for_hexagram(solar)

    # 十二长生
    changsheng_list = get_changsheng_all_lines(upper_num, lower_num)

    day_ganzhi = get_accurate_day_ganzhi(solar)
    day_dizhi = get_day_dizhi(solar)
    xunkong_info = get_xunkong(day_ganzhi=day_ganzhi)
    yueling = ""
    if isinstance(lunar_info, dict):
        yueling = lunar_info.get("yueling", "")

    yuepo = DIZHI_CHONG.get(yueling, "") if yueling else ""
    ripo = DIZHI_CHONG.get(day_dizhi, "") if day_dizhi else ""

    # 爻位名称
    position_names = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}

    # 组装每爻信息
    lines = []
    for pos in range(1, 7):
        nj = najia_list[pos - 1]
        tiangan = nj[0] if nj and len(nj) >= 2 else "?"
        dizhi = nj[1] if nj and len(nj) >= 2 else "?"
        dizhi_wuxing = DIZHI_WUXING.get(dizhi, "土")
        liushen_name = liushen_list[pos - 1]
        changsheng = changsheng_list[pos - 1]
        nayin_name = NAYIN_TABLE.get(nj, "未知纳音")
        line_status = _build_line_status(dizhi, xunkong_info, yueling, day_dizhi)
        month_relations = get_dizhi_relations(dizhi, yueling)
        day_relations = get_dizhi_relations(dizhi, day_dizhi)
        liushen_effect = _analyze_liushen_zhihua(dizhi_wuxing, liushen_name)
        lines.append({
            "position": pos,
            "position_name": position_names[pos],
            "najia": nj,
            "tiangan": tiangan,
            "tiangan_wuxing": TIANGAN_WUXING.get(tiangan, "土"),
            "dizhi": dizhi,
            "dizhi_wuxing": dizhi_wuxing,
            "liuqin": liuqin_list[pos - 1],
            "liushen": liushen_name,
            "liushen_wuxing": liushen_effect["liushen_wuxing"],
            "liushen_effect": liushen_effect["effect"],
            "liushen_effect_score": liushen_effect["score"],
            "changsheng": changsheng,
            "changsheng_power": CHANGSHENG_POWER.get(changsheng, 0),
            "nayin": nayin_name,
            "nayin_wuxing": NAYIN_NAME_TO_WUXING.get(nayin_name, "未知"),
            "line_status": line_status,
            "is_xunkong": "旬空" in line_status,
            "is_yuepo": "月破" in line_status,
            "is_ripo": "日破" in line_status,
            "month_relations": month_relations,
            "day_relations": day_relations,
            "is_shi": pos == shi_pos,
            "is_ying": pos == ying_pos,
            "is_dong": False,
        })

    result = {
        "hexagram_name": hexagram_name,
        "hexagram_key": (upper_num, lower_num),
        "palace_name": palace_name,
        "palace_wuxing": palace_wuxing,
        "palace_role": palace_role,
        "palace_index": palace_info.get("palace_index", -1),
        "shi_ying": {"shi": shi_pos, "ying": ying_pos},
        "lines": lines,
        "liushen_by_day": liushen_list,
        "day_ganzhi": day_ganzhi,
        "day_dizhi": day_dizhi,
        "xunkong": xunkong_info,
        "yueling": yueling,
        "yuepo": yuepo,
        "ripo": ripo,
    }
    return refresh_line_strengths(result)


# ------------------------------------------------------------
# 9. 装卦表格式化输出
# ------------------------------------------------------------

def format_zhuanggua_table(zhuanggua_result, dong_yao=None):
    """将装卦结果格式化为紧凑可打印的表格。"""
    lines_data = zhuanggua_result["lines"]
    hexagram_name = zhuanggua_result["hexagram_name"]
    palace_name = zhuanggua_result["palace_name"]
    palace_wuxing = zhuanggua_result["palace_wuxing"]
    palace_role = zhuanggua_result.get("palace_role", "未知")
    shi_pos = zhuanggua_result["shi_ying"]["shi"]
    ying_pos = zhuanggua_result["shi_ying"]["ying"]

    result = []
    for line in reversed(lines_data):
        marks = ""
        if line["is_shi"]:
            marks += " 世"
        if line["is_ying"]:
            marks += " 应"
        if line.get("is_dong"):
            marks += " →动"
        status = " ".join(line["line_status"]) if line["line_status"] else ""
        result.append(
            f"  {line['position_name']} {line['najia']} {line['dizhi_wuxing']} "
            f"{line['liuqin']} {line['liushen']}{marks}  {status}"
        )

    header = (
        f"卦名：{hexagram_name}  卦宫：{palace_name}宫（{palace_wuxing}，{palace_role}）  "
        f"世爻：第{shi_pos}爻  应爻：第{ying_pos}爻"
    )
    footer = (
        f"日辰：{zhuanggua_result.get('day_ganzhi', '未知')}  "
        f"旬空：{'、'.join(zhuanggua_result.get('xunkong', {}).get('empty_branches', [])) or '无'}  "
        f"月建：{zhuanggua_result.get('yueling', '未知')}  "
        f"月破：{zhuanggua_result.get('yuepo', '未知')}"
    )
    return "\n".join([header] + result + [footer])


# ------------------------------------------------------------
# 10. 六亲格局分析辅助
# ------------------------------------------------------------

def get_yongshen_name(question_category):
    """
    根据问题类别推断用神六亲。

    参数：
        question_category: 问题类别（如"求财"、"求官"等）

    返回：
        str: 用神六亲名称
    """
    inferred = infer_yongshen_from_question(question_category)
    if inferred.get("primary"):
        return inferred["primary"]
    for category, yongshen in YONGSHEN_QUERY.items():
        if category in question_category:
            return yongshen
    return "妻财"


def find_yongshen_position(zhuanggua_result, yongshen_name):
    """
    在装卦结果中查找用神所在爻位。

    返回：
        list[int]: 用神出现的爻位列表
    """
    positions = []
    for line in zhuanggua_result["lines"]:
        if line["liuqin"] == yongshen_name:
            positions.append(line["position"])
    return positions


def get_shishen_liuqin(zhuanggua_result):
    """
    获取世爻的六亲。

    返回：
        str: 世爻六亲名称
    """
    for line in zhuanggua_result["lines"]:
        if line["is_shi"]:
            return line["liuqin"]
    return "未知"


def get_original_god(yongshen_wuxing, palace_wuxing):
    """
    找回用神的原神（生用神者）。

    返回：
        str: 原神五行
    """
    for sheng, target in WUXING_SHENG.items():
        if target == yongshen_wuxing:
            return sheng
    return "土"


def get_aversion_god(yongshen_wuxing):
    """
    找回用神的忌神（克用神者）。

    返回：
        str: 忌神五行
    """
    for ke, target in WUXING_KE.items():
        if target == yongshen_wuxing:
            return ke
    return "土"


def analyze_liuqin_summary(zhuanggua_result, dong_yao=None):
    """
    生成六亲格局简要分析。

    返回：
        str: 六亲分析文本
    """
    lines = zhuanggua_result["lines"]
    summary = []

    # 世爻信息
    shi_line = None
    for line in lines:
        if line["is_shi"]:
            shi_line = line
            break

    if shi_line:
        summary.append(f"世爻居{shi_line['position_name']}，六亲为{shi_line['liuqin']}，"
                       f"纳甲{shi_line['najia']}，{shi_line['changsheng']}之地")
        if dong_yao and shi_line["position"] == dong_yao:
            summary.append("世爻发动，自身必有变动")

    # 六亲分布
    liuqin_count = {}
    for line in lines:
        lq = line["liuqin"]
        liuqin_count[lq] = liuqin_count.get(lq, 0) + 1

    distribution = "、".join([f"{k}{v}现" for k, v in liuqin_count.items()])
    summary.append(f"六亲分布：{distribution}")

    # 动爻六亲
    if dong_yao:
        dong_line = lines[dong_yao - 1]
        dong_liuqin = dong_line["liuqin"]
        summary.append(f"动爻为第{dong_yao}爻，六亲{dong_liuqin}，"
                       f"纳甲{dong_line['najia']}，{dong_line['changsheng']}之地")

    return "；".join(summary)


def analyze_dizhi_relation_summary(zhuanggua_result, dong_yao=None, yongshen_name=None):
    """分析动爻、世爻、用神与月日的刑冲合害。"""
    lines = zhuanggua_result["lines"]
    tips = []

    shi_line = next((line for line in lines if line["is_shi"]), None)
    dong_line = lines[dong_yao - 1] if dong_yao and 1 <= dong_yao <= 6 else None

    if shi_line and dong_line:
        relations = get_dizhi_relations(dong_line["dizhi"], shi_line["dizhi"])
        if relations:
            tips.append(
                f"动爻{dong_line['position_name']}{dong_line['dizhi']}与世爻"
                f"{shi_line['position_name']}{shi_line['dizhi']}形成{_build_relation_text(relations)}"
            )
        else:
            tips.append("动爻与世爻无直接刑冲合害，变化对主体影响较间接")

    important_lines = [
        line for line in lines
        if line["is_shi"] or line["is_ying"] or line.get("is_dong") or line["line_status"]
    ]
    for line in important_lines:
        month_relation = _build_relation_text(line["month_relations"])
        day_relation = _build_relation_text(line["day_relations"])
        status = "、".join(line["line_status"]) if line["line_status"] else "无特殊空破"
        tips.append(
            f"{line['position_name']}{line['liuqin']}临{line['dizhi']}："
            f"{status}，与月建{month_relation}，与日辰{day_relation}"
        )

    if yongshen_name:
        yong_lines = [line for line in lines if line["liuqin"] == yongshen_name]
        if yong_lines:
            yong_text = "、".join(
                f"{line['position_name']}{line['dizhi']}({line['changsheng']}{line['changsheng_power']:+g})"
                for line in yong_lines
            )
            tips.append(f"用神{yongshen_name}出现于：{yong_text}")

            ji_elements = {
                get_aversion_god(line["dizhi_wuxing"])
                for line in yong_lines
            }
            ji_lines = [line for line in lines if line["dizhi_wuxing"] in ji_elements]
            if ji_lines:
                ji_text = "、".join(f"{line['position_name']}{line['dizhi']}" for line in ji_lines)
                tips.append(f"忌神候选爻位：{ji_text}，需结合动静、空破与月日关系再断")
        else:
            tips.append(f"用神{yongshen_name}未显，宜看伏象、世应与动爻代断")

    return "；".join(tips) if tips else "地支刑冲合害关系平稳，无明显冲合空破"


def analyze_nayin_summary(zhuanggua_result):
    """生成纳音五行摘要。"""
    lines = zhuanggua_result["lines"]
    focus_lines = [
        line for line in lines
        if line["is_shi"] or line["is_ying"] or line.get("is_dong")
    ]
    if not focus_lines:
        focus_lines = lines

    return "；".join(
        f"{line['position_name']}{line['liuqin']}纳音{line['nayin']}，纳音五行{line['nayin_wuxing']}"
        for line in focus_lines
    )


def analyze_liushen_zhihua_summary(zhuanggua_result):
    """生成六神与爻支五行制化摘要。"""
    lines = zhuanggua_result["lines"]
    focus_lines = [
        line for line in lines
        if line["is_shi"] or line["is_ying"] or line.get("is_dong")
    ]
    if not focus_lines:
        focus_lines = lines

    return "；".join(
        f"{line['position_name']}{line['liushen']}：{line['liushen_effect']}"
        for line in focus_lines
    )


def _lines_by_element(zhuanggua_result, element):
    return [
        line for line in zhuanggua_result.get("lines", [])
        if line.get("dizhi_wuxing") == element
    ]


def _best_lines(lines, limit=3):
    return sorted(
        lines,
        key=lambda line: (
            line.get("is_dong", False),
            line.get("strength_score", 0),
            not line.get("line_status", []),
        ),
        reverse=True,
    )[:limit]


def _format_line_group(lines, empty_text="无"):
    if not lines:
        return empty_text
    return "、".join(_format_line_brief(line) for line in _best_lines(lines))


def analyze_fushen(zhuanggua_result, missing_liuqin):
    """用本宫首卦查伏神，返回伏神与飞神的对应关系。"""
    lines = zhuanggua_result.get("lines", [])
    if any(line.get("liuqin") == missing_liuqin for line in lines):
        return {
            "has_fushen": False,
            "summary": f"{missing_liuqin}已在本卦出现，无需另取伏神。",
            "items": [],
        }

    palace_name = zhuanggua_result.get("palace_name", "")
    palace_wuxing = zhuanggua_result.get("palace_wuxing", "土")
    pure_upper, pure_lower = get_pure_palace_hexagram(palace_name)
    pure_najia = get_najia_all_lines(pure_upper, pure_lower)
    items = []

    for index, najia in enumerate(pure_najia, start=1):
        pure_liuqin = get_liuqin_for_line(najia, palace_wuxing)
        if pure_liuqin != missing_liuqin:
            continue
        fly_line = lines[index - 1] if index - 1 < len(lines) else {}
        fushen_dizhi = najia[1] if najia and len(najia) >= 2 else "?"
        fushen_element = DIZHI_WUXING.get(fushen_dizhi, "土")
        fly_element = fly_line.get("dizhi_wuxing", "土")
        if WUXING_SHENG.get(fushen_element) == fly_element:
            relation = "伏神生飞神，伏象泄气"
            score = -0.5
        elif WUXING_SHENG.get(fly_element) == fushen_element:
            relation = "飞神生伏神，伏象得扶"
            score = 1.0
        elif WUXING_KE.get(fushen_element) == fly_element:
            relation = "伏神克飞神，伏象欲出但有争"
            score = 0.3
        elif WUXING_KE.get(fly_element) == fushen_element:
            relation = "飞神克伏神，伏象受压"
            score = -1.2
        elif fushen_element == fly_element:
            relation = "伏飞同气"
            score = 0.8
        else:
            relation = "伏飞关系平"
            score = 0.0

        items.append({
            "position": index,
            "position_name": fly_line.get("position_name", f"第{index}爻"),
            "fushen_najia": najia,
            "fushen_dizhi": fushen_dizhi,
            "fushen_wuxing": fushen_element,
            "fly_line": fly_line,
            "relation": relation,
            "score": score,
        })

    if not items:
        return {
            "has_fushen": False,
            "summary": f"本宫首卦亦未找到{missing_liuqin}伏神，需以世应与动爻代断。",
            "items": [],
        }

    item_text = "、".join(
        f"{item['position_name']}伏{missing_liuqin}{item['fushen_najia']}({item['fushen_wuxing']})，"
        f"飞神为{item['fly_line'].get('liuqin', '未知')}{item['fly_line'].get('dizhi', '?')}，{item['relation']}"
        for item in items
    )
    return {
        "has_fushen": True,
        "summary": f"{missing_liuqin}不现，按{palace_name}宫本宫首卦取伏神：{item_text}。",
        "items": items,
    }


def analyze_yongshen_system(zhuanggua_result, question_text="", dong_yao=None):
    """建立用神、原神、忌神、仇神、伏神的证据链。"""
    refresh_line_strengths(zhuanggua_result)
    infer = infer_yongshen_from_question(question_text)
    yongshen_name = infer["primary"]
    if yongshen_name not in LIUQIN_XIANGYI:
        shi_line = next((line for line in zhuanggua_result.get("lines", []) if line.get("is_shi")), None)
        if shi_line:
            yongshen_name = shi_line.get("liuqin", "兄弟")
            infer = {
                **infer,
                "primary": yongshen_name,
                "reason": f"{infer.get('reason', '')} 当前世爻为{yongshen_name}，故以世爻六亲落点为主用。",
            }
    palace_wuxing = zhuanggua_result.get("palace_wuxing", "土")
    yongshen_element = get_liuqin_element(yongshen_name, palace_wuxing)
    yuan_element = _sheng_source(yongshen_element)
    ji_element = _ke_source(yongshen_element)
    chou_element = _chou_god_element(yuan_element, ji_element)

    lines = zhuanggua_result.get("lines", [])
    yong_lines = [line for line in lines if line.get("liuqin") == yongshen_name]
    yuan_lines = _lines_by_element(zhuanggua_result, yuan_element)
    ji_lines = _lines_by_element(zhuanggua_result, ji_element)
    chou_lines = _lines_by_element(zhuanggua_result, chou_element)
    fushen = analyze_fushen(zhuanggua_result, yongshen_name)

    yong_score = max([line.get("strength_score", -4) for line in yong_lines], default=-2.0)
    yuan_score = max([line.get("strength_score", -3) for line in yuan_lines], default=-1.0)
    ji_score = max([line.get("strength_score", -3) for line in ji_lines], default=0.0)
    chou_score = max([line.get("strength_score", -3) for line in chou_lines], default=0.0)
    fushen_score = max([item.get("score", 0.0) for item in fushen.get("items", [])], default=0.0)

    system_score = yong_score + max(yuan_score, 0) * 0.45 - max(ji_score, 0) * 0.55 - max(chou_score, 0) * 0.25
    if not yong_lines:
        system_score -= 1.2
        system_score += fushen_score * 0.6
    if dong_yao and 1 <= dong_yao <= 6:
        dong_line = lines[dong_yao - 1]
        if dong_line.get("liuqin") == yongshen_name:
            system_score += 1.2
        if dong_line.get("dizhi_wuxing") == yuan_element:
            system_score += 0.8
        if dong_line.get("dizhi_wuxing") == ji_element:
            system_score -= 1.0

    keyword_text = f"命中关键词：{'、'.join(infer['keywords'])}。" if infer.get("keywords") else ""
    secondary_text = f"；兼看{infer['secondary']}" if infer.get("secondary") else ""
    parts = [
        f"用神判断：{infer['category']}，取{yongshen_name}为用神{secondary_text}。{keyword_text}{infer['reason']}",
        f"用神五行为{yongshen_element}，现爻：{_format_line_group(yong_lines, '本卦不现')}",
        f"原神（生用神）为{yuan_element}：{_format_line_group(yuan_lines)}",
        f"忌神（克用神）为{ji_element}：{_format_line_group(ji_lines)}",
        f"仇神（克原神、生忌神）为{chou_element}：{_format_line_group(chou_lines)}",
    ]
    if fushen.get("has_fushen"):
        parts.append(fushen["summary"])

    if system_score >= 4:
        verdict = "用神证据偏强，传统断法上较可用"
    elif system_score >= 1.5:
        verdict = "用神有根但仍需看动变"
    elif system_score > -1:
        verdict = "用神力量中平，宜结合现实条件"
    elif system_score > -3:
        verdict = "用神偏弱，推进宜谨慎"
    else:
        verdict = "用神受制较重，不宜强行乐观"
    parts.append(f"用神系统评分：{system_score:+.1f}，{verdict}。")

    return {
        "inference": infer,
        "yongshen_name": yongshen_name,
        "yongshen_element": yongshen_element,
        "yuan_element": yuan_element,
        "ji_element": ji_element,
        "chou_element": chou_element,
        "yong_lines": yong_lines,
        "yuan_lines": yuan_lines,
        "ji_lines": ji_lines,
        "chou_lines": chou_lines,
        "fushen": fushen,
        "score": round(system_score, 1),
        "summary": "；".join(parts),
    }


def analyze_line_strength_summary(zhuanggua_result):
    """输出世应动与全卦强弱概览。"""
    refresh_line_strengths(zhuanggua_result)
    lines = zhuanggua_result.get("lines", [])
    focus = [line for line in lines if line.get("is_shi") or line.get("is_ying") or line.get("is_dong")]
    strongest = sorted(lines, key=lambda line: line.get("strength_score", 0), reverse=True)[:2]
    weakest = sorted(lines, key=lambda line: line.get("strength_score", 0))[:2]
    parts = []
    if focus:
        parts.append("关键爻：" + "、".join(_format_line_brief(line) for line in focus))
    parts.append("旺爻：" + "、".join(_format_line_brief(line) for line in strongest))
    parts.append("弱爻：" + "、".join(_format_line_brief(line) for line in weakest))
    return "；".join(parts)


def analyze_bian_line_relation(zhuanggua_result, bian_zhuanggua_result, dong_yao):
    """分析动爻化出变爻后的回头生克与地支关系。"""
    if not dong_yao or dong_yao < 1 or dong_yao > 6:
        return {
            "score": 0.0,
            "summary": "无有效动爻，暂不分析回头生克。",
        }

    refresh_line_strengths(zhuanggua_result)
    refresh_line_strengths(bian_zhuanggua_result)
    original = zhuanggua_result["lines"][dong_yao - 1]
    changed = bian_zhuanggua_result["lines"][dong_yao - 1]
    orig_element = original.get("dizhi_wuxing", "")
    changed_element = changed.get("dizhi_wuxing", "")
    score = 0.0

    if WUXING_SHENG.get(changed_element) == orig_element:
        relation = "回头生"
        score += 2.5
        effect = "变爻生扶动爻，事情后势有回补与助力"
    elif WUXING_KE.get(changed_element) == orig_element:
        relation = "回头克"
        score -= 3.0
        effect = "变爻克制动爻，后续压力反扑，需防结果反噬"
    elif changed_element == orig_element:
        relation = "化比和"
        score += 1.0
        effect = "变爻与动爻同气，事情延续性较强"
    elif WUXING_SHENG.get(orig_element) == changed_element:
        relation = "化泄"
        score -= 1.0
        effect = "动爻生出变爻，主有付出、泄力、资源外流"
    elif WUXING_KE.get(orig_element) == changed_element:
        relation = "化制"
        score -= 0.3
        effect = "动爻克变爻，能制其事但耗力"
    else:
        relation = "平化"
        effect = "动变五行关系平平"

    dizhi_relations = get_dizhi_relations(original.get("dizhi", ""), changed.get("dizhi", ""))
    if "冲" in dizhi_relations:
        score -= 1.0
    if "合" in dizhi_relations:
        score += 0.6
    if "刑" in dizhi_relations or "害" in dizhi_relations:
        score -= 0.6

    relation_text = _build_relation_text(dizhi_relations)
    summary = (
        f"动爻{original['position_name']}{original['liuqin']}{original['najia']}"
        f"化{changed['liuqin']}{changed['najia']}，{relation}。{effect}；"
        f"动变地支关系：{relation_text}；回头生克评分{score:+.1f}。"
    )
    return {
        "score": round(score, 1),
        "relation": relation,
        "summary": summary,
        "original_line": original,
        "changed_line": changed,
    }


def build_traditional_evidence_chain(zhuanggua_result, yongshen_system, bian_relation):
    """把传统变量整理成一条可审阅的依据链，并保留理性校验提醒。"""
    xunkong = "、".join(zhuanggua_result.get("xunkong", {}).get("empty_branches", [])) or "未知"
    yuepo = zhuanggua_result.get("yuepo", "未知")
    ripo = zhuanggua_result.get("ripo", "未知")
    palace = f"{zhuanggua_result.get('palace_name', '未知')}宫{zhuanggua_result.get('palace_role', '')}"
    return (
        f"传统依据链：先定{palace}与世应，再取月建{zhuanggua_result.get('yueling', '未知')}、"
        f"日辰{zhuanggua_result.get('day_dizhi', '未知')}、旬空{xunkong}、月破{yuepo}、日破{ripo}；"
        f"本问取{yongshen_system.get('yongshen_name', '未知')}为用神，"
        f"用神系统评分{yongshen_system.get('score', 0):+.1f}；"
        f"{bian_relation.get('summary', '')}"
        "现实校验：凡涉金钱、合同、健康、法律、职业选择，仍应以事实证据、成本、时间、责任边界和专业意见复核。"
    )
