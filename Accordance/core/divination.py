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

from config.bagua_data import BAGUA_DATA
from core.qi_context import build_qi_seed, normalize_mod


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
    current_jieqi = "按月份近似"

    try:
        from zhdate import ZhDate  # type: ignore

        zh_date = ZhDate.from_datetime(now)
        lunar_year = int(zh_date.lunar_year)
        lunar_month = int(zh_date.lunar_month)
        lunar_day = int(zh_date.lunar_day)
        lunar_obj: Optional[Any] = zh_date
        current_jieqi = "zhdate农历"

    except (ImportError, AttributeError, ValueError, TypeError):
        lunar_obj = None

    hour = now.hour

    # 十二时辰序号：
    # 子时为 1，丑时为 2，……，亥时为 12。
    shi_chen_num = (hour + 1) // 2

    if shi_chen_num == 0:
        shi_chen_num = 12
    elif shi_chen_num > 12:
        shi_chen_num = 1

    season = get_season_by_month(lunar_month)

    # 四季末：
    # 农历 3 / 6 / 9 / 12 月后半段土旺。
    if lunar_month in (3, 6, 9, 12) and lunar_day >= 18:
        season = "四季末"

    yueling_by_month: Dict[int, str] = {
        1: "寅",
        2: "卯",
        3: "辰",
        4: "巳",
        5: "午",
        6: "未",
        7: "申",
        8: "酉",
        9: "戌",
        10: "亥",
        11: "子",
        12: "丑",
    }

    yueling = yueling_by_month.get(lunar_month, "寅")
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

    当前内部爻序：
    upper_yao + lower_yao
    即上三爻 + 下三爻。

    为保持与原项目逻辑一致，使用：
    yao_index = 6 - dong_yao
    """
    if upper_num not in GUA_NUM_TO_YAO:
        raise ValueError(f"非法上卦编号：{upper_num}")

    if lower_num not in GUA_NUM_TO_YAO:
        raise ValueError(f"非法下卦编号：{lower_num}")

    if dong_yao < 1 or dong_yao > 6:
        raise ValueError(f"非法动爻编号：{dong_yao}")

    upper_yao = list(GUA_NUM_TO_YAO[upper_num])
    lower_yao = list(GUA_NUM_TO_YAO[lower_num])

    all_yao = upper_yao + lower_yao

    yao_index = 6 - dong_yao
    all_yao[yao_index] = 1 - all_yao[yao_index]

    bian_upper_yao: YaoTuple = (
        int(all_yao[0]),
        int(all_yao[1]),
        int(all_yao[2]),
    )

    bian_lower_yao: YaoTuple = (
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
    简易日干支。

    用于兼容旧接口。
    当前算法为简化推算，不作为严格万年历依据。
    """
    solar = lunar_info.get("solar")

    if not isinstance(solar, datetime.datetime):
        solar = datetime.datetime.now()

    base_date = datetime.datetime(1900, 1, 31)
    delta_days = (solar - base_date).days

    gan = GAN_ORDER[(delta_days + 6) % 10]
    zhi = DIZHI_ORDER[delta_days % 12]

    return f"{gan}{zhi}"


