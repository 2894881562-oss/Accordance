# -*- coding: utf-8 -*-
"""
起卦气机上下文模块

核心思想：
不使用纯随机作为主要依据，而是采集：
1. 当前天时
2. 用户停顿时间
3. 问题文本
4. 起卦模式
5. 起卦瞬间的分钟、秒、毫秒

用于生成“起卦瞬间”的扰动因子。

这样同一个问题在不同起卦瞬间可能得到不同结果，
但这种变化并不是无意义随机，而是由天时、人念、问题文本共同形成。
"""

import time
import datetime
import math


# ------------------------------------------------------------
# 精确日干支计算（儒略日法）
# ------------------------------------------------------------

# 六十甲子表
JIAZI_TABLE = [
    "甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未",
    "壬申", "癸酉", "甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯",
    "庚辰", "辛巳", "壬午", "癸未", "甲申", "乙酉", "丙戌", "丁亥",
    "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳", "甲午", "乙未",
    "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯",
    "甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥",
    "壬子", "癸丑", "甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未",
    "庚申", "辛酉", "壬戌", "癸亥",
]


def _gregorian_to_jd(year, month, day):
    """
    公历日期转儒略日（Julian Day）。

    使用标准天文算法，适用于公元后的日期。
    精度足以支撑日干支计算。
    """
    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + a // 4

    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
    return int(jd)


def get_accurate_day_ganzhi(solar=None):
    """
    基于儒略日的高精度日干支计算。

    参数：
        solar: datetime.datetime 对象，默认为当前时间

    返回：
        str: 六十甲子日柱（如"甲子"、"乙丑"等）

    算法：
        以1900年1月1日（甲戌日）为基准日，
        计算目标日期与基准日之间的天数差，
        通过 mod 60 得到六十甲子序数。
    """
    if solar is None:
        solar = datetime.datetime.now()

    target_jd = _gregorian_to_jd(solar.year, solar.month, solar.day)
    base_jd = _gregorian_to_jd(1900, 1, 1)

    delta_days = target_jd - base_jd

    # 1900年1月1日为甲戌日，序数为10
    jiazi_index = (delta_days + 10) % 60
    return JIAZI_TABLE[jiazi_index]


def get_day_tiangan(solar=None):
    """
    获取当日天干。

    返回：
        str: 天干（甲、乙、丙、丁、戊、己、庚、辛、壬、癸）
    """
    ganzhi = get_accurate_day_ganzhi(solar)
    return ganzhi[0]


def get_day_dizhi(solar=None):
    """
    获取当日地支。

    返回：
        str: 地支（子、丑、寅、卯、辰、巳、午、未、申、酉、戌、亥）
    """
    ganzhi = get_accurate_day_ganzhi(solar)
    return ganzhi[1]


def get_xunkong(day_ganzhi=None, solar=None):
    """
    计算旬空（空亡）。

    六十甲子每十日为一旬，每旬余下两个地支为空亡：
    甲子旬戌亥空，甲戌旬申酉空，甲申旬午未空，
    甲午旬辰巳空，甲辰旬寅卯空，甲寅旬子丑空。
    """
    if day_ganzhi is None:
        day_ganzhi = get_accurate_day_ganzhi(solar)

    if day_ganzhi not in JIAZI_TABLE:
        return {
            "day_ganzhi": day_ganzhi,
            "xun_name": "未知旬",
            "empty_branches": [],
        }

    index = JIAZI_TABLE.index(day_ganzhi)
    xun_index = index // 10
    xun_names = ["甲子旬", "甲戌旬", "甲申旬", "甲午旬", "甲辰旬", "甲寅旬"]
    xunkong_map = [
        ["戌", "亥"],
        ["申", "酉"],
        ["午", "未"],
        ["辰", "巳"],
        ["寅", "卯"],
        ["子", "丑"],
    ]

    return {
        "day_ganzhi": day_ganzhi,
        "xun_name": xun_names[xun_index],
        "empty_branches": xunkong_map[xun_index],
    }


def get_year_ganzhi(year):
    """
    年干支计算（以立春为界做近似处理）。

    以1984年（甲子年）为基准推算。
    精确分界需要节气计算，这里提供近似值。
    """
    base_year = 1984
    diff = year - base_year
    index = diff % 60
    return JIAZI_TABLE[index]


def get_shichen_ganzhi(day_tiangan, shichen_num):
    """
    根据日天干和时辰序号计算时干支。

    口诀：甲己还加甲，乙庚丙作初，丙辛从戊起，丁壬庚子居，戊癸何方发，壬子是真途。

    参数：
        day_tiangan: 日天干
        shichen_num: 时辰序号（子=1, 丑=2, ..., 亥=12）

    返回：
        str: 时干支
    """
    shichen_start_map = {
        "甲": "甲", "己": "甲",
        "乙": "丙", "庚": "丙",
        "丙": "戊", "辛": "戊",
        "丁": "庚", "壬": "庚",
        "戊": "壬", "癸": "壬",
    }

    start_gan = shichen_start_map.get(day_tiangan, "甲")
    gan_list = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    zhi_list = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    start_index = gan_list.index(start_gan)
    gan_index = (start_index + shichen_num - 1) % 10
    zhi_index = (shichen_num - 1) % 12

    return f"{gan_list[gan_index]}{zhi_list[zhi_index]}"


def text_to_seed(text):
    """
    将文本转换为稳定数值种子。

    中文、英文、数字都可以参与计算。
    同一个文本会得到相同基础种子。
    """
    if not text:
        return 0

    return sum(ord(char) for char in text)


def normalize_mod(value, mod_base):
    """
    取余工具。

    八卦：除尽取 8
    动爻：除尽取 6
    """
    result = value % mod_base
    return mod_base if result == 0 else result


def collect_focus_seed(prompt_text="请静心凝神，按回车起卦..."):
    """
    采集用户从看到提示到按下回车之间的停顿时间。

    这个停顿时间不是随机数，而是用户当下状态、心念、犹豫、
    外部干扰和反应节奏共同形成的结果。
    """

    print(prompt_text)

    start_time = time.perf_counter()
    input()
    end_time = time.perf_counter()

    focus_seconds = end_time - start_time

    # 毫秒级扰动
    focus_seed = int(focus_seconds * 1000)

    return {
        "focus_seconds": focus_seconds,
        "focus_seed": focus_seed,
    }


def get_moment_seed():
    """
    获取起卦瞬间的时间扰动。

    使用分钟、秒、毫秒，避免同一时辰内结果完全固定。
    """

    now = datetime.datetime.now()

    moment_seed = (
        now.minute * 60 * 1000
        + now.second * 1000
        + now.microsecond // 1000
    )

    return {
        "now": now,
        "moment_seed": moment_seed,
    }


def build_qi_seed(question="", mode="default", extra_text="", focus_seed=0):
    """
    构建综合气机种子。

    参数：
        question: 用户问题
        mode: 起卦模式，例如 full、quick、item、decision、daily
        extra_text: 额外文本，例如物品名、选项名
        focus_seed: 用户停顿时间生成的人念扰动

    返回：
        int 综合扰动种子
    """

    moment_info = get_moment_seed()

    question_seed = text_to_seed(question)
    mode_seed = text_to_seed(mode)
    extra_seed = text_to_seed(extra_text)

    qi_seed = (
        moment_info["moment_seed"]
        + question_seed
        + mode_seed
        + extra_seed
        + focus_seed
    )

    return qi_seed



