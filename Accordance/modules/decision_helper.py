# -*- coding: utf-8 -*-
"""
二选一决策辅助模块

适用场景：
1. 两个选项之间难以取舍；
2. 例如：去/不去、买/不买、选A/选B、推进/暂缓；
3. 本模块只作为传统文化研究与决策参考，不替代现实分析。

当前版本：
1. 使用"问题文字 + 选项文字 + 农历时间"分别起卦；
2. 整合体用生克评分、六亲格局、互卦趋势对比；
3. 避免高分卦被机械判断为完全有利。
"""

from config.bagua_data import BAGUA_DATA
from core.divination import get_lunar_time, identify_tiyong, calculate_hugua
from core.interpretation import interpret_hexagram
from core.qi_context import get_accurate_day_ganzhi
from core.question_history import handle_duplicate_check, record_question


def print_separator():
    print("=" * 70)


def normalize_mod(value, mod_base):
    result = value % mod_base
    return mod_base if result == 0 else result


def text_to_seed(text):
    if not text:
        return 0
    return sum(ord(char) for char in text)


def option_text_qi_gua(question, option_text):
    """二选一专用：选项文字起卦法。"""
    lunar_info = get_lunar_time()

    question_seed = text_to_seed(question)
    option_seed = text_to_seed(option_text)

    month_num = lunar_info["month"]
    day_num = lunar_info["day"]
    shi_chen_num = lunar_info["shi_chen"]

    upper_seed = question_seed + month_num + day_num
    lower_seed = option_seed + day_num + shi_chen_num
    dong_yao_seed = question_seed + option_seed + month_num + day_num + shi_chen_num

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
        "question": question,
        "mode": "decision",
        "extra_text": option_text,
    }


def calculate_option_score(interpret_result):
    """
    根据解卦结果计算辅助评分。

    增强版：加入体用生克权重。
    """
    score = interpret_result["ji_xiong_score"] * 20

    sheng_ke_text = interpret_result["sheng_ke_analysis"]
    wang_shuai_text = interpret_result["wang_shuai_analysis"]

    # 体用生克评分
    tiyong_info = interpret_result.get("tiyong_info", {})
    tiyong_relation = tiyong_info.get("relation", "")
    if "用生体" in tiyong_relation:
        score += 20
    elif "比和" in tiyong_relation:
        score += 10
    elif "体克用" in tiyong_relation:
        score += 5
    elif "体生用" in tiyong_relation:
        score -= 10
    elif "用克体" in tiyong_relation:
        score -= 20

    # 纳甲用神与动变回头生克评分
    yongshen_system = interpret_result.get("yongshen_system", {})
    score += int(float(yongshen_system.get("score", 0)) * 3)
    bian_relation = interpret_result.get("bian_line_relation", {})
    score += int(float(bian_relation.get("score", 0)) * 4)

    # 生扶加分
    if "生扶" in sheng_ke_text:
        score += 10

    # 克制扣分
    if "克制" in sheng_ke_text or "反噬" in sheng_ke_text:
        score -= 10

    # 旺相加分
    score += wang_shuai_text.count("旺") * 8
    score += wang_shuai_text.count("相") * 5

    # 休囚死扣分
    score -= wang_shuai_text.count("休") * 3
    score -= wang_shuai_text.count("囚") * 6
    score -= wang_shuai_text.count("死") * 10

    # 风险关键词扣分
    risk_words = get_risk_keywords(interpret_result)
    for word in risk_words:
        if _risk_severity(word) >= 2:
            score -= 10
        else:
            score -= 5

    if score < 0:
        score = 0
    elif score > 120:
        score = 120

    return score


RISK_SEMANTIC_RULES = {
    "结构性阻碍": {
        "severity": 1,
        "patterns": ["阻", "困", "难", "艰", "险", "滞", "闭", "蹇", "坎"],
    },
    "冲突对立": {
        "severity": 1,
        "patterns": ["冲", "争", "讼", "斗", "敌", "裂", "违", "悖", "相左"],
    },
    "损耗破败": {
        "severity": 2,
        "patterns": ["损", "败", "破", "失", "耗", "衰", "死", "绝", "崩"],
    },
    "混乱失序": {
        "severity": 1,
        "patterns": ["乱", "迷", "惑", "昧", "蒙", "未济", "过", "失律"],
    },
    "健康灾厄": {
        "severity": 2,
        "patterns": ["病", "灾", "祸", "血", "伤", "鬼", "虎", "危"],
    },
}


def _risk_severity(word):
    max_severity = 0
    for rule in RISK_SEMANTIC_RULES.values():
        if any(pattern in word for pattern in rule["patterns"]):
            max_severity = max(max_severity, rule["severity"])
    return max_severity


def get_risk_keywords(interpret_result):
    """从卦象核心意象与解读文本中动态抽取风险语义。"""
    source_terms = list(interpret_result.get("core_meaning", []))
    source_terms.append(interpret_result.get("gua_ci", ""))
    source_terms.append(interpret_result.get("sheng_ke_analysis", ""))
    source_terms.append(interpret_result.get("dizhi_relation_summary", ""))
    source_terms.append(interpret_result.get("bian_line_relation_tip", ""))
    source_terms.append(interpret_result.get("yongshen_system_summary", ""))
    source_terms.append(interpret_result.get("decision_suggest", ""))

    matched = []
    for term in source_terms:
        if not term:
            continue
        for rule_name, rule in RISK_SEMANTIC_RULES.items():
            if any(pattern in term for pattern in rule["patterns"]):
                risk_text = f"{term}（{rule_name}）"
                if risk_text not in matched:
                    matched.append(risk_text)
                break

    return matched


def generate_risk_tip(interpret_result):
    risk_words = get_risk_keywords(interpret_result)
    if not risk_words:
        return "未发现明显风险关键词，但仍需结合现实条件判断。"
    if len(risk_words) <= 3:
        risk_text = "、".join(risk_words)
    else:
        risk_text = "、".join(risk_words[:3]) + "等"
    return (
        f"检测到风险象意：{risk_text}。"
        "该选项并非不能选择，但执行时应避免冲动、过度乐观或忽略现实阻碍。"
    )


def print_option_result(option_label, option_name, result):
    """打印单个选项的解读结果"""
    score = result.get("_score", 0)
    tiyong_info = result.get("tiyong_info", {})

    print_separator()
    print(f"【{option_label}：{option_name}】")
    print(f"卦名：{result['gua_name']}")
    print(f"卦辞：{result['gua_ci']}")
    print(f"吉凶等级：{result['ji_xiong']}")
    print(f"辅助评分：{score}/120")
    print(f"核心意象：{'、'.join(result['core_meaning'])}")

    print()
    print("【体用生克】")
    print(result['tiyong_tip'])

    print()
    print("【卦象解读】")
    print(result["qian_yin_hou_guo"])
    print(result["sheng_ke_analysis"])
    print(result["wang_shuai_analysis"])
    print(result["dong_yao_tip"])

    # 互卦趋势
    if result.get("hu_gua_tip"):
        print()
        print("【互卦趋势】")
        print(result["hu_gua_tip"])
        print(result["hu_cuo_zong_tip"])

    print()
    print("【空破刑冲与六神制化】")
    print(result["line_strength_summary"])
    print(result["bian_line_relation_tip"])
    print(result["yongshen_system_summary"])
    print(result["dizhi_relation_summary"])
    print(result["liushen_zhihua_summary"])

    print()
    print(f"【选项建议】：{result['decision_suggest']}")
    print(f"【风险提醒】：{generate_risk_tip(result)}")


def compare_options(option_a, score_a, result_a, option_b, score_b, result_b):
    """比较两个选项并生成结论"""
    score_gap = abs(score_a - score_b)
    risk_a = get_risk_keywords(result_a)
    risk_b = get_risk_keywords(result_b)

    print_separator()
    print("【二选一综合对比】")
    print(f"A：{option_a} —— {result_a['gua_name']}，{result_a['ji_xiong']}，评分 {score_a}/120，风险词 {len(risk_a)} 个")
    print(f"B：{option_b} —— {result_b['gua_name']}，{result_b['ji_xiong']}，评分 {score_b}/120，风险词 {len(risk_b)} 个")

    # 体用对比
    tiyong_a = result_a.get("tiyong_info", {})
    tiyong_b = result_b.get("tiyong_info", {})
    if tiyong_a and tiyong_b:
        print()
        print(f"A 体用关系：{tiyong_a.get('relation', '未知')}")
        print(f"B 体用关系：{tiyong_b.get('relation', '未知')}")

    print_separator()
    print("【倾向判断】")

    if score_gap <= 8:
        print("两个选项评分接近，卦象差距不明显。")
        print("建议不要只按卦象判断，应重点回到现实条件：成本、风险、时间、资源、长期收益。")
        if result_a["ji_xiong_score"] > result_b["ji_xiong_score"]:
            print(f"若必须选择，A「{option_a}」的吉凶等级略占优，可作为轻微倾向。")
        elif result_b["ji_xiong_score"] > result_a["ji_xiong_score"]:
            print(f"若必须选择，B「{option_b}」的吉凶等级略占优，可作为轻微倾向。")
        else:
            print("两者吉凶等级也接近，建议暂缓决定或补充更多现实信息。")
    elif score_a > score_b:
        print(f"当前更倾向选择：A「{option_a}」")
        print("原因：A 的综合评分更高（含体用生克权重），卦象基调、五行状态或推进条件相对更有利。")
        if risk_a:
            print("但 A 存在一定风险象意，不宜只看分数，需要结合现实条件谨慎执行。")
        if "克制" in result_a["sheng_ke_analysis"]:
            print("A 仍存在克制关系，选择 A 时不宜激进，应先处理阻碍。")
    else:
        print(f"当前更倾向选择：B「{option_b}」")
        print("原因：B 的综合评分更高（含体用生克权重），卦象基调、五行状态或推进条件相对更有利。")
        if risk_b:
            print("但 B 存在一定风险象意，不宜只看分数，需要结合现实条件谨慎执行。")
        if "克制" in result_b["sheng_ke_analysis"]:
            print("B 仍存在克制关系，选择 B 时不宜激进，应先处理阻碍。")

    print_separator()
    print("【现实决策提醒】")
    print("1. 卦象只提供象征化参考，不应替代现实分析。")
    print("2. 若涉及金钱、合同、考试、健康、法律等重要事项，应以事实、数据和专业意见为准。")
    print("3. 如果两个选项评分接近，说明当前更适合补充信息，而不是急于决断。")
    print("4. 体用生克出自梅花易数体系，六亲格局出自纳甲筮法，综合参考更有意义。")
    print_separator()


def run_decision_helper():
    """运行二选一决策辅助流程"""
    print_separator()
    print("【二选一决策辅助】")
    print("说明：本功能适合两个选项之间的辅助判断。")
    print("整合梅花易数体用生克 + 互卦趋势 + 风险分析。")
    print("本结果仅作传统文化研究与决策参考，不替代现实判断。")
    print_separator()

    question = input("请输入你要决策的问题：").strip()
    option_a = input("请输入选项A：").strip()
    option_b = input("请输入选项B：").strip()

    if not question:
        question = "未命名问题"

    should_proceed, question = handle_duplicate_check(question, "二选一决策")
    if not should_proceed:
        return

    if not option_a:
        option_a = "选项A"
    if not option_b:
        option_b = "选项B"

    print_separator()
    print(f"当前问题：{question}")
    print(f"A：{option_a}")
    print(f"B：{option_b}")
    print(f"日干支：{get_accurate_day_ganzhi()}")

    print('\n系统将使用"问题文字 + 选项文字 + 农历时间"的方式分别起卦。')
    print("这样可以避免 A/B 在同一时辰内得到完全相同的时间卦。")
    input("确认后按回车开始分析...")

    # 分别为 A、B 使用选项文字起卦
    hexagram_a = option_text_qi_gua(question, option_a)
    result_a = interpret_hexagram(hexagram_a)
    score_a = calculate_option_score(result_a)
    result_a["_score"] = score_a

    hexagram_b = option_text_qi_gua(question, option_b)
    result_b = interpret_hexagram(hexagram_b)
    score_b = calculate_option_score(result_b)
    result_b["_score"] = score_b

    record_question(
        question, "二选一决策",
        f"A「{option_a}」→ {result_a['gua_name']}（{result_a['ji_xiong']}），"
        f"B「{option_b}」→ {result_b['gua_name']}（{result_b['ji_xiong']}）"
    )

    print_option_result("选项A", option_a, result_a)
    print_option_result("选项B", option_b, result_b)

    compare_options(option_a, score_a, result_a, option_b, score_b, result_b)
