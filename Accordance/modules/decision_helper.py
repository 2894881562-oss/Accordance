# -*- coding: utf-8 -*-
"""
二选一决策辅助模块
适合两个选项之间难以取舍的场景。
整合梅花易数体用生克 + 互卦趋势 + 纳甲用神分析。
"""

import re

from core.divination import get_lunar_time
from core.interpretation import interpret_hexagram
from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi
from core.question_precheck import build_question_profile, format_question_profile
from core.question_history import handle_duplicate_check, record_question
from config.bagua_data import BAGUA_DATA
from config.hexagram_data import HEXAGRAM_DATA
from config.wuxing_rules import WUXING_SHENG, WUXING_KE


DECISION_SPLIT_PATTERN = re.compile(r"(.+?)\s*(?:还是|或者|或)\s*(.+)")
LABELED_OPTIONS_PATTERN = re.compile(
    r"(?:^|[\s，,；;])A[\.、:：\)]?\s*([^，,；;\n]+).*?"
    r"(?:^|[\s，,；;])B[\.、:：\)]?\s*([^，,；;\n]+)",
    re.IGNORECASE,
)
LEADING_OPTION_HINTS = (
    "我应该选择", "我该选择", "应该选择", "该选择",
    "我应该选", "我该选", "应该选", "该选", "选择", "选",
)
TRAILING_OPTION_HINTS = (
    "哪个更适合", "哪一个更适合", "哪个更好", "哪一个更好",
    "哪个合适", "哪一个合适", "更适合", "更合适", "更好",
    "比较好", "合适吗", "好吗",
)


def _sep(char="─", width=62):
    print(char * width)


def _normalize_mod(value, mod_base):
    result = value % mod_base
    return mod_base if result == 0 else result


def _text_to_seed(text):
    if not text:
        return 0
    return sum(ord(c) for c in text)


def _clean_detected_option(text):
    option = (text or "").strip(" 　：:，,。.;；？?！!")
    option = re.sub(r"^(?:选项)?[ABab][\.、:：\)]\s*", "", option).strip()
    for hint in LEADING_OPTION_HINTS:
        if option.startswith(hint):
            option = option[len(hint):].strip()
            break
    for hint in TRAILING_OPTION_HINTS:
        if option.endswith(hint):
            option = option[:-len(hint)].strip()
            break
    return option.strip(" 　：:，,。.;；？?！!")


def _extract_options_from_question(question):
    """从“A方案还是B方案”这类问题文本中识别二选一选项。"""
    text = (question or "").strip()
    if not text:
        return None

    labeled = LABELED_OPTIONS_PATTERN.search(text)
    if labeled:
        option_a = _clean_detected_option(labeled.group(1))
        option_b = _clean_detected_option(labeled.group(2))
        if option_a and option_b and option_a != option_b:
            return option_a, option_b

    split = DECISION_SPLIT_PATTERN.search(text)
    if not split:
        return None

    option_a = _clean_detected_option(split.group(1))
    option_b = _clean_detected_option(split.group(2))
    if not option_a or not option_b or option_a == option_b:
        return None
    if len(option_a) > 24 or len(option_b) > 24:
        return None
    return option_a, option_b


def _confirm_detected_options(question):
    options = _extract_options_from_question(question)
    if not options:
        return None

    option_a, option_b = options
    print()
    print("检测到你已在问题中列出两个选项：")
    print(f"  A：{option_a}")
    print(f"  B：{option_b}")
    choice = input("是否直接使用这些选项？(Y/n)：").strip().lower()
    if choice in {"", "y", "yes"}:
        return option_a, option_b
    return None


def _ask_option(label, existing=None):
    existing = set(existing or [])
    while True:
        option = input(f"请输入选项{label}：").strip() or f"选项{label}"
        if option in existing:
            print(f"选项「{option}」已存在，请输入一个不同的选项。")
            continue
        return option


def _option_qi_gua(question, option_text, focus_seed=0):
    """选项文字起卦法。"""
    lunar_info = get_lunar_time()
    qs = _text_to_seed(question)
    os = _text_to_seed(option_text)
    m, d, sc = lunar_info["month"], lunar_info["day"], lunar_info["shi_chen"]

    upper_num = _normalize_mod(qs + m + d + focus_seed, 8)
    lower_num = _normalize_mod(os + d + sc + focus_seed // 2, 8)
    dong_yao = _normalize_mod(qs + os + m + d + sc + focus_seed // 3, 6)

    return {
        "upper_gua": BAGUA_DATA[upper_num], "lower_gua": BAGUA_DATA[lower_num],
        "upper_num": upper_num, "lower_num": lower_num, "dong_yao": dong_yao,
        "lunar_info": lunar_info, "question": question, "mode": "decision",
        "extra_text": option_text, "focus_seed": focus_seed,
    }


def _decision_history_question(question, option_a, option_b):
    return f"二选一：{question}｜A：{option_a}｜B：{option_b}"


def _option_score(r):
    """计算选项综合评分。"""
    score = r["ji_xiong_score"] * 15
    tiyong = r.get("tiyong_info", {})
    tr = tiyong.get("relation", "")
    if "用生体" in tr:
        score += 20
    elif "比和" in tr:
        score += 10
    elif "体克用" in tr:
        score += 5
    elif "体生用" in tr:
        score -= 10
    elif "用克体" in tr:
        score -= 20

    ys = r.get("yongshen_system", {})
    score += int(float(ys.get("score", 0)) * 3)
    br = r.get("bian_line_relation", {})
    score += int(float(br.get("score", 0)) * 4)

    sk = r.get("sheng_ke_analysis", "")
    if "生扶" in sk:
        score += 8
    if "克制" in sk or "反噬" in sk:
        score -= 8

    ws = r.get("wang_shuai_analysis", "")
    score += ws.count("旺") * 6 + ws.count("相") * 4
    score -= ws.count("休") * 2 + ws.count("囚") * 5 + ws.count("死") * 8

    risk = _risk_keywords(r)
    for w in risk:
        score -= 8 if _risk_severity(w) >= 2 else 4

    return max(0, min(120, score))


RISK_RULES = {
    "结构性阻碍": {"severity": 1, "patterns": ["阻", "困", "难", "艰", "险", "滞", "闭", "蹇", "坎"]},
    "冲突对立": {"severity": 1, "patterns": ["冲", "争", "讼", "斗", "敌", "裂", "违", "悖"]},
    "损耗破败": {"severity": 2, "patterns": ["损", "败", "破", "失", "耗", "衰", "死", "绝", "崩"]},
    "混乱失序": {"severity": 1, "patterns": ["乱", "迷", "惑", "昧", "蒙", "未济", "过"]},
    "健康灾厄": {"severity": 2, "patterns": ["病", "灾", "祸", "血", "伤", "鬼", "虎", "危"]},
}


def _risk_severity(word):
    for rule in RISK_RULES.values():
        if any(p in word for p in rule["patterns"]):
            return rule["severity"]
    return 0


def _risk_keywords(r):
    sources = list(r.get("core_meaning", [])) + [
        r.get("gua_ci", ""), r.get("sheng_ke_analysis", ""),
        r.get("dizhi_relation_summary", ""), r.get("bian_line_relation_tip", ""),
        r.get("yongshen_system_summary", ""), r.get("decision_suggest", ""),
    ]
    matched = []
    for term in sources:
        if not term:
            continue
        for rule_name, rule in RISK_RULES.items():
            if any(p in term for p in rule["patterns"]):
                risk_text = f"{term[:30]}…（{rule_name}）"
                if risk_text not in matched:
                    matched.append(risk_text)
                break
    return matched


def _risk_tip(r):
    rw = _risk_keywords(r)
    if not rw:
        return "未发现明显风险关键词"
    return f"检测到风险象意：{'、'.join(rw[:3])}"


def _plain_decision_conclusion(option_a, score_a, r_a, option_b, score_b, r_b):
    """生成二选一的短结论。"""
    gap = abs(score_a - score_b)
    if gap <= 8:
        return f"建议暂缓。A与B只差{gap}分，卦象差距不明显，先按成本、风险、时间和现实条件再筛一轮。"

    if score_a > score_b:
        label, option, winner_score, loser_score, winner_result = "A", option_a, score_a, score_b, r_a
    else:
        label, option, winner_score, loser_score, winner_result = "B", option_b, score_b, score_a, r_b

    risk_note = (
        f"但{label}也有风险，执行前要核对现实条件。"
        if _risk_keywords(winner_result)
        else "按现实条件确认后可优先推进。"
    )
    return f"倾向选{label}「{option}」。{label}高出{winner_score - loser_score}分，{risk_note}"


def _print_option(label, name, r):
    score = r.get("_score", 0)
    tiyong = r.get("tiyong_info", {})
    print()
    _sep("━")
    print(f"  {label}：{name}")
    print(f"  卦：【{r['gua_name']}】{r['ji_xiong']}  |  评分：{score}/120  |  "
          f"体用：{tiyong.get('relation', '')}")
    _sep("━")
    print(f"  卦辞：{r['gua_ci']}")
    print(f"  卦意：{'、'.join(r['core_meaning'][:3])}")
    print(f"  校准：{r['calibration_tip']}")
    if r.get("daxiang"):
        print(f"  大象：{r['daxiang']}")
    print(f"  体用：{tiyong.get('relation', '')} — {tiyong.get('relation_desc', '')}")
    print(f"  五行：{r['sheng_ke_analysis']}")
    print(f"  旺衰：{r['wang_shuai_analysis']}")
    print(f"  动爻：{r['dong_yao_tip']}")
    print(f"  互卦：{r['hu_gua_tip']}")
    print(f"  动变：{r['bian_line_relation_tip']}")
    print(f"  用神：{r['yongshen_system_summary']}")
    print(f"  依据：{r['source_trace']}")
    print(f"  校验：{r['reality_check']}")
    print(f"  风险：{_risk_tip(r)}")
    print(f"  ▶ {r['judgment_conclusion']}")


def _compare(option_a, score_a, r_a, option_b, score_b, r_b):
    gap = abs(score_a - score_b)
    risk_a = _risk_keywords(r_a)
    risk_b = _risk_keywords(r_b)

    print()
    _sep("═")
    print("  二选一综合对比")
    _sep("═")
    print(f"  A「{option_a}」→ {r_a['gua_name']}，{r_a['ji_xiong']}，评分 {score_a}，风险词 {len(risk_a)}个")
    print(f"  B「{option_b}」→ {r_b['gua_name']}，{r_b['ji_xiong']}，评分 {score_b}，风险词 {len(risk_b)}个")

    tiyong_a = r_a.get("tiyong_info", {})
    tiyong_b = r_b.get("tiyong_info", {})
    print(f"  A体用：{tiyong_a.get('relation', '未知')}  |  B体用：{tiyong_b.get('relation', '未知')}")
    print()

    if gap <= 8:
        print("  两选项评分接近，卦象差距不明显。")
        print("  建议回到现实条件：成本、风险、时间、资源、长期收益来决策。")
        if r_a["ji_xiong_score"] > r_b["ji_xiong_score"]:
            print(f"  若必须选择，A「{option_a}」吉凶等级略占优，可作为轻微倾向。")
        elif r_b["ji_xiong_score"] > r_a["ji_xiong_score"]:
            print(f"  若必须选择，B「{option_b}」吉凶等级略占优，可作为轻微倾向。")
        else:
            print("  两者吉凶等级也接近，建议暂缓决定或补充更多现实信息。")
    elif score_a > score_b:
        print(f"  倾向选择：A「{option_a}」")
        print(f"  原因：A综合评分更高，卦象基调、五行状态或推进条件相对更有利。")
        if risk_a:
            print(f"  但A存在风险象意，不宜只看分数，需结合现实条件谨慎执行。")
    else:
        print(f"  倾向选择：B「{option_b}」")
        print(f"  原因：B综合评分更高，卦象基调、五行状态或推进条件相对更有利。")
        if risk_b:
            print(f"  但B存在风险象意，不宜只看分数，需结合现实条件谨慎执行。")

    print()
    print("  提醒：卦象只为参考，金钱/合同/健康/法律等重要事项应以事实和专业意见为准。")
    # 人本提醒
    print(r_a.get("human_agency_reminder", ""))
    print(f"  【简短结论】{_plain_decision_conclusion(option_a, score_a, r_a, option_b, score_b, r_b)}")


def run_decision_helper(prefilled_question=None):
    """运行二选一决策辅助流程"""
    print()
    _sep("═")
    print("  二选一决策辅助 · 梅花体用 + 纳甲用神 + 风险分析")
    _sep("═")

    question = (prefilled_question or "").strip()
    if not question:
        question = input("请输入你要决策的问题：").strip() or "未命名问题"

    question_key = f"二选一：{question}"
    should_proceed, _ = handle_duplicate_check(
        question_key,
        "二选一决策",
        allow_rephrase=False,
        match_mode="prefix",
    )
    if not should_proceed:
        return

    detected_options = _confirm_detected_options(question)
    if detected_options:
        option_a, option_b = detected_options
    else:
        option_a = _ask_option("A")
        option_b = _ask_option("B", existing={option_a})

    history_question = _decision_history_question(question, option_a, option_b)

    question_profile = build_question_profile(question, current_method_key="decision")
    print()
    print(format_question_profile(question_profile))

    print()
    print(f"  问题：{question}")
    print(f"  A：{option_a}")
    print(f"  B：{option_b}")
    print(f"  日干支：{get_accurate_day_ganzhi()}")
    focus_info = collect_focus_seed("请静心凝神，专注于两个选项的真实取舍。准备好后按回车开始分析...")
    print(f"  凝神停顿：{focus_info['focus_seconds']:.2f}秒")

    r_a = interpret_hexagram(_option_qi_gua(question, option_a, focus_info["focus_seed"]))
    score_a = _option_score(r_a)
    r_a["_score"] = score_a

    r_b = interpret_hexagram(_option_qi_gua(question, option_b, focus_info["focus_seed"]))
    score_b = _option_score(r_b)
    r_b["_score"] = score_b

    record_question(
        history_question, "二选一决策",
        f"A「{option_a}」→ {r_a['gua_name']}（{r_a['ji_xiong']}），"
        f"B「{option_b}」→ {r_b['gua_name']}（{r_b['ji_xiong']}）"
    )

    _print_option("选项A", option_a, r_a)
    _print_option("选项B", option_b, r_b)
    _compare(option_a, score_a, r_a, option_b, score_b, r_b)
    _sep("═")
    print()
