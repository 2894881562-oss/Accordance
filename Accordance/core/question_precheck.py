# -*- coding: utf-8 -*-
"""起卦前问事校准。

先审所问，再定用神。这里做轻量提示，不改变起卦结果，
只帮助用户把问题问得更清楚、方法选得更贴切。
"""

from core.method_selector import recommend_divination_methods
from core.zhuanggua import infer_yongshen_from_question


METHOD_KEY_BY_LABEL = {
    "六爻详占": "full",
    "三爻快占": "quick",
    "姓名起卦": "name",
    "当日气运": "daily",
    "寻物专项占": "item",
    "二选一决策": "decision",
    "多选最优决策": "multi_decision",
    "四柱八字": "bazi",
    "奇门运筹": "qimen",
}


CATEGORY_CONTEXT_HINTS = {
    "财货经营": ["金额与投入上限", "合同/付款/交付节点", "止损线"],
    "官职压力": ["岗位/组织变化", "上级反馈", "竞争者或考核标准"],
    "文书长辈": ["材料清单", "截止日期", "审批/签章流程"],
    "疾病病象": ["症状持续时间", "检查结果", "医生意见"],
    "医药治疗": ["治疗方案", "用药或复诊时间", "现实症状变化"],
    "婚恋女占": ["双方关系状态", "真实沟通", "现实阻力"],
    "婚恋男占": ["双方关系状态", "真实沟通", "现实阻力"],
    "婚恋未分性别": ["求测者性别", "双方关系状态", "现实阻力"],
    "寻物失物": ["最后出现位置", "物品特征", "搜索范围是否已扩大"],
    "出行行人": ["出发/返回时间", "交通方式", "天气路况"],
    "子女解忧": ["对象年龄/身份", "现实症状或诉求", "当前处理方式"],
    "同辈竞争": ["双方权责", "利益分配", "沟通记录"],
}


def _detect_time_scope(question):
    text = question or ""
    if any(word in text for word in ["今天", "今日", "当天", "今晚", "现在", "马上"]):
        return "眼前/当日"
    if any(word in text for word in ["明天", "本周", "这周", "最近", "短期"]):
        return "短期"
    if any(word in text for word in ["本月", "这个月", "下个月", "三个月", "半年"]):
        return "中期"
    if any(word in text for word in ["今年", "长期", "以后", "未来", "发展", "趋势"]):
        return "长期/趋势"
    return "未明示"


def _quality_hints(question, category, method_key):
    text = (question or "").strip()
    hints = []
    if len(text) < 8:
        hints.append("问题较短，建议补明对象、所求结果和时间范围。")
    if "婚恋未分性别" == category:
        hints.append("婚恋占需说明男占/女占，否则妻财、官鬼取用会有偏差。")
    if method_key == "quick" and any(word in text for word in ["长期", "重大", "合同", "法律", "健康", "疾病"]):
        hints.append("此问牵涉较重，三爻只宜看眼前应对，完整判断建议改用六爻详占。")
    if method_key == "full" and any(word in text for word in ["马上", "现在", "今天要不要"]) and len(text) <= 18:
        hints.append("此问偏短急，若只求眼前方向，三爻快占更轻便。")
    if "还是" in text and method_key != "decision":
        hints.append("若实际是两个方案取舍，二选一决策更贴切。")
    if any(word in text for word in ["多个方案", "多个选项", "多选", "最优解", "排名", "排序"]) and method_key != "multi_decision":
        hints.append("若实际是三个及以上方案取舍，多选最优决策更贴切。")
    return hints


def build_question_profile(question, current_method_key="full"):
    """生成问事校准资料。"""
    inference = infer_yongshen_from_question(question)
    ranked_methods = recommend_divination_methods(question)
    top_method = ranked_methods[0]
    category = inference.get("category", "泛问")
    primary = inference.get("primary", "世爻")
    secondary = inference.get("secondary", "")
    time_scope = _detect_time_scope(question)
    quality_hints = _quality_hints(question, category, current_method_key)

    context_hints = CATEGORY_CONTEXT_HINTS.get(category, [])
    if not context_hints:
        context_hints = ["求测对象", "时间范围", "现实已发生的关键变化"]

    method_aligned = top_method["key"] == current_method_key
    return {
        "category": category,
        "primary_yongshen": primary,
        "secondary_yongshen": secondary,
        "reason": inference.get("reason", ""),
        "keywords": inference.get("keywords", []),
        "time_scope": time_scope,
        "context_hints": context_hints,
        "quality_hints": quality_hints,
        "current_method": current_method_key,
        "recommended_method": top_method,
        "method_aligned": method_aligned,
        "ranked_methods": ranked_methods[:3],
    }


def format_question_profile(profile):
    """格式化问事校准提示。"""
    secondary = profile.get("secondary_yongshen")
    yongshen_text = profile["primary_yongshen"]
    if secondary:
        yongshen_text += f"；兼看{secondary}"

    lines = [
        "  【问事校准】",
        f"  问类：{profile['category']}｜用神：{yongshen_text}｜时间尺度：{profile['time_scope']}",
        f"  取用依据：{profile['reason']}",
    ]

    method = profile["recommended_method"]
    if profile["method_aligned"]:
        lines.append(f"  起卦法：当前方法与问事匹配（{method['name']}）。")
    else:
        lines.append(
            f"  起卦法提醒：更推荐菜单{method['menu']}「{method['name']}」；"
            f"当前仍可继续，但应按其适用边界解读。"
        )

    if profile.get("context_hints"):
        lines.append(f"  实占补充：{ '、'.join(profile['context_hints'][:3]) }。")
    for hint in profile.get("quality_hints", [])[:2]:
        lines.append(f"  问法提醒：{hint}")
    return "\n".join(lines)
