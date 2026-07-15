# -*- coding: utf-8 -*-
"""多选最优决策辅助模块。"""

import re

from core.cli_input import ask_text
from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi
from core.question_history import handle_duplicate_check, record_question
from core.question_precheck import build_question_profile, format_question_profile
from modules.decision_helper import _option_qi_gua, _option_score, _print_option
from core.interpretation import interpret_hexagram


OPTION_LABELS = list("ABCDEFGHI")
WEEKDAY_TERMS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日", "周天")
LIST_SEPARATORS = r"[、,，/／|｜;；\n]+"
QUESTION_HINTS = ("哪个", "哪一个", "哪天", "如何", "怎么", "是否", "要不要", "适合", "最优", "选择", "帮我")
WEEKDAY_PATTERN = re.compile("|".join(WEEKDAY_TERMS))


def _sep(char="─", width=62):
    print(char * width)


def _ask_option_count():
    while True:
        raw = input("请输入选项数量（3-9，0返回主菜单）：").strip()
        if raw in {"0", "q", "Q", "返回"}:
            return None
        try:
            count = int(raw)
        except ValueError:
            print("输入无效，请输入 3 到 9 之间的整数。")
            continue
        if count < 3:
            print("多选最优至少需要 3 个选项；两个选项请使用菜单6「二选一决策」。")
            continue
        if count > len(OPTION_LABELS):
            print(f"当前最多支持 {len(OPTION_LABELS)} 个选项。")
            continue
        return count


def _ask_options(count):
    options = []
    option_keys = set()
    for index in range(count):
        label = OPTION_LABELS[index]
        while True:
            option = ask_text(f"请输入选项{label}：", f"选项 {label}", 120)
            option_key = option.casefold()
            if option_key in option_keys:
                print(f"选项「{option}」已存在，请输入一个不同的选项。")
                continue
            options.append(option)
            option_keys.add(option_key)
            break
    return options


def _clean_detected_option(text):
    option = text.strip()
    option = re.sub(r"^(?:选项)?[A-Ia-i][\.、:：\)]\s*", "", option)
    option = re.sub(r"^方案[一二三四五六七八九十\d]+[\.、:：\)]?\s*", "", option)
    return option.strip(" 　：:，,。.;；")


def _extract_weekday_options(text):
    options = []
    for match in WEEKDAY_PATTERN.finditer(text):
        term = match.group(0)
        if term not in options:
            options.append(term)
    return options if 3 <= len(options) <= len(OPTION_LABELS) else []


def _extract_options_from_question(question):
    """从“周一、周二、周三”这类问题文本中识别已列出的选项。"""
    text = (question or "").strip()
    if not text:
        return []

    weekday_options = _extract_weekday_options(text)
    if weekday_options:
        return weekday_options

    if not re.search(LIST_SEPARATORS, text):
        return []

    parts = [_clean_detected_option(part) for part in re.split(LIST_SEPARATORS, text)]
    options = []
    option_keys = set()
    for part in parts:
        part_key = part.casefold()
        if not part or part_key in option_keys:
            continue
        if any(hint in part for hint in QUESTION_HINTS):
            return []
        if len(part) > 24:
            return []
        options.append(part)
        option_keys.add(part_key)

    return options if 3 <= len(options) <= len(OPTION_LABELS) else []


def parse_multi_options_text(text):
    """解析 Web/API 提交的多选文本，每行或常见分隔符代表一个选项。"""
    parts = [_clean_detected_option(part) for part in re.split(LIST_SEPARATORS, (text or "").strip())]
    options = []
    option_keys = set()
    for option in parts:
        if not option:
            continue
        if len(option) > 120:
            raise ValueError("每个选项最多 120 个字符")
        option_key = option.casefold()
        if option_key in option_keys:
            raise ValueError(f"选项「{option}」重复，请保留唯一选项")
        options.append(option)
        option_keys.add(option_key)

    if len(options) < 3:
        raise ValueError("多选最优至少需要 3 个选项；两个选项请使用二选一决策")
    if len(options) > len(OPTION_LABELS):
        raise ValueError(f"多选最优当前最多支持 {len(OPTION_LABELS)} 个选项")
    return options


def _confirm_detected_options(question):
    options = _extract_options_from_question(question)
    if not options:
        return []

    print()
    print(f"检测到你已在问题中列出 {len(options)} 个选项：")
    for index, option in enumerate(options):
        print(f"  {OPTION_LABELS[index]}：{option}")
    choice = input("是否直接使用这些选项？(Y/n)：").strip().lower()
    if choice in {"", "y", "yes"}:
        return options
    return []


def _multi_history_question(question, options):
    option_text = "｜".join(f"{OPTION_LABELS[index]}：{option}" for index, option in enumerate(options))
    return f"多选最优：{question}｜{option_text}"


def _profile_question(question, options):
    option_text = "、".join(options)
    return f"多选最优取舍：从{option_text}中选择最合适的一项。原问：{question}"


def _score_options(question, options, focus_seed):
    scored = []
    for index, option in enumerate(options):
        qi_gua = _option_qi_gua(question, option, focus_seed)
        qi_gua["mode"] = "multi_decision"
        result = interpret_hexagram(qi_gua)
        score = _option_score(result)
        result["_score"] = score
        scored.append({
            "index": index,
            "label": OPTION_LABELS[index],
            "option": option,
            "score": score,
            "result": result,
        })
    scored.sort(key=lambda item: (-item["score"], item["index"]))
    return scored


def _print_scoreboard(scored):
    print()
    _sep("═")
    print("  多选最终得分")
    _sep("═")
    for rank, item in enumerate(scored, 1):
        print(f"  {rank}. {item['label']}「{item['option']}」：{item['score']}/120")


def _plain_multi_conclusion(scored):
    """返回多选结果的一句结论，供 CLI 与 Web 共用。"""
    best = scored[0]
    runner_up = scored[1] if len(scored) > 1 else None
    if not runner_up:
        return f"建议优先选择{best['label']}「{best['option']}」。"

    gap = best["score"] - runner_up["score"]
    if gap <= 8:
        return (
            f"当前评分最高的是{best['label']}「{best['option']}」，"
            f"但仅高出第二名{gap}分，属于小幅领先。建议先按现实成本、风险和资源再复核一遍。"
        )
    return (
        f"建议优先选择{best['label']}「{best['option']}」。"
        f"它比第二名高出{gap}分，当前卦象承载力相对更强。"
    )


def _print_best_summary(scored):
    best = scored[0]
    print()
    _sep("═")
    print("  最优解详细说明")
    _sep("═")
    _print_option(f"最优选项{best['label']}", best["option"], best["result"])

    print()
    print(f"  【结论】{_plain_multi_conclusion(scored)}")
    print("  提醒：多选评分只做传统文化参考，最终仍应以现实证据、成本、风险和可执行条件校验。")


def _record_summary(scored):
    best = scored[0]
    others = "；".join(f"{item['label']} {item['score']}" for item in scored[1:])
    if others:
        return f"最优{best['label']}「{best['option']}」{best['score']}分；其他：{others}"
    return f"最优{best['label']}「{best['option']}」{best['score']}分"


def run_multi_decision(prefilled_question=None):
    """运行多选最优决策辅助流程。"""
    print()
    _sep("═")
    print("  多选最优决策 · 多案评分 + 最优详解")
    _sep("═")

    question = ask_text(
        "请输入你要决策的问题：",
        "决策问题",
        200,
        initial=prefilled_question,
    )

    question_key = f"多选最优：{question}"
    should_proceed, _ = handle_duplicate_check(
        question_key,
        "多选最优决策",
        allow_rephrase=False,
        match_mode="prefix",
    )
    if not should_proceed:
        return

    options = _confirm_detected_options(question)
    if not options:
        count = _ask_option_count()
        if count is None:
            return
        options = _ask_options(count)

    history_question = _multi_history_question(question, options)

    question_profile = build_question_profile(_profile_question(question, options), current_method_key="multi_decision")
    print()
    print(format_question_profile(question_profile))

    print()
    print(f"  问题：{question}")
    for index, option in enumerate(options):
        print(f"  {OPTION_LABELS[index]}：{option}")
    print(f"  日干支：{get_accurate_day_ganzhi()}")
    focus_info = collect_focus_seed("请静心凝神，专注于多个选项的真实优先级。准备好后按回车开始分析...")
    print(f"  凝神停顿：{focus_info['focus_seconds']:.2f}秒")

    scored = _score_options(question, options, focus_info["focus_seed"])
    record_question(history_question, "多选最优决策", _record_summary(scored))

    _print_scoreboard(scored)
    _print_best_summary(scored)
    _sep("═")
    print()
