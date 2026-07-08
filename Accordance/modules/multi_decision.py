# -*- coding: utf-8 -*-
"""多选最优决策辅助模块。"""

from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi
from core.question_history import handle_duplicate_check, record_question
from core.question_precheck import build_question_profile, format_question_profile
from modules.decision_helper import _option_qi_gua, _option_score, _print_option
from core.interpretation import interpret_hexagram


OPTION_LABELS = list("ABCDEFGHI")


def _sep(char="─", width=62):
    print(char * width)


def _ask_option_count():
    while True:
        raw = input("请输入选项数量（3-9）：").strip()
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
    for index in range(count):
        label = OPTION_LABELS[index]
        option = input(f"请输入选项{label}：").strip()
        options.append(option or f"选项{label}")
    return options


def _multi_history_question(question, options):
    option_text = "｜".join(f"{OPTION_LABELS[index]}：{option}" for index, option in enumerate(options))
    return f"多选最优：{question}｜{option_text}"


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


def _print_best_summary(scored):
    best = scored[0]
    runner_up = scored[1] if len(scored) > 1 else None
    print()
    _sep("═")
    print("  最优解详细说明")
    _sep("═")
    _print_option(f"最优选项{best['label']}", best["option"], best["result"])

    print()
    if runner_up:
        gap = best["score"] - runner_up["score"]
        if gap <= 8:
            print(
                f"  【结论】当前评分最高的是{best['label']}「{best['option']}」，"
                f"但仅高出第二名{gap}分，属于小幅领先。建议先按现实成本、风险和资源再复核一遍。"
            )
        else:
            print(
                f"  【结论】建议优先选择{best['label']}「{best['option']}」。"
                f"它比第二名高出{gap}分，当前卦象承载力相对更强。"
            )
    else:
        print(f"  【结论】建议优先选择{best['label']}「{best['option']}」。")
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

    question = (prefilled_question or "").strip()
    if not question:
        question = input("请输入你要决策的问题：").strip() or "未命名问题"
    count = _ask_option_count()
    options = _ask_options(count)

    history_question = _multi_history_question(question, options)
    should_proceed, _ = handle_duplicate_check(
        history_question,
        "多选最优决策",
        allow_rephrase=False,
        match_mode="exact",
    )
    if not should_proceed:
        return

    question_profile = build_question_profile(question, current_method_key="multi_decision")
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
