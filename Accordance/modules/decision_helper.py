# -*- coding: utf-8 -*-
"""
二选一决策辅助模块

适用场景：
1. 两个选项之间难以取舍；
2. 例如：去/不去、买/不买、选A/选B、推进/暂缓；
3. 本模块只作为传统文化研究与决策参考，不替代现实分析。

当前版本优化：
1. 使用“问题文字 + 选项文字 + 当前农历时间”的方式分别起卦；
2. 避免 A/B 在同一时辰内得到完全相同的时间卦；
3. 增加风险关键词扫描；
4. 避免高分卦被机械判断为完全有利；
5. 输出更理性、稳健的二选一建议。
"""

from config.bagua_data import BAGUA_DATA
from core.divination import get_lunar_time
from core.interpretation import interpret_hexagram


def print_separator():
    print("=" * 70)


def normalize_mod(value, mod_base):
    """
    取余工具：
    八卦除尽取8，动爻除尽取6。
    """
    result = value % mod_base
    return mod_base if result == 0 else result


def text_to_seed(text):
    """
    将文字转换为稳定数值种子。

    使用 ord() 获取每个字符的 Unicode 编码值。
    中文、英文、数字都可以参与计算。
    """
    if not text:
        return 0

    return sum(ord(char) for char in text)


def option_text_qi_gua(question, option_text):
    """
    二选一专用：选项文字起卦法。

    设计逻辑：
    1. 问题本身代表共同背景；
    2. 选项文字代表不同路径；
    3. 当前农历日、时辰代表当下时机；
    4. 三者结合生成上卦、下卦、动爻。

    返回结构与 time_qi_gua() 保持一致，
    因此可以直接交给 interpret_hexagram() 解卦。
    """

    lunar_info = get_lunar_time()

    question_seed = text_to_seed(question)
    option_seed = text_to_seed(option_text)

    month_num = lunar_info["month"]
    day_num = lunar_info["day"]
    shi_chen_num = lunar_info["shi_chen"]

    # 上卦：问题背景 + 农历月日
    upper_seed = question_seed + month_num + day_num

    # 下卦：选项内容 + 农历日 + 当前时辰
    lower_seed = option_seed + day_num + shi_chen_num

    # 动爻：问题、选项、时间综合
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
        "gua_full_name": f"{upper_gua['name']}{lower_gua['name']}{lower_gua['xiang']}"
    }


def calculate_option_score(interpret_result):
    """
    根据解卦结果计算辅助评分。

    注意：
    该评分不是绝对吉凶，只用于二选一时做相对比较。
    """

    score = interpret_result["ji_xiong_score"] * 20

    sheng_ke_text = interpret_result["sheng_ke_analysis"]
    wang_shuai_text = interpret_result["wang_shuai_analysis"]

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

    # 风险关键词扣分：普通风险词每个扣5分，严重风险词每个扣10分。
    # 这样“上上卦但风险象意密集”的选项不会被虚高评分。
    risk_words = get_risk_keywords(interpret_result)
    severe_risk_words = ["危险", "危机", "崩溃", "死亡", "损失", "决裂", "暴力", "邪道"]
    for word in risk_words:
        if word in severe_risk_words:
            score -= 10
        else:
            score -= 5

    # 限制评分范围
    if score < 0:
        score = 0
    elif score > 120:
        score = 120

    return score


def get_risk_keywords(interpret_result):
    """
    从核心意象与解卦文本中提取风险关键词。

    返回：
        命中的风险关键词列表
    """

    risk_keyword_pool = [
        "危险", "危机", "崩溃", "黑暗", "错误", "背叛",
        "冲突", "矛盾", "争执", "诉讼", "裁决", "对立",
        "阻碍", "阻力", "困难", "艰险", "难关", "险难",
        "受困", "妨碍", "苦恼", "抑压", "苦闷",
        "损失", "减少", "缺陷", "不完整", "受伤",
        "决裂", "决溃", "暴力", "私欲", "独裁",
        "混乱", "腐败", "多事", "多难",
        "停滞", "烦恼", "受限", "苦难", "挫折",
        "放弃", "退避", "逃跑", "隐遁",
        "不当", "反常", "悖礼", "邪道",
        "离异", "反目", "不和", "相左",
        "诱惑", "迷惑", "中毒", "病源",
        "消极", "过错", "过分", "失律"
    ]

    text_parts = []

    text_parts.extend(interpret_result.get("core_meaning", []))
    text_parts.append(interpret_result.get("sheng_ke_analysis", ""))
    text_parts.append(interpret_result.get("decision_suggest", ""))

    full_text = "、".join(text_parts)

    matched = []
    for word in risk_keyword_pool:
        if word in full_text and word not in matched:
            matched.append(word)

    return matched


def generate_risk_tip(interpret_result):
    """
    根据风险关键词生成风险提醒文本。
    """

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


def print_option_result(option_label, option_name, interpret_result, score):
    """打印单个选项的解读结果"""

    print_separator()
    print(f"【{option_label}：{option_name}】")
    print(f"卦名：{interpret_result['gua_name']}")
    print(f"卦辞：{interpret_result['gua_ci']}")
    print(f"吉凶等级：{interpret_result['ji_xiong']}")
    print(f"辅助评分：{score}/120")
    print(f"核心意象：{'、'.join(interpret_result['core_meaning'])}")

    print_separator()
    print("【卦象解读】")
    print(interpret_result["qian_yin_hou_guo"])
    print(interpret_result["sheng_ke_analysis"])
    print(interpret_result["wang_shuai_analysis"])
    print(interpret_result["dong_yao_tip"])

    print_separator()
    print(f"【选项建议】：{interpret_result['decision_suggest']}")
    print(f"【风险提醒】：{generate_risk_tip(interpret_result)}")


def compare_options(option_a, score_a, result_a, option_b, score_b, result_b):
    """比较两个选项并生成结论"""

    score_gap = abs(score_a - score_b)

    risk_a = get_risk_keywords(result_a)
    risk_b = get_risk_keywords(result_b)

    print_separator()
    print("【二选一综合对比】")
    print(f"A：{option_a} —— {result_a['gua_name']}，{result_a['ji_xiong']}，评分 {score_a}/120，风险词 {len(risk_a)} 个")
    print(f"B：{option_b} —— {result_b['gua_name']}，{result_b['ji_xiong']}，评分 {score_b}/120，风险词 {len(risk_b)} 个")

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
        print("原因：A 的综合评分更高，说明其卦象基调、五行状态或推进条件相对更有利。")

        if risk_a:
            print("但 A 存在一定风险象意，不宜只看分数，需要结合现实条件谨慎执行。")

        if "克制" in result_a["sheng_ke_analysis"]:
            print("A 仍存在克制关系，选择 A 时不宜激进，应先处理阻碍。")

    else:
        print(f"当前更倾向选择：B「{option_b}」")
        print("原因：B 的综合评分更高，说明其卦象基调、五行状态或推进条件相对更有利。")

        if risk_b:
            print("但 B 存在一定风险象意，不宜只看分数，需要结合现实条件谨慎执行。")

        if "克制" in result_b["sheng_ke_analysis"]:
            print("B 仍存在克制关系，选择 B 时不宜激进，应先处理阻碍。")

    print_separator()
    print("【现实决策提醒】")
    print("1. 卦象只提供象征化参考，不应替代现实分析。")
    print("2. 若涉及金钱、合同、考试、健康、法律等重要事项，应以事实、数据和专业意见为准。")
    print("3. 如果两个选项评分接近，说明当前更适合补充信息，而不是急于决断。")
    print("4. 如果推荐项风险词较多，应优先排查现实层面的成本、损失、冲突和后续责任。")
    print_separator()


def run_decision_helper():
    """运行二选一决策辅助流程"""

    print_separator()
    print("【二选一决策辅助】")
    print("说明：本功能适合两个选项之间的辅助判断。")
    print("例如：选A还是选B、去还是不去、买还是不买、推进还是暂缓。")
    print("本结果仅作传统文化研究与决策参考，不替代现实判断。")
    print_separator()

    question = input("请输入你要决策的问题：").strip()
    option_a = input("请输入选项A：").strip()
    option_b = input("请输入选项B：").strip()

    if not question:
        question = "未命名问题"

    if not option_a:
        option_a = "选项A"

    if not option_b:
        option_b = "选项B"

    print_separator()
    print(f"当前问题：{question}")
    print(f"A：{option_a}")
    print(f"B：{option_b}")

    print("\n系统将使用“问题文字 + 选项文字 + 当前农历时间”的方式分别起卦。")
    print("这样可以避免 A/B 在同一时辰内得到完全相同的时间卦。")
    input("确认后按回车开始分析...")

    # 分别为 A、B 使用选项文字起卦
    hexagram_a = option_text_qi_gua(question, option_a)
    result_a = interpret_hexagram(hexagram_a)
    score_a = calculate_option_score(result_a)

    hexagram_b = option_text_qi_gua(question, option_b)
    result_b = interpret_hexagram(hexagram_b)
    score_b = calculate_option_score(result_b)

    print_option_result("选项A", option_a, result_a, score_a)
    print_option_result("选项B", option_b, result_b, score_b)

    compare_options(option_a, score_a, result_a, option_b, score_b, result_b)



