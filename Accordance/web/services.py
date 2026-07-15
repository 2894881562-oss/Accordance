# -*- coding: utf-8 -*-
"""Web/API 可复用的非交互起卦服务。"""

import datetime
from typing import Any, Dict, List

from config.name_strokes import analyze_text_strokes
from core.bazi import analyze_bazi_birth
from core.divination import (
    daily_guidance_gua,
    dynamic_three_yao_quick_divination,
    dynamic_time_qi_gua,
    name_qi_gua,
    time_qi_gua,
)
from core.interpretation import interpret_hexagram, interpret_three_yao
from core.method_selector import format_method_recommendation
from core.question_precheck import build_question_profile, format_question_profile
from core.qimen import analyze_qimen, format_qimen_report
from core.qi_context import get_accurate_day_ganzhi
from modules.daily_fortune import _plain_daily_conclusion
from modules.bazi import _bazi_history_question, _bazi_history_summary
from modules.decision_helper import (
    _option_qi_gua,
    _option_score,
    _plain_decision_conclusion,
    _risk_tip,
)
from modules.item_search import _hint, _item_tips, _likelihood, _plain_item_conclusion
from modules.multi_decision import (
    _multi_history_question,
    _plain_multi_conclusion,
    _profile_question,
    _record_summary,
    _score_options,
    parse_multi_options_text,
)
from modules.name_divination import _name_history_prefix, _name_history_question
from modules.qimen import _qimen_history_question, _qimen_history_summary
from web.history_store import check_duplicate, record_question


FEATURES = {
    "full": {"name": "六爻详占", "label": "六爻详占", "method_key": "full"},
    "quick": {"name": "三爻快占", "label": "三爻快占", "method_key": "quick"},
    "name": {"name": "姓名起卦", "label": "姓名起卦", "method_key": "name"},
    "daily": {"name": "当日气运", "label": "当日气运", "method_key": "daily"},
    "item": {"name": "寻物专项", "label": "寻物专项占", "method_key": "item"},
    "decision": {"name": "二选一决策", "label": "二选一决策", "method_key": "decision"},
    "multi_decision": {"name": "多选最优", "label": "多选最优决策", "method_key": "multi_decision"},
    "bazi": {"name": "四柱八字", "label": "四柱八字基础分析", "method_key": "bazi"},
    "qimen": {"name": "奇门运筹", "label": "奇门运筹分析", "method_key": "qimen"},
}

FOCUS_REQUIRED_FEATURES = frozenset({
    "full",
    "quick",
    "item",
    "decision",
    "multi_decision",
    "qimen",
})


def _clean(text, default="", limit=200):
    value = (text or "").strip()
    if not value:
        value = default
    return value[:limit]


def _resolve_name_strokes(text, provided, label):
    analysis = analyze_text_strokes(text)
    if provided is not None:
        return provided, "手动提供", analysis
    if analysis["missing"]:
        missing = "、".join(dict.fromkeys(analysis["missing"]))
        raise ValueError(f"系统暂未识别{label}中的「{missing}」，请手动填写{label}总笔画")
    if analysis["total"] <= 0:
        raise ValueError(f"无法识别{label}笔画，请手动填写{label}总笔画")
    return analysis["total"], "系统自动识别", analysis


def _stroke_breakdown(analysis):
    return " + ".join(
        f"{item['char']}{item['stroke']}画"
        for item in analysis["details"]
        if item["stroke"] is not None
    )


def _section(title, items):
    return {"title": title, "items": [str(item) for item in items if item not in (None, "")]}


def _text_report_sections(report, initial_title="起局摘要"):
    """把 CLI 的标题式报告转换为 Web 可折叠分节。"""
    sections = []
    title = initial_title
    items = []
    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("【") and line.endswith("】"):
            if items:
                sections.append(_section(title, items))
            title = line[1:-1]
            items = []
        else:
            items.append(line)
    if items:
        sections.append(_section(title, items))
    return sections


def _plain_qimen_conclusion(result):
    """压缩奇门首屏结论，完整依据保留在折叠分节。"""
    decision = result.get("integrated_decision", {})
    confidence = result.get("confidence_profile", {})
    guardrails = result.get("execution_guardrails", {})
    signal = decision.get("final_signal") or "信号未定"
    primary = decision.get("primary_direction") or "待定方位"
    priority = decision.get("priority") or "先核信息"
    guard_mode = guardrails.get("mode") or "小步验证"
    score = confidence.get("score", "未评估")
    level = confidence.get("level") or "待校准"
    return (
        f"{signal}：主位优先{primary}，策略为{priority}，执行上{guard_mode}。"
        f"置信度{score}/100（{level}）；关键动作前先核对现实条件与停止条件。"
    )


def _profile_section(question, method_key):
    profile = build_question_profile(question, current_method_key=method_key)
    text = format_question_profile(profile)
    return _section("问事校准", [line.strip() for line in text.splitlines() if line.strip()])


def _hexagram_sections(result):
    tiyong = result.get("tiyong_info", {})
    return [
        _section("卦象概要", [
            f"【{result['gua_name']}】{result['ji_xiong']}",
            f"卦辞：{result.get('gua_ci', '')}",
            f"卦意：{'、'.join(result.get('core_meaning', [])[:4])}",
            f"校准：{result.get('calibration_tip', '')}",
            f"大象：{result.get('daxiang', '')}",
            f"彖传：{result.get('tuanzhuan', '')}",
        ]),
        _section("体用与动变", [
            f"体用：{tiyong.get('relation', '')} — {tiyong.get('relation_desc', '')}",
            f"五行：{result.get('sheng_ke_analysis', '')}",
            f"旺衰：{result.get('wang_shuai_analysis', '')}",
            f"动爻：{result.get('dong_yao_tip', '')}",
            result.get("bian_line_relation_tip", ""),
            result.get("hu_gua_tip", ""),
            result.get("cuo_gua_tip", ""),
            result.get("zong_gua_tip", ""),
        ]),
        _section("纳甲用神", [
            result.get("yongshen_system_summary", ""),
            result.get("liuqin_interpretation", ""),
            result.get("line_strength_summary", ""),
            result.get("liushen_zhihua_summary", ""),
            result.get("dizhi_relation_summary", ""),
        ]),
        _section("传统依据与现实校验", [
            result.get("source_trace", ""),
            result.get("reality_check", ""),
            result.get("traditional_evidence_chain", ""),
        ]),
        _section("断语", [
            result.get("judgment_detail", ""),
            result.get("judgment_conclusion", ""),
        ]),
        _section("人本提醒", [
            result.get("human_guidance", ""),
            result.get("human_agency_reminder", ""),
        ]),
    ]


def _three_yao_sections(result, info):
    return [
        _section("卦象概要", [
            result.get("core_tip", ""),
            result.get("meaning_tip", ""),
            result.get("tiyong_note", ""),
            result.get("single_tiyong_tip", ""),
        ]),
        _section("方位天时物象", [
            result.get("direction_tip", ""),
            result.get("weather_tip", ""),
            result.get("wu_xiang_tip", ""),
            f"三爻：{info.get('yao_list', [])}",
        ]),
        _section("建议与边界", [
            result.get("suggest", ""),
            result.get("external_omen_tip", ""),
            "三爻适合紧急、单点、短期判断；重大事项请改用六爻详占。",
        ]),
    ]


def _format_bazi_hidden(hidden_stems):
    return "、".join(
        f"{item['stem']}{item['ten_god']}({item['weight']:.1f})"
        for item in hidden_stems
    )


def _bazi_sections(result):
    day_master = result["day_master"]
    pattern = result["pattern_analysis"]
    useful = result["useful_profile"]
    luck = result["luck_cycles"]
    current_year = result["current_year"]
    timing = result["current_timing_analysis"]
    hour_candidates = result["hour_candidates"]
    return [
        _section("四柱", [
            f"出生：{result['birth']['date']} {result['birth']['time']}（{result['birth']['calendar']}）",
            f"八字：{result['bazi']}",
            *[
                (
                    f"{pillar['name']} {pillar['ganzhi']}：天干{pillar['gan']}{pillar['stem_ten_god']}；"
                    f"地支{pillar['zhi']}藏干[{_format_bazi_hidden(pillar['hidden_stems'])}]"
                )
                for pillar in result["pillars"]
            ],
        ]),
        _section("日主与五行", [
            (
                f"日主：{day_master['day_gan']}{day_master['day_element']}；"
                f"月令：{day_master['yueling']}；季节状态：{day_master['season_status']}；"
                f"判断：{day_master['level']}（评分{day_master['score']}）"
            ),
            f"五行分布：{result['element_balance']}",
            f"十神分组：{result['ten_god_counts']['groups']}",
            day_master["advice"],
        ]),
        _section("阶段提示", [item["summary"] for item in result["stage_analysis"]]),
        _section("内外气质", [
            result["inner_outer"]["summary"],
            "出生时辰临界时，此项只能辅助观察，不能单独反推时辰。",
        ]),
        _section("格局倾向", [
            f"{pattern['pattern']}：{pattern['strategy']}",
            f"显著十神：{pattern['top_ten_gods']}",
            pattern["note"],
        ]),
        _section("喜忌取向", [
            useful["summary"],
            f"可借力：{'、'.join(useful['favorable_groups']) or '不固定'}",
            f"需治理：{'、'.join(useful['caution_groups']) or '不固定'}",
            useful["principle"],
        ]),
        _section("岁运同参", [
            timing["summary"],
            timing["action_tip"],
            *timing["details"],
        ]),
        _section("大运流年", [
            luck["summary"],
            *[
                (
                    f"{cycle['summary']}约{cycle['calendar_start_year']}-{cycle['calendar_end_year']}年。"
                    f"{cycle.get('useful_evaluation', {}).get('label', '')}。"
                    f"{'当前所处大运。' if luck.get('current_cycle') and cycle['index'] == luck['current_cycle']['index'] else ''}"
                )
                for cycle in luck.get("cycles", [])[:8]
            ],
            current_year["summary"],
        ]),
        _section("临界时辰对照", [
            hour_candidates["summary"],
            *[
                (
                    f"{candidate['summary']}"
                    f"{'（当前采用）' if candidate['selected'] else ''}"
                )
                for candidate in hour_candidates["candidates"]
            ],
        ]),
        _section("关系双向性", result["relationship_notes"]),
        _section("边界", [
            result["boundary_note"],
            "八字用于传统文化研究和自我观察，不替代现实证据、专业意见和个人选择。",
        ]),
    ]


def _record_if_needed(client_id, question, module_label, summary, should_record=True):
    if should_record:
        record_question(client_id, question, module_label, summary)
    return should_record


def _gate_duplicate(client_id, question, module_label, force, match_mode="semantic"):
    duplicate = check_duplicate(client_id, question, module_label, match_mode=match_mode)
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not force:
        return duplicate
    return duplicate


def _blocked_response(question, duplicate):
    return {
        "plain_conclusion": "此问与近期历史问题相近，建议先复盘前卦；如确有新条件，可确认继续。",
        "summary": "触发复问提醒，尚未起卦。",
        "sections": [
            _section("复问提醒", [
                duplicate.get("message", ""),
                duplicate.get("ethics", ""),
                f"此前问题：{duplicate.get('matched', {}).get('question', '')}",
                f"此前结果：{duplicate.get('matched', {}).get('result', '')}",
            ])
        ],
        "raw_result": {"question": question},
        "duplicate_check": duplicate,
        "history_recorded": False,
    }


def run_divination(feature_key, payload, client_id):
    if feature_key not in FEATURES:
        raise ValueError("未知功能入口")
    _require_focus_seed(feature_key, payload.focus_seed)
    if feature_key == "full":
        return _run_full(payload, client_id)
    if feature_key == "quick":
        return _run_quick(payload, client_id)
    if feature_key == "name":
        return _run_name(payload, client_id)
    if feature_key == "daily":
        return _run_daily(payload, client_id)
    if feature_key == "item":
        return _run_item(payload, client_id)
    if feature_key == "decision":
        return _run_decision(payload, client_id)
    if feature_key == "multi_decision":
        return _run_multi_decision(payload, client_id)
    if feature_key == "bazi":
        return _run_bazi(payload, client_id)
    if feature_key == "qimen":
        return _run_qimen(payload, client_id)
    raise ValueError("未知功能入口")


def _require_focus_seed(feature_key, focus_seed):
    if feature_key in FOCUS_REQUIRED_FEATURES and focus_seed <= 0:
        raise ValueError("请先完成默念凝神，再提交本次分析")


def _run_full(payload, client_id):
    question = _clean(payload.question, "未命名问题")
    duplicate = _gate_duplicate(client_id, question, "六爻详占", payload.force)
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(question, duplicate)

    info = dynamic_time_qi_gua(
        question=question,
        mode="full",
        extra_text=_clean(payload.external_omen, limit=160),
        focus_seed=payload.focus_seed,
    )
    info["external_omen"] = _clean(payload.external_omen, limit=160)
    result = interpret_hexagram(info)
    sections = [_profile_section(question, "full")] + _hexagram_sections(result)
    summary = f"{result['gua_name']}（{result['ji_xiong']}）"
    recorded = _record_if_needed(client_id, question, "六爻详占", summary)
    return {
        "plain_conclusion": result["plain_conclusion"],
        "summary": summary,
        "sections": sections,
        "raw_result": {"hexagram": result, "input": info},
        "duplicate_check": duplicate,
        "history_recorded": recorded,
    }


def _run_quick(payload, client_id):
    question = _clean(payload.question, "未命名问题")
    duplicate = _gate_duplicate(client_id, question, "三爻快占", payload.force)
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(question, duplicate)

    info = dynamic_three_yao_quick_divination(
        question=question,
        mode="quick",
        extra_text=_clean(payload.external_omen, limit=160),
        focus_seed=payload.focus_seed,
    )
    info["external_omen"] = _clean(payload.external_omen, limit=160)
    result = interpret_three_yao(info)
    sections = [_profile_section(question, "quick")] + _three_yao_sections(result, info)
    summary = f"{info['gua_info']['full_name']}，{result['suggest']}"
    recorded = _record_if_needed(client_id, question, "三爻快占", summary)
    return {
        "plain_conclusion": result["plain_conclusion"],
        "summary": summary,
        "sections": sections,
        "raw_result": {"three_yao": result, "input": info},
        "duplicate_check": duplicate,
        "history_recorded": recorded,
    }


def _run_name(payload, client_id):
    xing = _clean(payload.xing, "", 24)
    ming = _clean(payload.ming, "", 24)
    if not xing or not ming:
        raise ValueError("姓名起卦需要填写姓氏和名字")
    xing_stroke, xing_source, xing_analysis = _resolve_name_strokes(
        xing,
        payload.xing_stroke,
        "姓氏",
    )
    ming_stroke, ming_source, ming_analysis = _resolve_name_strokes(
        ming,
        payload.ming_stroke,
        "名字",
    )
    question = _name_history_prefix(xing, ming)
    duplicate = _gate_duplicate(
        client_id,
        question,
        "姓名起卦",
        payload.force,
        match_mode="prefix",
    )
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(question, duplicate)

    history_question = _name_history_question(xing, ming, xing_stroke, ming_stroke)
    info = name_qi_gua(xing, ming, xing_stroke, ming_stroke)
    result = interpret_hexagram(info)
    sections = _hexagram_sections(result)
    sections.insert(0, _section("姓名信息", [
        f"姓名：{xing}{ming}",
        f"姓氏笔画：{xing_stroke}（{xing_source}）",
        f"名字笔画：{ming_stroke}（{ming_source}）",
        f"姓氏拆分：{_stroke_breakdown(xing_analysis)}" if xing_source == "系统自动识别" else "",
        f"名字拆分：{_stroke_breakdown(ming_analysis)}" if ming_source == "系统自动识别" else "",
    ]))
    summary = f"{xing}{ming}：{result['gua_name']}（{result['ji_xiong']}）"
    recorded = _record_if_needed(client_id, history_question, "姓名起卦", summary)
    return {
        "plain_conclusion": result["plain_conclusion"],
        "summary": summary,
        "sections": sections,
        "raw_result": {
            "hexagram": result,
            "input": info,
            "stroke_source": {"xing": xing_source, "ming": ming_source},
        },
        "duplicate_check": duplicate,
        "history_recorded": recorded,
    }


def _run_daily(payload, client_id):
    info = time_qi_gua()
    result = interpret_hexagram(info)
    daily_info = daily_guidance_gua()
    helper = interpret_three_yao(daily_info)
    lunar = info["lunar_info"]
    plain = _plain_daily_conclusion(result, helper)
    sections = [
        _section("日期与主卦", [
            f"农历：{lunar['year']}年{lunar['month']}月{lunar['day']}日",
            f"日干支：{get_accurate_day_ganzhi()}",
            f"季节：{lunar['season']}",
            f"当日主卦：{result['gua_name']}（{result['ji_xiong']}）",
            f"基调：{'、'.join(result.get('core_meaning', [])[:3])}",
        ]),
        *_hexagram_sections(result),
        _section("辅助指引", [
            helper.get("core_tip", ""),
            helper.get("meaning_tip", ""),
            helper.get("plain_conclusion", ""),
        ]),
    ]
    summary = f"当日气运：{result['gua_name']}（{result['ji_xiong']}）"
    return {
        "plain_conclusion": plain,
        "summary": summary,
        "sections": sections,
        "raw_result": {"hexagram": result, "daily": helper, "input": info},
        "duplicate_check": {"is_duplicate": False, "action": "none"},
        "history_recorded": False,
    }


def _run_item(payload, client_id):
    item_name = _clean(payload.item_name, "目标物品", 80)
    last_place = _clean(payload.last_place, "未提供", 120)
    item_feature = _clean(payload.item_feature, "未提供", 120)
    search_scope = _clean(payload.search_scope, "1", 8)
    external_omen = _clean(payload.external_omen, "", 160)
    question = f"寻找{item_name}"
    duplicate = _gate_duplicate(client_id, question, "寻物专项占", payload.force)
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(question, duplicate)

    extra = f"{item_name}|{last_place}|{item_feature}|范围:{search_scope}|外应:{external_omen}"
    info = dynamic_three_yao_quick_divination(
        question=question,
        mode="item_search",
        extra_text=extra,
        focus_seed=payload.focus_seed,
    )
    info["external_omen"] = external_omen
    result = interpret_three_yao(info)
    gua_info = info["gua_info"]
    gua_name = gua_info["name"]
    tips = _item_tips(item_name, last_place, item_feature, gua_name)
    plain = _plain_item_conclusion(gua_name, tips, search_scope)
    sections = [_profile_section(question, "item")] + _three_yao_sections(result, info)
    sections.extend([
        _section("寻物定位", [
            f"寻找：{item_name}",
            f"最后位置：{last_place}",
            f"特征：{item_feature}",
            f"寻回概率：{_likelihood(gua_name)}",
            f"空间定位：{_hint(gua_name)}",
            result.get("direction_tip", ""),
        ]),
        _section("寻找建议", tips + [
            "回到最后见到它的位置，不要急着扩大范围。",
            "无果则沿最近行动路线反向寻找。",
        ]),
    ])
    summary = f"得{gua_info['name']}卦，方位{gua_info['position']}"
    recorded = _record_if_needed(client_id, question, "寻物专项占", summary)
    return {
        "plain_conclusion": plain,
        "summary": summary,
        "sections": sections,
        "raw_result": {"three_yao": result, "input": info, "tips": tips},
        "duplicate_check": duplicate,
        "history_recorded": recorded,
    }


def _run_decision(payload, client_id):
    question = _clean(payload.question, "未命名问题")
    option_a = _clean(payload.option_a, "选项A", 120)
    option_b = _clean(payload.option_b, "选项B", 120)
    duplicate = _gate_duplicate(client_id, question, "二选一决策", payload.force)
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(question, duplicate)

    result_a = interpret_hexagram(_option_qi_gua(question, option_a, payload.focus_seed))
    score_a = _option_score(result_a)
    result_a["_score"] = score_a
    result_b = interpret_hexagram(_option_qi_gua(question, option_b, payload.focus_seed))
    score_b = _option_score(result_b)
    result_b["_score"] = score_b
    plain = _plain_decision_conclusion(option_a, score_a, result_a, option_b, score_b, result_b)
    sections = [_profile_section(question, "decision")]
    sections.extend([
        _section("选项A", [
            f"A：{option_a}",
            f"卦：{result_a['gua_name']}（{result_a['ji_xiong']}）",
            f"评分：{score_a}/120",
            f"风险：{_risk_tip(result_a)}",
            result_a.get("judgment_conclusion", ""),
        ]),
        _section("选项B", [
            f"B：{option_b}",
            f"卦：{result_b['gua_name']}（{result_b['ji_xiong']}）",
            f"评分：{score_b}/120",
            f"风险：{_risk_tip(result_b)}",
            result_b.get("judgment_conclusion", ""),
        ]),
        _section("综合对比", [
            f"A评分：{score_a}；B评分：{score_b}；分差：{abs(score_a - score_b)}",
            plain,
            "卦象只为参考，重要事项仍以事实、数据和专业意见为准。",
        ]),
    ])
    summary = (
        f"A「{option_a}」→ {result_a['gua_name']}（{result_a['ji_xiong']}），"
        f"B「{option_b}」→ {result_b['gua_name']}（{result_b['ji_xiong']}）"
    )
    recorded = _record_if_needed(client_id, question, "二选一决策", summary)
    return {
        "plain_conclusion": plain,
        "summary": summary,
        "sections": sections,
        "raw_result": {"option_a": result_a, "option_b": result_b},
        "duplicate_check": duplicate,
        "history_recorded": recorded,
    }


def _run_multi_decision(payload, client_id):
    question = _clean(payload.question, "未命名问题")
    options = parse_multi_options_text(payload.options_text)
    question_key = f"多选最优：{question}"
    duplicate = _gate_duplicate(
        client_id,
        question_key,
        "多选最优决策",
        payload.force,
        match_mode="prefix",
    )
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(question_key, duplicate)

    history_question = _multi_history_question(question, options)
    scored = _score_options(question, options, payload.focus_seed)
    best = scored[0]
    best_result = best["result"]
    plain = _plain_multi_conclusion(scored)
    sections = [
        _profile_section(_profile_question(question, options), "multi_decision"),
        _section("综合排名", [
            f"{rank}. {item['label']}「{item['option']}」：{item['score']}/120"
            for rank, item in enumerate(scored, 1)
        ]),
        _section("最优选项", [
            f"{best['label']}：{best['option']}",
            f"卦：{best_result['gua_name']}（{best_result['ji_xiong']}）",
            f"评分：{best['score']}/120",
            f"风险：{_risk_tip(best_result)}",
            best_result.get("judgment_conclusion", ""),
            "多选评分只作传统文化参考，最终仍应核对现实成本、风险和执行条件。",
        ]),
    ]
    summary = _record_summary(scored)
    recorded = _record_if_needed(client_id, history_question, "多选最优决策", summary)
    return {
        "plain_conclusion": plain,
        "summary": summary,
        "sections": sections,
        "raw_result": {"ranked": scored, "options": options},
        "duplicate_check": duplicate,
        "history_recorded": recorded,
    }


def _run_bazi(payload, client_id):
    if payload.birth_hour is None:
        raise ValueError("四柱八字需要填写出生小时")
    birth_minute = payload.birth_minute or 0
    history_question = _bazi_history_question(
        payload.birth_date,
        payload.birth_hour,
        birth_minute,
        payload.gender,
    )
    duplicate = _gate_duplicate(
        client_id,
        history_question,
        "四柱八字",
        payload.force,
        match_mode="exact",
    )
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(history_question, duplicate)

    result = analyze_bazi_birth(
        payload.birth_date,
        payload.birth_hour,
        birth_minute,
        payload.gender,
    )
    summary = f"{result['birth']['date']} {result['birth']['time']}：{result['bazi']}"
    record_question(client_id, history_question, "四柱八字", _bazi_history_summary(result))
    return {
        "plain_conclusion": result["plain_conclusion"],
        "summary": summary,
        "sections": _bazi_sections(result),
        "raw_result": {"bazi": result},
        "duplicate_check": duplicate,
        "history_recorded": True,
    }


def _run_qimen(payload, client_id):
    topic = _clean(payload.question, "未命名事项")
    direction = _clean(payload.direction, "", 20)
    mode = _clean(payload.qimen_mode, "综合", 12)
    question_key = f"奇门：{topic}"
    duplicate = _gate_duplicate(
        client_id,
        question_key,
        "奇门运筹",
        payload.force,
        match_mode="prefix",
    )
    if duplicate.get("is_duplicate") and duplicate.get("action") in ("block", "warn") and not payload.force:
        return _blocked_response(question_key, duplicate)

    history_question = _qimen_history_question(topic, direction, mode)
    result = analyze_qimen(
        topic=topic,
        direction=direction,
        mode=mode,
        current=datetime.datetime.now(),
    )
    summary = _qimen_history_summary(result)
    recorded = _record_if_needed(client_id, history_question, "奇门运筹", summary)
    return {
        "plain_conclusion": _plain_qimen_conclusion(result),
        "summary": summary,
        "sections": _text_report_sections(format_qimen_report(result)),
        "raw_result": {"qimen": result, "focus_seed": payload.focus_seed},
        "duplicate_check": duplicate,
        "history_recorded": recorded,
    }


def recommend_methods(question):
    question = _clean(question, "", 200)
    text, ranked = format_method_recommendation(question)
    return {
        "question": question,
        "summary": text,
        "ranked": ranked,
    }
