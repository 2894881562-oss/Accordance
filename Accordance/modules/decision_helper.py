# -*- coding: utf-8 -*-
"""
二选一决策辅助模块
适合两个选项之间难以取舍的场景。
整合梅花易数体用生克 + 互卦趋势 + 纳甲用神分析。
"""

from core.divination import get_lunar_time
from core.interpretation import interpret_hexagram
from core.qi_context import get_accurate_day_ganzhi
from core.question_history import handle_duplicate_check, record_question
from config.bagua_data import BAGUA_DATA
from config.hexagram_data import HEXAGRAM_DATA
from config.wuxing_rules import WUXING_SHENG, WUXING_KE


def _sep(char="─", width=62):
    print(char * width)


def _normalize_mod(value, mod_base):
    result = value % mod_base
    return mod_base if result == 0 else result


def _text_to_seed(text):
    if not text:
        return 0
    return sum(ord(c) for c in text)


def _option_qi_gua(question, option_text):
    """选项文字起卦法。"""
    lunar_info = get_lunar_time()
    qs = _text_to_seed(question)
    os = _text_to_seed(option_text)
    m, d, sc = lunar_info["month"], lunar_info["day"], lunar_info["shi_chen"]

    upper_num = _normalize_mod(qs + m + d, 8)
    lower_num = _normalize_mod(os + d + sc, 8)
    dong_yao = _normalize_mod(qs + os + m + d + sc, 6)

    return {
        "upper_gua": BAGUA_DATA[upper_num], "lower_gua": BAGUA_DATA[lower_num],
        "upper_num": upper_num, "lower_num": lower_num, "dong_yao": dong_yao,
        "lunar_info": lunar_info, "question": question, "mode": "decision",
        "extra_text": option_text,
    }


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
    if r.get("daxiang"):
        print(f"  大象：{r['daxiang']}")
    print(f"  体用：{tiyong.get('relation', '')} — {tiyong.get('relation_desc', '')}")
    print(f"  五行：{r['sheng_ke_analysis']}")
    print(f"  旺衰：{r['wang_shuai_analysis']}")
    print(f"  动爻：{r['dong_yao_tip']}")
    print(f"  互卦：{r['hu_gua_tip']}")
    print(f"  动变：{r['bian_line_relation_tip']}")
    print(f"  用神：{r['yongshen_system_summary']}")
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


def run_decision_helper():
    """运行二选一决策辅助流程"""
    print()
    _sep("═")
    print("  二选一决策辅助 · 梅花体用 + 纳甲用神 + 风险分析")
    _sep("═")

    question = input("请输入你要决策的问题：").strip() or "未命名问题"
    option_a = input("请输入选项A：").strip() or "选项A"
    option_b = input("请输入选项B：").strip() or "选项B"

    should_proceed, question = handle_duplicate_check(question, "二选一决策")
    if not should_proceed:
        return

    print()
    print(f"  问题：{question}")
    print(f"  A：{option_a}")
    print(f"  B：{option_b}")
    print(f"  日干支：{get_accurate_day_ganzhi()}")
    input("确认后按回车开始分析...")

    r_a = interpret_hexagram(_option_qi_gua(question, option_a))
    score_a = _option_score(r_a)
    r_a["_score"] = score_a

    r_b = interpret_hexagram(_option_qi_gua(question, option_b))
    score_b = _option_score(r_b)
    r_b["_score"] = score_b

    record_question(
        question, "二选一决策",
        f"A「{option_a}」→ {r_a['gua_name']}（{r_a['ji_xiong']}），"
        f"B「{option_b}」→ {r_b['gua_name']}（{r_b['ji_xiong']}）"
    )

    _print_option("选项A", option_a, r_a)
    _print_option("选项B", option_b, r_b)
    _compare(option_a, score_a, r_a, option_b, score_b, r_b)
    _sep("═")
    print()
