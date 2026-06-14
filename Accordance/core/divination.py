# -*- coding: utf-8 -*-
"""
起卦核心逻辑

本文件尽量不强依赖外部库。
若环境安装了 zhdate，会优先读取农历年月日；
若未安装，则自动降级为公历日期近似值，保证程序不会因依赖缺失而崩溃。

核心功能：
1. 获取农历/时间信息
2. 传统时间起卦
3. 动态时间起卦
4. 动态三爻快占
5. 当日气运辅助单卦
6. 姓名起卦
7. 变卦计算
8. 简易干支辅助函数
"""

import datetime
from typing import Any, Dict, List, Optional, Tuple

from config.bagua_data import BAGUA_DATA, NUM_TO_GUA_NAME
from config.hexagram_data import HEXAGRAM_DATA, HUGUA_MAP, TRIGRAM_CUO, TRIGRAM_ZONG
from config.wuxing_rules import WUXING_SHENG, WUXING_KE
from core.qi_context import (
    build_qi_seed,
    normalize_mod,
    get_accurate_day_ganzhi,
    get_day_tiangan,
    get_yueling_by_solar,
    get_season_by_yueling,
    get_shichen_by_hour,
)


# ------------------------------------------------------------
# 八卦三爻映射
# 1 为阳爻，0 为阴爻
# 顺序保持与 BAGUA_DATA 编号一致：
# 1乾、2兑、3离、4震、5巽、6坎、7艮、8坤
# ------------------------------------------------------------

YaoTuple = Tuple[int, int, int]

YAO_TO_GUA_NUM: Dict[YaoTuple, int] = {
    (1, 1, 1): 1,  # 乾 ☰
    (1, 1, 0): 2,  # 兑 ☱
    (1, 0, 1): 3,  # 离 ☲
    (1, 0, 0): 4,  # 震 ☳
    (0, 1, 1): 5,  # 巽 ☴
    (0, 1, 0): 6,  # 坎 ☵
    (0, 0, 1): 7,  # 艮 ☶
    (0, 0, 0): 8,  # 坤 ☷
}

GUA_NUM_TO_YAO: Dict[int, YaoTuple] = {
    value: key for key, value in YAO_TO_GUA_NUM.items()
}


DIZHI_ORDER: List[str] = [
    "子", "丑", "寅", "卯", "辰", "巳",
    "午", "未", "申", "酉", "戌", "亥"
]

GAN_ORDER: List[str] = [
    "甲", "乙", "丙", "丁", "戊",
    "己", "庚", "辛", "壬", "癸"
]


# ------------------------------------------------------------
# 基础时间与干支辅助
# ------------------------------------------------------------

def get_year_dizhi(year: int) -> str:
    """
    按年份粗略换算年支。

    说明：
    这里以 2020 年为子年进行序列推算。
    若后续需要严格节气换年，可进一步接入专业干支库。
    """
    return DIZHI_ORDER[(year - 2020) % 12]


def get_year_num(year: int) -> int:
    """
    年支序数：
    子为1，丑为2，……，亥为12。
    """
    return DIZHI_ORDER.index(get_year_dizhi(year)) + 1


def get_season_by_month(month: int) -> str:
    """
    按农历月份判断旺衰季节。

    3-5：春
    6-8：夏
    9-11：秋
    12-2：冬
    """
    if 3 <= month <= 5:
        return "春"

    if 6 <= month <= 8:
        return "夏"

    if 9 <= month <= 11:
        return "秋"

    return "冬"


def get_lunar_time() -> Dict[str, Any]:
    """
    获取当前时间、农历信息与旺衰季节。

    返回字段保持稳定，供所有模块调用：
    year / month / day / hour / shi_chen / season / yueling /
    year_dizhi / year_num / current_jieqi / solar / lunar

    若未安装 zhdate，则使用公历年月日作为近似农历信息，
    以保证项目基础功能可运行。
    """
    now = datetime.datetime.now()

    lunar_year = now.year
    lunar_month = now.month
    lunar_day = now.day
    lunar_source = "按公历近似农历"

    try:
        from zhdate import ZhDate  # type: ignore

        zh_date = ZhDate.from_datetime(now)
        lunar_year = int(zh_date.lunar_year)
        lunar_month = int(zh_date.lunar_month)
        lunar_day = int(zh_date.lunar_day)
        lunar_obj: Optional[Any] = zh_date
        lunar_source = "zhdate农历"

    except (ImportError, AttributeError, ValueError, TypeError):
        lunar_obj = None

    hour = now.hour

    # 十二时辰序号：子=1，丑=2，……，亥=12；23:00-00:59 均属子时。
    shi_chen_num = get_shichen_by_hour(hour)

    # 六爻月建以节气为界，农历月只保留给梅花年月日时起卦。
    yueling = get_yueling_by_solar(now)
    season = get_season_by_yueling(yueling)
    current_jieqi = f"节气月建近似：{yueling}月；农历来源：{lunar_source}"
    year_dizhi = get_year_dizhi(lunar_year)
    year_num = get_year_num(lunar_year)

    return {
        "year": lunar_year,
        "month": lunar_month,
        "day": lunar_day,
        "hour": hour,
        "shi_chen": shi_chen_num,
        "season": season,
        "yueling": yueling,
        "year_dizhi": year_dizhi,
        "year_num": year_num,
        "current_jieqi": current_jieqi,
        "solar": now,
        "lunar": lunar_obj,
    }


# ------------------------------------------------------------
# 起卦核心
# ------------------------------------------------------------

def time_qi_gua() -> Dict[str, Any]:
    """
    传统时间起卦。

    规则：
    年 + 月 + 日 → 上卦
    年 + 月 + 日 + 时辰 → 下卦
    年 + 月 + 日 + 时辰 → 动爻

    除尽时：
    八卦取 8
    动爻取 6
    """
    lunar_info = get_lunar_time()

    year_num = int(lunar_info["year_num"])
    month_num = int(lunar_info["month"])
    day_num = int(lunar_info["day"])
    shi_chen_num = int(lunar_info["shi_chen"])

    upper_num = normalize_mod(year_num + month_num + day_num, 8)
    lower_num = normalize_mod(year_num + month_num + day_num + shi_chen_num, 8)
    dong_yao = normalize_mod(year_num + month_num + day_num + shi_chen_num, 6)

    upper_gua = BAGUA_DATA[upper_num]
    lower_gua = BAGUA_DATA[lower_num]

    return {
        "upper_gua": upper_gua,
        "lower_gua": lower_gua,
        "upper_num": upper_num,
        "lower_num": lower_num,
        "dong_yao": dong_yao,
        "lunar_info": lunar_info,
        "gua_full_name": f"{upper_gua['name']}{lower_gua['name']}{lower_gua['xiang']}",
    }


def dynamic_time_qi_gua(
    question: str = "",
    mode: str = "full",
    extra_text: str = "",
    focus_seed: int = 0,
) -> Dict[str, Any]:
    """
    动态时间起卦。

    与传统 time_qi_gua() 的区别：
    1. 保留农历年、月、日、时辰作为天时基础；
    2. 加入问题文字，体现所问之事；
    3. 加入用户停顿时间，体现人念；
    4. 加入当前分钟、秒、毫秒，体现起卦瞬间；
    5. 加入 mode 和 extra_text，使不同模块拥有不同气机入口。

    结果不是纯随机，但同一问题在不同气机下会产生不同卦象。
    """
    lunar_info = get_lunar_time()

    year_num = int(lunar_info["year_num"])
    month_num = int(lunar_info["month"])
    day_num = int(lunar_info["day"])
    shi_chen_num = int(lunar_info["shi_chen"])

    qi_seed = build_qi_seed(
        question=question,
        mode=mode,
        extra_text=extra_text,
        focus_seed=focus_seed,
    )

    upper_seed = year_num + month_num + day_num + qi_seed
    lower_seed = year_num + month_num + day_num + shi_chen_num + (qi_seed // 2)
    dong_yao_seed = year_num + month_num + day_num + shi_chen_num + (qi_seed // 3)

    upper_num = normalize_mod(upper_seed, 8)
    lower_num = normalize_mod(lower_seed, 8)
    dong_yao = normalize_mod(dong_yao_seed, 6)

    upper_gua = BAGUA_DATA[upper_num]
    lower_gua = BAGUA_DATA[lower_num]

    return {
        "upper_gua": upper_gua,
        "lower_gua": lower_gua,
        "upper_num": upper_num,
        "lower_num": lower_num,
        "dong_yao": dong_yao,
        "lunar_info": lunar_info,
        "gua_full_name": f"{upper_gua['name']}{lower_gua['name']}{lower_gua['xiang']}",
        "qi_seed": qi_seed,
        "question": question,
        "mode": mode,
        "extra_text": extra_text,
        "focus_seed": focus_seed,
    }


def three_yao_quick_divination() -> Dict[str, Any]:
    """
    普通三爻快占。

    保留接口兼容旧模块。
    当前版本不再依赖 random，而是调用动态三爻逻辑。
    """
    return dynamic_three_yao_quick_divination(mode="quick_legacy")


def dynamic_three_yao_quick_divination(
    question: str = "",
    mode: str = "quick",
    extra_text: str = "",
    focus_seed: int = 0,
) -> Dict[str, Any]:
    """
    动态三爻快占。

    使用：
    1. 当前农历时间
    2. 起卦瞬间
    3. 用户问题文本
    4. 用户按回车前的停顿时间
    5. 起卦模式与额外文本

    共同生成三爻。
    """
    lunar_info = get_lunar_time()

    qi_seed = build_qi_seed(
        question=question,
        mode=mode,
        extra_text=extra_text,
        focus_seed=focus_seed,
    )

    year_num = int(lunar_info["year_num"])
    month_num = int(lunar_info["month"])
    day_num = int(lunar_info["day"])
    shi_chen_num = int(lunar_info["shi_chen"])

    base_seed = year_num + month_num + day_num + shi_chen_num + qi_seed

    # 生成三爻：
    # 1 为阳，0 为阴。
    yao_1 = int((base_seed + month_num + focus_seed) % 2)
    yao_2 = int((base_seed + day_num + qi_seed // 3) % 2)
    yao_3 = int((base_seed + shi_chen_num + qi_seed // 7) % 2)

    yao_key: YaoTuple = (yao_1, yao_2, yao_3)
    yao_list = [yao_1, yao_2, yao_3]

    gua_num = YAO_TO_GUA_NUM[yao_key]
    gua_info = BAGUA_DATA[gua_num]

    return {
        "gua_info": gua_info,
        "yao_list": yao_list,
        "lunar_info": lunar_info,
        "gua_hua": gua_info["gua_hua"],
        "qi_seed": qi_seed,
        "question": question,
        "mode": mode,
        "extra_text": extra_text,
        "focus_seed": focus_seed,
    }


def daily_guidance_gua() -> Dict[str, Any]:
    """
    当日气运辅助单卦。

    设计原则：
    1. 当日气运不应像快占一样每次刷新都剧烈变化；
    2. 因此不使用 random，也不使用用户停顿时间；
    3. 只根据农历年、月、日生成当日辅助单卦；
    4. 同一天内结果相对稳定，跨日自然变化。
    """
    lunar_info = get_lunar_time()

    year_num = int(lunar_info["year_num"])
    month_num = int(lunar_info["month"])
    day_num = int(lunar_info["day"])

    gua_seed = year_num + month_num * 2 + day_num * 3
    gua_num = normalize_mod(gua_seed, 8)

    gua_info = BAGUA_DATA[gua_num]
    yao_tuple = GUA_NUM_TO_YAO[gua_num]
    yao_list = list(yao_tuple)

    return {
        "gua_info": gua_info,
        "yao_list": yao_list,
        "lunar_info": lunar_info,
        "gua_hua": gua_info["gua_hua"],
        "mode": "daily_guidance",
    }


# ------------------------------------------------------------
# 姓名起卦
# ------------------------------------------------------------

def _ask_positive_int(prompt: str) -> int:
    """
    安全读取正整数。
    用于姓名起卦笔画数输入，避免用户输入非数字导致程序崩溃。
    """
    while True:
        value = input(prompt).strip()

        try:
            number = int(value)
        except ValueError:
            print("输入无效，请输入整数。")
            continue

        if number <= 0:
            print("笔画数应为正整数，请重新输入。")
            continue

        return number


def name_qi_gua(
    xing: str,
    ming: str,
    xing_stroke: Optional[int] = None,
    ming_stroke: Optional[int] = None,
) -> Dict[str, Any]:
    """
    姓名起卦法。

    xing / ming：
        用户输入的姓氏与名字，用于提示与记录。

    xing_stroke / ming_stroke：
        姓氏与名字的笔画数。

    若调用方未传入笔画数，本函数会兜底询问一次，
    避免旧模块调用时报错。

    规则：
    姓氏总笔画数 ÷ 8 → 上卦
    名字总笔画数 ÷ 8 → 下卦
    姓氏笔画 + 名字笔画 → 动爻
    """
    lunar_info = get_lunar_time()

    if xing_stroke is None:
        xing_stroke_value = _ask_positive_int(
            f"请输入姓氏「{xing}」的康熙字典总笔画数："
        )
    else:
        xing_stroke_value = int(xing_stroke)

    if ming_stroke is None:
        ming_stroke_value = _ask_positive_int(
            f"请输入名字「{ming}」的康熙字典总笔画数："
        )
    else:
        ming_stroke_value = int(ming_stroke)

    if xing_stroke_value <= 0:
        raise ValueError("姓氏笔画数必须为正整数")

    if ming_stroke_value <= 0:
        raise ValueError("名字笔画数必须为正整数")

    upper_num = normalize_mod(xing_stroke_value, 8)
    lower_num = normalize_mod(ming_stroke_value, 8)
    dong_yao = normalize_mod(xing_stroke_value + ming_stroke_value, 6)

    upper_gua = BAGUA_DATA[upper_num]
    lower_gua = BAGUA_DATA[lower_num]

    return {
        "upper_gua": upper_gua,
        "lower_gua": lower_gua,
        "upper_num": upper_num,
        "lower_num": lower_num,
        "dong_yao": dong_yao,
        "lunar_info": lunar_info,
        "gua_full_name": f"{upper_gua['name']}{lower_gua['name']}{lower_gua['xiang']}",
        "xing": xing,
        "ming": ming,
        "xing_stroke": xing_stroke_value,
        "ming_stroke": ming_stroke_value,
    }


# ------------------------------------------------------------
# 变卦计算
# ------------------------------------------------------------

def calculate_bian_gua(
    upper_num: int,
    lower_num: int,
    dong_yao: int,
) -> Tuple[int, int]:
    """
    根据动爻计算变卦。

    dong_yao = 1 为初爻；
    dong_yao = 6 为上爻。

    GUA_NUM_TO_YAO 的三爻顺序为从下到上；
    六爻内部也按初爻到上爻排列：
    lower_yao + upper_yao。
    """
    if upper_num not in GUA_NUM_TO_YAO:
        raise ValueError(f"非法上卦编号：{upper_num}")

    if lower_num not in GUA_NUM_TO_YAO:
        raise ValueError(f"非法下卦编号：{lower_num}")

    if dong_yao < 1 or dong_yao > 6:
        raise ValueError(f"非法动爻编号：{dong_yao}")

    upper_yao = list(GUA_NUM_TO_YAO[upper_num])
    lower_yao = list(GUA_NUM_TO_YAO[lower_num])

    all_yao = lower_yao + upper_yao

    yao_index = dong_yao - 1
    all_yao[yao_index] = 1 - all_yao[yao_index]

    bian_lower_yao: YaoTuple = (
        int(all_yao[0]),
        int(all_yao[1]),
        int(all_yao[2]),
    )

    bian_upper_yao: YaoTuple = (
        int(all_yao[3]),
        int(all_yao[4]),
        int(all_yao[5]),
    )

    bian_upper_num = YAO_TO_GUA_NUM[bian_upper_yao]
    bian_lower_num = YAO_TO_GUA_NUM[bian_lower_yao]

    return bian_upper_num, bian_lower_num


# ------------------------------------------------------------
# 干支与五行辅助
# ------------------------------------------------------------

def get_ganzhi_wuxing(ganzhi: str) -> str:
    """
    获取天干五行。

    用于兼容解卦模块中的纳甲辅助函数。
    若输入为空或无法识别，则默认返回土。
    """
    if not ganzhi:
        return "土"

    gan_wuxing = {
        "甲": "木",
        "乙": "木",
        "丙": "火",
        "丁": "火",
        "戊": "土",
        "己": "土",
        "庚": "金",
        "辛": "金",
        "壬": "水",
        "癸": "水",
    }

    return gan_wuxing.get(ganzhi[0], "土")


def get_day_ganzhi(lunar_info: Dict[str, Any]) -> str:
    """
    基于儒略日的精确日干支计算。

    代替之前的简化推算，精度与万年历一致。
    """
    solar = lunar_info.get("solar")

    if not isinstance(solar, datetime.datetime):
        solar = datetime.datetime.now()

    return get_accurate_day_ganzhi(solar)


# ------------------------------------------------------------
# 互卦、错卦、综卦计算
# ------------------------------------------------------------

def calculate_hugua(upper_num: int, lower_num: int) -> Tuple[int, int]:
    """
    计算互卦（交互卦/卦中卦）。

    取本卦第二、三、四爻为下卦，第三、四、五爻为上卦。
    互卦揭示事情发展的中间过程与隐藏因素。

    返回：
        (hu_upper_num, hu_lower_num): 互卦上下卦编号
    """
    if (upper_num, lower_num) in HUGUA_MAP:
        return HUGUA_MAP[(upper_num, lower_num)]
    return upper_num, lower_num


def calculate_cuogua(upper_num: int, lower_num: int) -> Tuple[int, int]:
    """
    计算错卦（旁通卦/对卦）。

    将六爻卦中每一爻的阴阳属性全部取反。
    错卦代表事物向其对立面转化，从相反角度审视问题。

    返回：
        (cuo_upper_num, cuo_lower_num): 错卦上下卦编号
    """
    if upper_num in TRIGRAM_CUO:
        cuo_upper = TRIGRAM_CUO[upper_num]
    else:
        cuo_upper = upper_num

    if lower_num in TRIGRAM_CUO:
        cuo_lower = TRIGRAM_CUO[lower_num]
    else:
        cuo_lower = lower_num

    return cuo_upper, cuo_lower


def calculate_zonggua(upper_num: int, lower_num: int) -> Tuple[int, int]:
    """
    计算综卦（覆卦/反卦）。

    将本卦上下颠倒180度。
    综卦代表换位思考，从对方立场审视同一事物。

    八纯卦中的自综卦：乾、坤、离、坎、大过、小过、颐、中孚
    这些卦颠倒后仍为自身。

    返回：
        (zong_upper_num, zong_lower_num): 综卦上下卦编号
    """
    # 综卦：上卦颠倒为下卦，下卦颠倒为上卦
    if upper_num in TRIGRAM_ZONG:
        zong_lower = TRIGRAM_ZONG[upper_num]
    else:
        zong_lower = upper_num

    if lower_num in TRIGRAM_ZONG:
        zong_upper = TRIGRAM_ZONG[lower_num]
    else:
        zong_upper = lower_num

    return zong_upper, zong_lower


# ------------------------------------------------------------
# 体用识别（梅花易数）
# ------------------------------------------------------------

def identify_tiyong(upper_num: int, lower_num: int, dong_yao: int) -> Dict[str, Any]:
    """
    梅花易数体用识别。

    规则：
    - 动爻在上卦（第4/5/6爻）→ 用卦在上卦，体卦在下卦
    - 动爻在下卦（第1/2/3爻）→ 用卦在下卦，体卦在上卦

    体卦代表求测者本人，用卦代表所问之事/对方/外部环境。

    返回：
        dict: {
            "ti_gua_num": int,        # 体卦编号
            "yong_gua_num": int,      # 用卦编号
            "ti_gua_name": str,       # 体卦名称
            "yong_gua_name": str,     # 用卦名称
            "ti_element": str,        # 体卦五行
            "yong_element": str,      # 用卦五行
            "relation": str,          # 体用关系（用生体/体克用/比和/体生用/用克体）
            "relation_desc": str,     # 关系描述
        }
    """
    if dong_yao >= 4:
        # 动爻在上卦 → 上卦为用，下卦为体
        yong_num = upper_num
        ti_num = lower_num
    else:
        # 动爻在下卦 → 下卦为用，上卦为体
        yong_num = lower_num
        ti_num = upper_num

    ti_gua = BAGUA_DATA[ti_num]
    yong_gua = BAGUA_DATA[yong_num]

    ti_element = ti_gua["element"]
    yong_element = yong_gua["element"]

    # 判断体用五行关系
    relation = ""
    relation_desc = ""

    if WUXING_SHENG.get(yong_element) == ti_element:
        relation = "用生体"
        relation_desc = "大吉：外界助我，好事送上门，有进益之喜，不费力可成"
    elif ti_element == yong_element:
        relation = "比和"
        relation_desc = "吉利：五行相同，百事顺遂，势均力敌，顺利和乐"
    elif WUXING_KE.get(ti_element) == yong_element:
        relation = "体克用"
        relation_desc = "小吉（吉带凶）：我方掌控局面，辛苦费力但能成事"
    elif WUXING_SHENG.get(ti_element) == yong_element:
        relation = "体生用"
        relation_desc = "小凶（泄气）：自己耗心力、为他人作嫁衣，付出多、有损耗"
    elif WUXING_KE.get(yong_element) == ti_element:
        relation = "用克体"
        relation_desc = "大凶：受人牵制，被动挨打，诸事难成，有损耗"

    return {
        "ti_gua_num": ti_num,
        "yong_gua_num": yong_num,
        "ti_gua_name": ti_gua["name"],
        "yong_gua_name": yong_gua["name"],
        "ti_gua_full": ti_gua["full_name"],
        "yong_gua_full": yong_gua["full_name"],
        "ti_element": ti_element,
        "yong_element": yong_element,
        "relation": relation,
        "relation_desc": relation_desc,
        "ti_gua_data": ti_gua,
        "yong_gua_data": yong_gua,
    }
