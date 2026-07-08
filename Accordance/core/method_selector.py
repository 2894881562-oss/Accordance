# -*- coding: utf-8 -*-
"""起卦法选择器。

根据问题文本和场景特征推荐更合适的术数入口。选择器只做方法建议，
不替代用户判断，也不直接参与起卦计算。
"""

import re


METHOD_PROFILES = {
    "full": {
        "menu": "1",
        "name": "六爻详占",
        "fit": "重大、复杂、牵涉前因后果与多方关系的问题。",
        "basis": "六爻纳甲可看世应、用神、动变、月日、飞伏与六亲，适合实占细断。",
        "keywords": [
            "工作", "事业", "求职", "升职", "财", "投资", "合同", "官司", "法律",
            "婚姻", "感情", "疾病", "健康", "治疗", "搬家", "买房", "考试",
            "项目", "合作", "长期", "趋势", "结果", "前因后果", "重大",
        ],
    },
    "quick": {
        "menu": "2",
        "name": "三爻快占",
        "fit": "紧急、单点、短期、只需方向提示的问题。",
        "basis": "三爻取象轻快，宜看眼前一念与短期应对，不宜承载复杂断法。",
        "keywords": [
            "现在", "马上", "今天", "明天", "短期", "临时", "急", "要不要",
            "该不该", "能不能", "可不可以", "是否", "小事", "单点",
        ],
    },
    "name": {
        "menu": "3",
        "name": "姓名起卦",
        "fit": "人名、字号、品牌名、改名、命名相关的问题。",
        "basis": "姓名起卦以名号笔画立象，适合审名号与人事关系的象意。",
        "keywords": ["姓名", "名字", "改名", "起名", "笔画", "公司名", "品牌名", "店名", "艺名"],
    },
    "bazi": {
        "menu": "8",
        "name": "四柱八字",
        "fit": "已知公历出生日期和时辰，想看四柱、十神、日主强弱、阶段倾向的问题。",
        "basis": "八字以年、月、日、时四柱为结构，以日干为核心分析其余七字的生克比关系。",
        "keywords": [
            "八字", "四柱", "命理", "出生", "生日", "生辰", "时辰", "日主", "日干",
            "十神", "正印", "偏印", "食神", "伤官", "正官", "七杀", "正财", "偏财", "比肩", "劫财",
        ],
    },
    "qimen": {
        "menu": "9",
        "name": "奇门运筹",
        "fit": "已明确行动场景，想看方位、择时、谈判竞争布局与攻守节奏的问题。",
        "basis": "奇门以时间与空间起局，合参九宫、八门、九星、八神和三奇六仪，适合现实运筹而非改动格局。",
        "keywords": [
            "奇门", "遁甲", "八门", "九星", "三奇", "六仪", "方位", "方向", "择时", "时机",
            "运筹", "布局", "谈判", "竞争", "对峙", "克敌", "制胜", "攻守", "站位", "路线",
        ],
    },
    "daily": {
        "menu": "4",
        "name": "当日气运",
        "fit": "只想看今天整体行事基调，不针对单一事件。",
        "basis": "日卦以当日气机为主，同日稳定，适合行事参考。",
        "keywords": ["今日", "今天", "当天", "日运", "气运", "运势", "整体", "行事"],
    },
    "item": {
        "menu": "5",
        "name": "寻物专项占",
        "fit": "丢失、寻找物品，尤其是范围相对明确的寻物。",
        "basis": "寻物取八卦方位、物象、颜色与空间提示，先服务现实搜索路径。",
        "keywords": ["寻物", "找东西", "寻找", "找回", "丢", "丢失", "失物", "遗失", "落下", "不见"],
    },
    "decision": {
        "menu": "6",
        "name": "二选一决策",
        "fit": "两个明确选项之间取舍、比较。",
        "basis": "两案分别起象再比较体用、用神、风险，适合二择一。",
        "keywords": ["二选一", "选哪个", "哪一个", "哪个更", "选择", "取舍", "还是", "对比", "比较", "A", "B"],
    },
    "multi_decision": {
        "menu": "7",
        "name": "多选最优决策",
        "fit": "三个及以上明确选项之间做评分排序，并只展开最优方案详解的问题。",
        "basis": "多案分别起象评分，先给全部选项最终分，再仅对最优项展开卦象、用神、风险与结论，避免多卦信息过载。",
        "keywords": [
            "多选", "多个选项", "多个方案", "多方案", "多案", "三选一", "四选一", "五选一",
            "哪个最优", "哪一个最优", "最优解", "最适合", "排名", "排序", "优先级", "从中选一个",
            "多项选择", "多问题选择", "多项问题", "多种选择",
        ],
    },
}


NEGATIVE_HINTS = {
    "full": "若只是眼前小事，六爻会显得过重。",
    "quick": "若牵涉合同、健康、法律、长期结果，三爻信息量不足。",
    "name": "若问题不是名号本身，姓名起卦容易偏离事体。",
    "bazi": "若没有可靠出生日期与时辰，八字分析只能做粗略参考；具体决策仍需回到现实信息。",
    "qimen": "若要看完整前因后果或长期结果，仍宜用六爻详占；奇门只按当前时空给运筹参考，不实现风后奇门式改局。",
    "daily": "若已有明确问题，应改用对应起卦法。",
    "item": "若物品可能已离身或范围很大，寻物专项只能先给搜索启示，宜转六爻详占。",
    "decision": "若选项不止两个，宜改用多选最优决策；若问题本身尚未厘清，应先整理为明确方案。",
    "multi_decision": "若只有两个选项，二选一决策更精简；若选项尚未成形，应先整理为可比较的具体方案。",
}


HIGH_STAKES_TERMS = [
    "合同", "法律", "官司", "诉讼", "疾病", "健康", "治疗", "手术",
    "投资", "股票", "基金", "买房", "卖房", "离职", "跳槽", "婚姻",
    "长期", "重大", "风险", "前因后果", "项目", "合作",
]

ITEM_OBJECT_TERMS = ["东西", "物品", "钥匙", "手机", "证件", "钱包", "文件", "卡", "包"]
ITEM_ACTION_TERMS = ["寻物", "找东西", "寻找", "找回", "丢", "丢失", "失物", "遗失", "落下", "不见"]
NAME_TERMS = ["姓名", "名字", "改名", "起名", "笔画", "公司名", "品牌名", "店名", "艺名"]
BAZI_TERMS = ["八字", "四柱", "命理", "出生", "生日", "生辰", "时辰", "日主", "日干", "十神"]
QIMEN_TERMS = ["奇门", "遁甲", "八门", "九星", "三奇", "六仪", "方位", "择时", "运筹", "布局", "克敌", "制胜", "对峙", "站位"]
DAILY_TERMS = ["今日", "今天", "当天", "日运", "气运", "运势", "整体", "行事"]
QUICK_TERMS = ["现在", "马上", "今天", "明天", "短期", "临时", "急", "要不要", "该不该", "能不能", "可不可以", "是否"]
COMPLEX_TERMS = ["长期", "重大", "复杂", "前因后果", "多方", "结果", "趋势", "风险"]
WEEKDAY_TERMS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日", "周天")
LIST_SEPARATORS = r"[、,，/／|｜;；\n]+"
MULTI_DECISION_TERMS = [
    "多选", "多个选项", "多个方案", "多方案", "多案", "三选一", "四选一", "五选一", "六选一",
    "七选一", "八选一", "九选一", "哪个最优", "哪一个最优", "哪个最好", "哪一个最好",
    "最优解", "最适合", "排名", "排序", "优先级", "从中选一个", "选一个最优",
    "几个方案", "几个选项", "这些方案", "这些选项", "这几个方案", "这几个选项",
    "多项选择", "多问题选择", "多项问题", "多种选择", "多个问题选择",
]


def _contains_any(text, keywords):
    return [word for word in keywords if word and word.lower() in text]


def _has_any(text, keywords):
    return any(word.lower() in text.lower() for word in keywords)


def _looks_like_two_options(text):
    if any(word in text for word in ["二选一", "选哪个", "哪一个", "哪个更", "取舍", "对比", "比较"]):
        return True
    if "还是" in text or "或者" in text:
        return True

    upper_text = text.upper()
    return bool(
        re.search(r"(?:^|[^A-Z])A(?:[^A-Z]|$).*(?:^|[^A-Z])B(?:[^A-Z]|$)", upper_text)
        or re.search(r"(?:^|[^A-Z])B(?:[^A-Z]|$).*(?:^|[^A-Z])A(?:[^A-Z]|$)", upper_text)
    )


def _looks_like_multi_options(text):
    if _has_any(text, MULTI_DECISION_TERMS):
        return True
    if "多" in text and any(word in text for word in ["选择", "取舍", "最优", "排序", "排名", "优先级"]):
        return True
    if sum(1 for term in WEEKDAY_TERMS if term in text) >= 3:
        return True
    if re.search(LIST_SEPARATORS, text):
        parts = [part.strip(" 　：:，,。.;；") for part in re.split(LIST_SEPARATORS, text)]
        options = [part for part in parts if part]
        if 3 <= len(options) <= 9 and all(len(option) <= 24 for option in options):
            return True
    if re.search(r"(?:[三四五六七八九]|[3-9])\s*选\s*(?:一|1)", text):
        return True
    if re.search(r"(?:[3-9]|[三四五六七八九])\s*(?:个|项|种)?\s*(?:方案|选项)", text):
        return True
    return False


def _build_route_context(text):
    """识别强场景，给选择器排序提供可审的加权依据。"""
    normalized = text.lower()
    boosts = {key: 0 for key in METHOD_PROFILES}
    labels = {key: [] for key in METHOD_PROFILES}

    item_hit = _has_any(normalized, ITEM_ACTION_TERMS) or (
        "找" in text and _has_any(normalized, ITEM_OBJECT_TERMS)
    )
    multi_decision_hit = _looks_like_multi_options(text)
    decision_hit = _looks_like_two_options(text) and not multi_decision_hit
    name_hit = _has_any(normalized, NAME_TERMS)
    bazi_hit = _has_any(normalized, BAZI_TERMS)
    qimen_hit = _has_any(normalized, QIMEN_TERMS)
    daily_hit = _has_any(normalized, DAILY_TERMS)
    high_stakes_hit = _has_any(normalized, HIGH_STAKES_TERMS)
    complex_hit = _has_any(normalized, COMPLEX_TERMS)
    quick_hit = _has_any(normalized, QUICK_TERMS) or len(text.strip()) <= 18

    if item_hit:
        boosts["item"] += 14
        boosts["daily"] -= 5
        boosts["quick"] -= 2
        labels["item"].append("寻物强场景")
        if "范围大" in text or "不确定" in text or "离身" in text:
            boosts["full"] += 4
            labels["full"].append("寻物范围不明需六爻补充")

    if decision_hit:
        boosts["decision"] += 13
        boosts["quick"] -= 1
        labels["decision"].append("二选一强场景")

    if multi_decision_hit:
        boosts["multi_decision"] += 16
        boosts["decision"] -= 6
        boosts["quick"] -= 2
        labels["multi_decision"].append("多选最优强场景")

    if name_hit:
        boosts["name"] += 12
        boosts["full"] -= 1
        labels["name"].append("名号笔画强场景")

    if bazi_hit:
        boosts["bazi"] += 14
        boosts["name"] -= 3
        boosts["daily"] -= 3
        labels["bazi"].append("出生四柱强场景")

    if qimen_hit:
        boosts["qimen"] += 14
        boosts["daily"] -= 3
        boosts["quick"] -= 2
        labels["qimen"].append("奇门方位运筹强场景")
        if high_stakes_hit or complex_hit:
            boosts["full"] += 3
            labels["full"].append("奇门事项仍需六爻看前因后果")

    if daily_hit and not (item_hit or decision_hit or multi_decision_hit or name_hit or bazi_hit or qimen_hit or high_stakes_hit):
        boosts["daily"] += 10
        labels["daily"].append("当日整体基调")
    elif daily_hit:
        boosts["daily"] += 2

    if high_stakes_hit:
        boosts["full"] += 10
        boosts["quick"] -= 5
        boosts["daily"] -= 4
        labels["full"].append("高风险复杂事项")
    elif complex_hit:
        boosts["full"] += 7
        labels["full"].append("复杂事项")

    if quick_hit and not high_stakes_hit and not complex_hit and not item_hit and not decision_hit and not multi_decision_hit and not name_hit and not bazi_hit and not qimen_hit:
        boosts["quick"] += 6
        labels["quick"].append("短急单点")

    return {"boosts": boosts, "labels": labels}


def _score_method(text, method_key, route_context=None):
    profile = METHOD_PROFILES[method_key]
    hits = _contains_any(text, profile["keywords"])
    score = len(hits) * 3

    if method_key == "decision" and ("还是" in text or "或者" in text or "选" in text):
        score += 4
    if method_key == "multi_decision" and any(word in text for word in ["多选", "方案", "选项", "最优", "排名", "排序", "优先级"]):
        score += 5
    if method_key == "full" and any(word in text for word in ["长期", "重大", "复杂", "前因后果", "风险"]):
        score += 5
    if method_key == "quick" and len(text) <= 18:
        score += 2
    if method_key == "daily" and any(word in text for word in ["今天", "今日", "当天"]):
        score += 4
    if method_key == "item" and (
        any(word in text for word in ["丢", "丢失", "失物", "遗失", "落下", "不见", "找回", "寻物"])
        or ("找" in text and any(word in text for word in ["东西", "物品", "钥匙", "手机", "证件", "钱包"]))
    ):
        score += 5
    if method_key == "name" and any(word in text for word in ["名", "笔画"]):
        score += 5
    if method_key == "qimen" and any(word in text for word in ["奇门", "遁甲", "方位", "择时", "运筹", "布局", "站位"]):
        score += 5

    if route_context:
        score += route_context["boosts"].get(method_key, 0)

    return score, hits


def recommend_divination_methods(question):
    """按问题文本返回起卦法推荐列表。"""
    text = (question or "").strip()
    normalized = text.lower()
    route_context = _build_route_context(text) if text else None
    ranked = []
    for key in METHOD_PROFILES:
        score, hits = _score_method(normalized, key, route_context)
        ranked.append({
            "key": key,
            "score": score,
            "hits": hits,
            "rule_hits": route_context["labels"].get(key, []) if route_context else [],
            **METHOD_PROFILES[key],
            "caution": NEGATIVE_HINTS[key],
        })

    ranked.sort(key=lambda item: item["score"], reverse=True)

    if not text:
        ranked[0]["score"] = max(ranked[0]["score"], 1)
        ranked[0]["reason"] = "未输入具体问题，默认先用六爻详占承接完整问事。"
        return ranked

    if ranked[0]["score"] <= 0:
        # 泛问不明时，优先六爻详占；若用户只需快问，可自行转三爻。
        for item in ranked:
            if item["key"] == "full":
                item["score"] = 1
                item["reason"] = "未命中特定门类，六爻详占的信息承载更完整。"
        ranked.sort(key=lambda item: item["score"], reverse=True)

    for item in ranked:
        if "reason" not in item:
            rule_hits = item.get("rule_hits", [])
            if rule_hits and item["hits"]:
                item["reason"] = f"规则：{'、'.join(rule_hits)}；命中：{'、'.join(item['hits'][:5])}。{item['fit']}"
            elif rule_hits:
                item["reason"] = f"规则：{'、'.join(rule_hits)}。{item['fit']}"
            elif item["hits"]:
                item["reason"] = f"命中：{'、'.join(item['hits'][:5])}。{item['fit']}"
            else:
                item["reason"] = item["fit"]
    return ranked


def format_method_recommendation(question, limit=3):
    """格式化起卦法推荐文本。"""
    ranked = recommend_divination_methods(question)
    lines = ["起卦法建议："]
    for index, item in enumerate(ranked[:limit], 1):
        lines.append(
            f"{index}. 菜单{item['menu']} {item['name']}｜评分{item['score']}｜{item['reason']}"
        )
        lines.append(f"   依据：{item['basis']}")
        lines.append(f"   边界：{item['caution']}")
    return "\n".join(lines), ranked
