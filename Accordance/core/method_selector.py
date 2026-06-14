# -*- coding: utf-8 -*-
"""起卦法选择器。

根据问题文本和场景特征推荐更合适的术数入口。选择器只做方法建议，
不替代用户判断，也不直接参与起卦计算。
"""


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
}


NEGATIVE_HINTS = {
    "full": "若只是眼前小事，六爻会显得过重。",
    "quick": "若牵涉合同、健康、法律、长期结果，三爻信息量不足。",
    "name": "若问题不是名号本身，姓名起卦容易偏离事体。",
    "daily": "若已有明确问题，应改用对应起卦法。",
    "item": "若物品可能已离身或范围很大，寻物专项只能先给搜索启示，宜转六爻详占。",
    "decision": "若选项不止两个或问题本身尚未厘清，应先整理为明确方案。",
}


def _contains_any(text, keywords):
    return [word for word in keywords if word and word.lower() in text]


def _score_method(text, method_key):
    profile = METHOD_PROFILES[method_key]
    hits = _contains_any(text, profile["keywords"])
    score = len(hits) * 3

    if method_key == "decision" and ("还是" in text or "或者" in text or "选" in text):
        score += 4
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

    return score, hits


def recommend_divination_methods(question):
    """按问题文本返回起卦法推荐列表。"""
    text = (question or "").strip()
    normalized = text.lower()
    ranked = []
    for key in METHOD_PROFILES:
        score, hits = _score_method(normalized, key)
        ranked.append({
            "key": key,
            "score": score,
            "hits": hits,
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
            if item["hits"]:
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
