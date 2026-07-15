# -*- coding: utf-8 -*-
"""规则与数据一致性审计。

该模块面向维护者：把纳甲、世应、八宫、六十四卦校准与起卦法选择器
中最容易手写漂移的规则集中校验，便于每次改规则后快速回归。
"""

import ast
import datetime
import re
from pathlib import Path

from config.bagua_data import NUM_TO_GUA_NAME, PALACE_HEXAGRAMS, PALACE_WUXING
from config.bazi_data import DIZHI_HIDDEN_STEMS, GAN_YINYANG, TEN_GOD_GROUP
from config.hexagram_calibration import HEXAGRAM_CALIBRATION, build_calibration_tip
from config.hexagram_data import HEXAGRAM_DATA
from config.naja_data import BAGUA_NAJIA, BAGUA_SHI_YING, LIUSHEN_ORDER, LIUSHEN_START, NAYIN_TABLE
from config.name_strokes import KANGXI_STROKES, analyze_text_strokes
from config.qimen_data import (
    EIGHT_DOORS,
    EIGHT_GODS,
    NINE_STARS,
    OUTER_PALACE_KEYS,
    QIMEN_PALACES,
    QIMEN_SCENARIO_RULES,
    QIMEN_STEM_MEANING,
    QIMEN_STEM_ORDER,
    SIX_JIA_DUN,
    SIX_YI_TO_HIDDEN_JIA,
    SIX_YI,
    THREE_QI,
)
from config.wuxing_rules import DIZHI_ORDER, DIZHI_WUXING, TIANGAN_WUXING
from core.method_selector import METHOD_PROFILES, NEGATIVE_HINTS, recommend_divination_methods
from core.qimen import analyze_qimen
from core.zhuanggua import (
    SHI_YING_BY_PALACE_INDEX,
    get_changsheng_for_line,
    get_hexagram_palace,
    get_liuqin_all_lines,
    get_najia_all_lines,
    get_shi_ying,
    get_shi_ying_by_key,
)
from core.bazi import analyze_bazi_birth, get_ten_god


TIANGAN_ORDER = set(TIANGAN_WUXING)
VALID_DIZHI = set(DIZHI_ORDER)
VALID_LIUQIN = {"父母", "兄弟", "子孙", "妻财", "官鬼"}
REQUIRED_CALIBRATION_FIELDS = ("axis", "keywords", "proper_use", "risk")
REQUIRED_FOCUS_WIRING = {
    "modules/full_divination.py": ("六爻详占", ("collect_focus_seed", "focus_seed")),
    "modules/quick_divination.py": ("三爻快占", ("collect_focus_seed", "focus_seed")),
    "modules/item_search.py": ("寻物专项占", ("collect_focus_seed", "focus_seed")),
    "modules/decision_helper.py": ("二选一决策", ("collect_focus_seed", "focus_seed")),
    "modules/multi_decision.py": ("多选最优决策", ("collect_focus_seed", "focus_seed")),
    "modules/qimen.py": ("奇门运筹", ("collect_focus_seed", "current=focus_moment")),
}
REQUIRED_WEB_FOCUS_WIRING = {
    "web/templates/feature.html": (
        "Web 二选一",
        ('{% if key in ["full", "quick", "item", "decision", "multi_decision", "qimen"] %}', "data-focus-seed", "data-focus-ritual"),
    ),
    "web/static/app.js": (
        "Web 凝神交互",
        ("completeRunningFocus", "focus_seed", "resetFocus", "invalidateFocusForEdit"),
    ),
    "web/services.py": (
        "Web 二选一与奇门",
        (
            "FOCUS_REQUIRED_FEATURES",
            "_require_focus_seed(feature_key, payload.focus_seed)",
            "_option_qi_gua(question, option_a, payload.focus_seed)",
            "_option_qi_gua(question, option_b, payload.focus_seed)",
            "current=datetime.datetime.now()",
            '"focus_seed": payload.focus_seed',
        ),
    ),
}
REQUIRED_WEB_REQUEST_WIRING = {
    "web/app.py": (
        "Web 请求校验",
        (
            "except ValidationError as exc:",
            "raise HTTPException(status_code=422, detail=exc.errors()) from exc",
            "MAX_RATE_BUCKETS = 4096",
            "MAX_REQUEST_BYTES = 64 * 1024",
            "_prune_rate_buckets",
            '"Content-Security-Policy"',
            '"Permissions-Policy"',
            '"X-Frame-Options": "DENY"',
            "status_code=413",
            "len(await request.body()) > MAX_REQUEST_BYTES",
        ),
    ),
    "web/schemas.py": (
        "Web 选择器输入",
        ('question: str = Field(..., min_length=1, max_length=200)',),
    ),
    "web/static/app.js": (
        "Web 错误反馈",
        (
            "renderStatus",
            "normalizeErrorDetail",
            'form.dataset.submitting === "true"',
            "网络连接失败，请确认服务仍在运行后重试。",
            "paragraph.textContent = message",
        ),
    ),
}
REQUIRED_WEB_NAME_STROKE_WIRING = {
    "web/services.py": (
        "analyze_text_strokes",
        "_resolve_name_strokes",
        "系统自动识别",
        "_stroke_breakdown",
        '"stroke_source": {"xing": xing_source, "ming": ming_source}',
    ),
    "web/schemas.py": ("xing_stroke: Optional[int] = Field(None, ge=1, le=999)",),
    "web/templates/feature.html": (
        'name="xing_stroke" type="number" min="1" max="999" placeholder="留空则自动识别"',
        'name="ming_stroke" type="number" min="1" max="999" placeholder="留空则自动识别"',
        "系统优先按内置康熙/Unihan 数据自动合计",
    ),
}
DETERMINISTIC_NO_FOCUS = {
    "modules/daily_fortune.py": "当日气运",
    "modules/name_divination.py": "姓名起卦",
    "modules/bazi.py": "四柱八字",
    "modules/method_selector.py": "起卦法选择器",
}
REQUIRED_HISTORY_WIRING = {
    "modules/full_divination.py": ("六爻详占", ("handle_duplicate_check", "record_question")),
    "modules/quick_divination.py": ("三爻快占", ("handle_duplicate_check", "record_question")),
    "modules/name_divination.py": ("姓名起卦", ("handle_duplicate_check", "record_question", "allow_rephrase=False", 'match_mode="prefix"')),
    "modules/item_search.py": ("寻物专项占", ("handle_duplicate_check", "record_question", "allow_rephrase=False", 'match_mode="prefix"')),
    "modules/decision_helper.py": ("二选一决策", ("handle_duplicate_check", "record_question", "allow_rephrase=False", 'match_mode="prefix"')),
    "modules/multi_decision.py": ("多选最优决策", ("handle_duplicate_check", "record_question", "allow_rephrase=False", 'match_mode="prefix"')),
    "modules/bazi.py": ("四柱八字", ("handle_duplicate_check", "record_question", "allow_rephrase=False", 'match_mode="exact"')),
    "modules/qimen.py": ("奇门运筹", ("handle_duplicate_check", "record_question", "allow_rephrase=False", 'match_mode="prefix"')),
}
REQUIRED_WEB_HISTORY_WIRING = {
    "web/history_store.py": (
        "Web 复问匹配",
        ("match_mode=\"semantic\"", "match_mode=match_mode"),
    ),
    "web/services.py": (
        "Web 姓名与八字",
        (
            "_name_history_prefix",
            "_name_history_question",
            'match_mode="prefix"',
            "_bazi_history_question",
            "_bazi_history_summary",
            'match_mode="exact"',
            "_multi_history_question",
            "_record_summary",
            "_run_multi_decision",
            "_qimen_history_question",
            "_qimen_history_summary",
            "_run_qimen",
            "_plain_qimen_conclusion",
        ),
    ),
    "web/templates/history.html": (
        "Web 历史清理确认",
        ('data-confirm-message="只清空当前设备的匿名历史，确认继续？"', "{% if cleared %}"),
    ),
    "web/static/app.js": (
        "Web 历史清理交互",
        ('event.target.closest("[data-confirm-message]")', "window.confirm"),
    ),
    "web/app.py": (
        "Web 历史清理反馈",
        ('RedirectResponse("/history?cleared=1", status_code=303)', 'request.query_params.get("cleared") == "1"'),
    ),
}
DETERMINISTIC_NO_HISTORY = {
    "modules/daily_fortune.py": "当日气运",
    "modules/method_selector.py": "起卦法选择器",
}


def _issue(level, area, message, detail=""):
    return {
        "level": level,
        "area": area,
        "message": message,
        "detail": detail,
    }


def _hexagram_names():
    return {detail.get("name", "") for detail in HEXAGRAM_DATA.values()}


def audit_focus_seed_wiring():
    """校验需要承接当下问念的 CLI 入口是否配备凝神步骤。"""
    issues = []
    project_root = Path(__file__).resolve().parents[1]

    for filename, (feature_name, required_tokens) in REQUIRED_FOCUS_WIRING.items():
        path = project_root / filename
        if not path.exists():
            issues.append(_issue("error", "凝神入口", f"{feature_name}入口文件缺失", filename))
            continue

        text = path.read_text(encoding="utf-8")
        missing_tokens = [token for token in required_tokens if token not in text]
        if missing_tokens:
            issues.append(_issue(
                "error",
                "凝神入口",
                f"{feature_name}缺少凝神承接",
                f"{filename} missing={missing_tokens}",
            ))

    for filename, (feature_name, required_tokens) in REQUIRED_WEB_FOCUS_WIRING.items():
        path = project_root / filename
        if not path.exists():
            issues.append(_issue("error", "凝神入口", f"{feature_name}入口文件缺失", filename))
            continue

        text = path.read_text(encoding="utf-8")
        missing_tokens = [token for token in required_tokens if token not in text]
        if missing_tokens:
            issues.append(_issue(
                "error",
                "凝神入口",
                f"{feature_name}缺少凝神承接",
                f"{filename} missing={missing_tokens}",
            ))

        if filename == "web/templates/feature.html":
            focus_position = text.find("data-focus-ritual")
            last_business_field = max(
                text.find('name="options_text"'),
                text.find('name="qimen_mode"'),
                text.find('name="gender"'),
            )
            if focus_position < last_business_field:
                issues.append(_issue(
                    "error",
                    "凝神入口",
                    "Web 凝神步骤应位于全部业务字段之后",
                    filename,
                ))

    for filename, feature_name in DETERMINISTIC_NO_FOCUS.items():
        path = project_root / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "collect_focus_seed" in text:
            issues.append(_issue(
                "warning",
                "凝神入口",
                f"{feature_name}属于确定性或维护型功能，不建议接入凝神种子",
                filename,
            ))

    return issues


def audit_web_request_wiring():
    """校验 Web 校验错误、网络异常和重复提交保护。"""
    issues = []
    project_root = Path(__file__).resolve().parents[1]
    for filename, (feature_name, required_tokens) in REQUIRED_WEB_REQUEST_WIRING.items():
        path = project_root / filename
        if not path.exists():
            issues.append(_issue("error", "Web 请求", f"{feature_name}文件缺失", filename))
            continue
        text = path.read_text(encoding="utf-8")
        missing = [token for token in required_tokens if token not in text]
        if missing:
            issues.append(_issue(
                "error",
                "Web 请求",
                f"{feature_name}缺少统一保护",
                f"{filename} missing={missing}",
            ))
    templates_root = project_root / "web/templates"
    for path in templates_root.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\son[a-z]+\s*=", text, re.IGNORECASE):
            issues.append(_issue(
                "error",
                "Web 请求",
                "严格内容策略下不应使用内联事件处理器",
                str(path.relative_to(project_root)),
            ))
    return issues


def audit_history_wiring():
    """校验问事型 CLI 入口是否接入复问拦截和历史记录。"""
    issues = []
    project_root = Path(__file__).resolve().parents[1]

    for filename, (feature_name, required_tokens) in REQUIRED_HISTORY_WIRING.items():
        path = project_root / filename
        if not path.exists():
            issues.append(_issue("error", "历史记录", f"{feature_name}入口文件缺失", filename))
            continue

        text = path.read_text(encoding="utf-8")
        missing_tokens = [token for token in required_tokens if token not in text]
        if missing_tokens:
            issues.append(_issue(
                "error",
                "历史记录",
                f"{feature_name}缺少复问拦截或记录",
                f"{filename} missing={missing_tokens}",
            ))

    for filename, (feature_name, required_tokens) in REQUIRED_WEB_HISTORY_WIRING.items():
        path = project_root / filename
        if not path.exists():
            issues.append(_issue("error", "历史记录", f"{feature_name}入口文件缺失", filename))
            continue

        text = path.read_text(encoding="utf-8")
        missing_tokens = [token for token in required_tokens if token not in text]
        if missing_tokens:
            issues.append(_issue(
                "error",
                "历史记录",
                f"{feature_name}缺少复问拦截或记录",
                f"{filename} missing={missing_tokens}",
            ))

    web_services_path = project_root / "web/services.py"
    if web_services_path.exists():
        web_services_text = web_services_path.read_text(encoding="utf-8")
        daily_match = re.search(
            r"def _run_daily\(.*?\n(?=def _run_item\()",
            web_services_text,
            re.DOTALL,
        )
        if not daily_match:
            issues.append(_issue("error", "历史记录", "无法识别 Web 当日气运服务", "web/services.py"))
        else:
            daily_block = daily_match.group(0)
            if "record_question(" in daily_block:
                issues.append(_issue(
                    "warning",
                    "历史记录",
                    "Web 当日气运属于确定性功能，不应写入问事历史",
                    "web/services.py",
                ))
            if '"history_recorded": False' not in daily_block:
                issues.append(_issue(
                    "error",
                    "历史记录",
                    "Web 当日气运应明确标记为未写入历史",
                    "web/services.py",
                ))

    for filename, feature_name in DETERMINISTIC_NO_HISTORY.items():
        path = project_root / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "record_question" in text:
            issues.append(_issue(
                "warning",
                "历史记录",
                f"{feature_name}不是具体起卦问事，不建议写入问事历史",
                filename,
            ))

    main_path = project_root / "main.py"
    if not main_path.exists():
        issues.append(_issue("error", "历史记录", "CLI 主菜单文件缺失", "main.py"))
        return issues

    main_text = main_path.read_text(encoding="utf-8")
    menu_match = re.search(r"def main_menu\(\):(?P<body>.*?)\ndef main\(\):", main_text, re.DOTALL)
    if not menu_match:
        issues.append(_issue("error", "历史记录", "无法识别 CLI 主菜单结构", "main.py"))
        return issues

    menu_labels = [
        label
        for _, label in re.findall(
            r'^\s*print\("(\d+)\.\s+([^\"]+)"\)\s*$',
            menu_match.group("body"),
            re.MULTILINE,
        )
    ]
    expected_tail = [
        "查看近期起卦记录",
        "起卦法选择器（按问题推荐入口）",
        "退出系统",
    ]
    if menu_labels[-3:] != expected_tail:
        issues.append(_issue(
            "error",
            "历史记录",
            "CLI 主菜单尾部顺序发生漂移",
            f"actual={menu_labels[-3:]} expected={expected_tail}",
        ))
    if "清除历史询问记录（谨慎操作）" not in menu_labels[:-3]:
        issues.append(_issue(
            "error",
            "历史记录",
            "清除历史入口应位于固定尾部菜单之前",
            str(menu_labels),
        ))

    return issues


def audit_name_stroke_data():
    """校验姓名起卦自动笔画表的关键样例。"""
    issues = []
    required_samples = {
        "张": 11,
        "三": 3,
        "李": 7,
        "四": 5,
        "马": 10,
        "梦": 14,
    }
    for char, expected in required_samples.items():
        actual = KANGXI_STROKES.get(char)
        if actual != expected:
            issues.append(_issue(
                "error",
                "姓名笔画",
                f"{char} 的康熙笔画不符合关键样例",
                f"actual={actual} expected={expected}",
            ))

    zhang_san = analyze_text_strokes("张三")
    if zhang_san["missing"] or zhang_san["total"] != 14:
        issues.append(_issue(
            "error",
            "姓名笔画",
            "张三自动笔画合计错误",
            str(zhang_san),
        ))

    project_root = Path(__file__).resolve().parents[1]
    for filename, required_tokens in REQUIRED_WEB_NAME_STROKE_WIRING.items():
        path = project_root / filename
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [token for token in required_tokens if token not in text]
        if missing:
            issues.append(_issue(
                "error",
                "姓名笔画",
                "Web 姓名起卦未复用自动笔画能力",
                f"{filename} missing={missing}",
            ))

    return issues


def audit_palace_hexagram_matrix():
    """校验八宫六十四卦矩阵。"""
    issues = []
    all_keys = []

    if set(PALACE_HEXAGRAMS) != set(PALACE_WUXING):
        issues.append(_issue(
            "error",
            "八宫",
            "PALACE_HEXAGRAMS 与 PALACE_WUXING 的宫名不一致",
            f"hexagrams={sorted(PALACE_HEXAGRAMS)} wuxing={sorted(PALACE_WUXING)}",
        ))

    for palace_name, hexagrams in PALACE_HEXAGRAMS.items():
        if len(hexagrams) != 8:
            issues.append(_issue("error", "八宫", f"{palace_name}宫不是 8 卦", str(len(hexagrams))))
        if len(set(hexagrams)) != len(hexagrams):
            issues.append(_issue("error", "八宫", f"{palace_name}宫内部存在重复卦键"))
        for index, key in enumerate(hexagrams):
            all_keys.append(key)
            if key not in HEXAGRAM_DATA:
                issues.append(_issue("error", "八宫", f"{palace_name}宫第{index + 1}卦不在六十四卦库", str(key)))
                continue
            expected_palace = f"{palace_name}宫"
            actual_palace = HEXAGRAM_DATA[key].get("palace", "")
            if actual_palace and actual_palace != expected_palace:
                issues.append(_issue(
                    "warning",
                    "八宫",
                    f"{HEXAGRAM_DATA[key].get('name')} 的 palace 字段与八宫表不一致",
                    f"data={actual_palace} expected={expected_palace}",
                ))

    if len(all_keys) != 64 or len(set(all_keys)) != 64:
        issues.append(_issue("error", "八宫", "八宫表未形成 64 个唯一卦键", f"total={len(all_keys)} unique={len(set(all_keys))}"))

    missing = set(HEXAGRAM_DATA) - set(all_keys)
    extra = set(all_keys) - set(HEXAGRAM_DATA)
    if missing:
        issues.append(_issue("error", "八宫", "八宫表缺少六十四卦键", str(sorted(missing))))
    if extra:
        issues.append(_issue("error", "八宫", "八宫表包含六十四卦库以外的卦键", str(sorted(extra))))

    return issues


def audit_shi_ying_rules():
    """校验手写世应表与八宫序列推导结果是否一致。"""
    issues = []
    expected_names = _hexagram_names()

    missing = expected_names - set(BAGUA_SHI_YING)
    extra = set(BAGUA_SHI_YING) - expected_names
    if missing:
        issues.append(_issue("error", "世应", "BAGUA_SHI_YING 缺少卦名", "、".join(sorted(missing))))
    if extra:
        issues.append(_issue("error", "世应", "BAGUA_SHI_YING 含未知卦名", "、".join(sorted(extra))))

    for key, detail in HEXAGRAM_DATA.items():
        name = detail.get("name", "")
        palace_info = get_hexagram_palace(*key)
        palace_index = palace_info.get("palace_index", -1)
        expected = SHI_YING_BY_PALACE_INDEX.get(palace_index)
        derived = get_shi_ying_by_key(*key)
        by_name = get_shi_ying(name)
        table_value = BAGUA_SHI_YING.get(name)

        if not expected:
            issues.append(_issue("error", "世应", f"{name} 无法按八宫序列推导世应", str(key)))
            continue
        if derived != expected:
            issues.append(_issue("error", "世应", f"{name} 推导世应错误", f"derived={derived} expected={expected}"))
        if by_name != expected:
            issues.append(_issue("error", "世应", f"{name} 名称查询世应错误", f"by_name={by_name} expected={expected}"))
        if table_value and dict(table_value) != expected:
            issues.append(_issue("error", "世应", f"{name} 手写世应表与八宫序列不一致", f"table={table_value} expected={expected}"))

    return issues


def audit_najia_rules():
    """校验纳甲、纳音、六亲与十二长生基础映射。"""
    issues = []
    expected_trigrams = set(NUM_TO_GUA_NAME.values())

    if set(BAGUA_NAJIA) != expected_trigrams:
        issues.append(_issue(
            "error",
            "纳甲",
            "BAGUA_NAJIA 的八卦键不完整",
            f"missing={sorted(expected_trigrams - set(BAGUA_NAJIA))} extra={sorted(set(BAGUA_NAJIA) - expected_trigrams)}",
        ))

    for gua_name, lines in BAGUA_NAJIA.items():
        if len(lines) != 6:
            issues.append(_issue("error", "纳甲", f"{gua_name} 纳甲不是 6 爻", str(lines)))
        if len(set(lines)) != len(lines):
            issues.append(_issue("warning", "纳甲", f"{gua_name} 纳甲存在重复干支", str(lines)))
        for line in lines:
            if len(line) != 2:
                issues.append(_issue("error", "纳甲", f"{gua_name} 出现非法干支长度", line))
                continue
            tiangan, dizhi = line[0], line[1]
            if tiangan not in TIANGAN_ORDER:
                issues.append(_issue("error", "纳甲", f"{gua_name} 出现未知天干", line))
            if dizhi not in VALID_DIZHI:
                issues.append(_issue("error", "纳甲", f"{gua_name} 出现未知地支", line))
            if line not in NAYIN_TABLE:
                issues.append(_issue("error", "纳音", f"{gua_name} 纳甲干支缺少纳音", line))
            changsheng = get_changsheng_for_line(line)
            if changsheng == "未知":
                issues.append(_issue("error", "十二长生", f"{gua_name} 纳甲干支无法推导十二长生", line))

    for upper_num, lower_num in HEXAGRAM_DATA:
        najia_lines = get_najia_all_lines(upper_num, lower_num)
        if len(najia_lines) != 6 or any(line == "未知" for line in najia_lines):
            issues.append(_issue("error", "纳甲", "重卦纳甲生成失败", f"{(upper_num, lower_num)} -> {najia_lines}"))

        palace_wuxing = get_hexagram_palace(upper_num, lower_num).get("palace_wuxing", "")
        liuqin_lines = get_liuqin_all_lines(upper_num, lower_num, palace_wuxing)
        unknown_liuqin = [item for item in liuqin_lines if item not in VALID_LIUQIN]
        if unknown_liuqin:
            issues.append(_issue("error", "六亲", "重卦六亲生成失败", f"{(upper_num, lower_num)} -> {liuqin_lines}"))

    if len(NAYIN_TABLE) != 60:
        issues.append(_issue("error", "纳音", "六十甲子纳音表数量不是 60", str(len(NAYIN_TABLE))))

    return issues


def audit_liushen_rules():
    """校验六神排布基础表。"""
    issues = []
    if len(LIUSHEN_ORDER) != 6 or len(set(LIUSHEN_ORDER)) != 6:
        issues.append(_issue("error", "六神", "LIUSHEN_ORDER 必须是 6 个唯一六神", str(LIUSHEN_ORDER)))
    if set(LIUSHEN_START) != TIANGAN_ORDER:
        issues.append(_issue(
            "error",
            "六神",
            "LIUSHEN_START 必须覆盖十天干",
            f"missing={sorted(TIANGAN_ORDER - set(LIUSHEN_START))} extra={sorted(set(LIUSHEN_START) - TIANGAN_ORDER)}",
        ))
    for gan, index in LIUSHEN_START.items():
        if not isinstance(index, int) or index < 0 or index >= 6:
            issues.append(_issue("error", "六神", f"{gan} 日六神起点非法", str(index)))
    return issues


def audit_hexagram_calibration():
    """校验六十四卦正文与象义校准表。"""
    issues = []
    names = _hexagram_names()

    if len(HEXAGRAM_DATA) != 64:
        issues.append(_issue("error", "六十四卦", "HEXAGRAM_DATA 数量不是 64", str(len(HEXAGRAM_DATA))))
    expected_keys = {(upper, lower) for upper in range(1, 9) for lower in range(1, 9)}
    if set(HEXAGRAM_DATA) != expected_keys:
        issues.append(_issue(
            "error",
            "六十四卦",
            "HEXAGRAM_DATA 未覆盖 8x8 全部卦键",
            f"missing={sorted(expected_keys - set(HEXAGRAM_DATA))} extra={sorted(set(HEXAGRAM_DATA) - expected_keys)}",
        ))

    serials = [detail.get("serial_num") for detail in HEXAGRAM_DATA.values()]
    if set(serials) != set(range(1, 65)):
        issues.append(_issue("error", "六十四卦", "卦序 serial_num 未覆盖 1-64", str(sorted(serials))))

    missing_calibration = names - set(HEXAGRAM_CALIBRATION)
    extra_calibration = set(HEXAGRAM_CALIBRATION) - names
    if missing_calibration:
        issues.append(_issue("error", "象义校准", "缺少卦象校准", "、".join(sorted(missing_calibration))))
    if extra_calibration:
        issues.append(_issue("error", "象义校准", "存在六十四卦以外的校准项", "、".join(sorted(extra_calibration))))

    for name, data in HEXAGRAM_CALIBRATION.items():
        for field in REQUIRED_CALIBRATION_FIELDS:
            if field not in data:
                issues.append(_issue("error", "象义校准", f"{name} 缺少字段 {field}"))
        axis = str(data.get("axis", "")).strip()
        proper_use = str(data.get("proper_use", "")).strip()
        risk = str(data.get("risk", "")).strip()
        keywords = data.get("keywords", [])
        if not axis or "暂缺" in axis:
            issues.append(_issue("error", "象义校准", f"{name} 主轴为空或暂缺"))
        if not proper_use or "暂缺" in proper_use:
            issues.append(_issue("error", "象义校准", f"{name} 宜用为空或暂缺"))
        if not risk or "暂缺" in risk:
            issues.append(_issue("error", "象义校准", f"{name} 风险为空或暂缺"))
        if not isinstance(keywords, list) or len(keywords) < 3:
            issues.append(_issue("warning", "象义校准", f"{name} keywords 少于 3 个", str(keywords)))
        if name in names and "暂缺" in build_calibration_tip(name):
            issues.append(_issue("error", "象义校准", f"{name} 输出提示仍含暂缺"))

    return issues


def audit_method_selector_profiles():
    """校验起卦法选择器配置和几个强规则样例。"""
    issues = []
    required = {"menu", "name", "fit", "basis", "keywords"}
    menus = []
    for key, profile in METHOD_PROFILES.items():
        missing = required - set(profile)
        if missing:
            issues.append(_issue("error", "起卦法选择器", f"{key} profile 缺少字段", "、".join(sorted(missing))))
        if key not in NEGATIVE_HINTS:
            issues.append(_issue("error", "起卦法选择器", f"{key} 缺少边界提示"))
        menus.append(profile.get("menu"))
        if not profile.get("keywords"):
            issues.append(_issue("warning", "起卦法选择器", f"{key} keywords 为空"))
    if len(menus) != len(set(menus)):
        issues.append(_issue("error", "起卦法选择器", "菜单编号存在重复", str(menus)))

    empty_ranked = recommend_divination_methods("")
    if (
        not empty_ranked
        or empty_ranked[0].get("key") != "full"
        or any(not item.get("reason") for item in empty_ranked)
    ):
        issues.append(_issue(
            "error",
            "起卦法选择器",
            "空问题降级推荐缺少完整原因",
            str(empty_ranked[:3]),
        ))

    project_root = Path(__file__).resolve().parents[1]
    web_services_path = project_root / "web/services.py"
    try:
        tree = ast.parse(web_services_path.read_text(encoding="utf-8"))
        feature_node = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "FEATURES" for target in node.targets)
        )
        web_features = ast.literal_eval(feature_node)
        if set(web_features) != set(METHOD_PROFILES):
            issues.append(_issue(
                "error",
                "起卦法选择器",
                "Web 功能与选择器方法未保持一一对应",
                f"web={sorted(web_features)} selector={sorted(METHOD_PROFILES)}",
            ))
        for key, feature in web_features.items():
            if feature.get("method_key") != key:
                issues.append(_issue(
                    "error",
                    "起卦法选择器",
                    f"Web 功能 {key} 的选择器路由键漂移",
                    str(feature.get("method_key")),
                ))
    except Exception as exc:
        issues.append(_issue("error", "起卦法选择器", "无法审计 Web 功能映射", str(exc)))

    continuity_tokens = {
        "web/services.py": ('"question": question',),
        "web/app.py": ('initial_question = request.query_params.get("question", "").strip()[:200]',),
        "web/templates/feature.html": ("{{ initial_question }}",),
        "web/templates/partials/method_result.html": ("result.question|urlencode",),
    }
    for filename, tokens in continuity_tokens.items():
        text = (project_root / filename).read_text(encoding="utf-8")
        missing = [token for token in tokens if token not in text]
        if missing:
            issues.append(_issue(
                "error",
                "起卦法选择器",
                "Web 推荐问题未完整带入目标表单",
                f"{filename} missing={missing}",
            ))

    samples = [
        ("我的手机今天不见了，能找回吗", "item"),
        ("今天整体运势怎么样", "daily"),
        ("A方案还是B方案更适合", "decision"),
        ("这几个方案哪个最优，帮我从多个选项里选一个", "multi_decision"),
        ("多问题选择", "multi_decision"),
        ("周一、周二、周三、周五", "multi_decision"),
        ("这个公司名适合吗，按笔画看", "name"),
        ("我想看八字四柱和十神", "bazi"),
        ("明天谈判从哪个方位切入更有利", "qimen"),
        ("这个合同长期合作风险如何", "full"),
        ("现在要不要马上联系他", "quick"),
    ]
    for question, expected_key in samples:
        ranked = recommend_divination_methods(question)
        actual_key = ranked[0]["key"] if ranked else ""
        if actual_key != expected_key:
            issues.append(_issue(
                "error",
                "起卦法选择器",
                "强规则样例推荐不符合预期",
                f"question={question} expected={expected_key} actual={actual_key}",
            ))

    conflict_samples = [
        ("AI工具值得长期投入吗", "decision"),
        ("这个方案可行吗", "multi_decision"),
        ("这个选项风险如何", "decision"),
    ]
    for question, unrelated_key in conflict_samples:
        ranked = recommend_divination_methods(question)
        candidate = next(item for item in ranked if item["key"] == unrelated_key)
        if candidate["score"] != 0 or candidate["hits"]:
            issues.append(_issue(
                "error",
                "起卦法选择器",
                "单字母或单方案触发了无关决策入口",
                f"question={question} candidate={candidate}",
            ))

    return issues


def audit_bazi_rules():
    """校验八字基础表和十神计算。"""
    issues = []
    if set(GAN_YINYANG) != set(TIANGAN_ORDER):
        issues.append(_issue(
            "error",
            "八字",
            "天干阴阳表未覆盖十天干",
            f"missing={sorted(TIANGAN_ORDER - set(GAN_YINYANG))} extra={sorted(set(GAN_YINYANG) - TIANGAN_ORDER)}",
        ))
    if set(DIZHI_HIDDEN_STEMS) != VALID_DIZHI:
        issues.append(_issue(
            "error",
            "八字",
            "藏干表未覆盖十二地支",
            f"missing={sorted(VALID_DIZHI - set(DIZHI_HIDDEN_STEMS))} extra={sorted(set(DIZHI_HIDDEN_STEMS) - VALID_DIZHI)}",
        ))
    for dizhi, hidden_stems in DIZHI_HIDDEN_STEMS.items():
        weight_sum = round(sum(weight for _, weight in hidden_stems), 2)
        if weight_sum != 1.0:
            issues.append(_issue("warning", "八字", f"{dizhi}藏干权重合计不是1.0", str(weight_sum)))
        for stem, weight in hidden_stems:
            if stem not in TIANGAN_ORDER:
                issues.append(_issue("error", "八字", f"{dizhi}藏干出现未知天干", stem))
            if weight <= 0:
                issues.append(_issue("error", "八字", f"{dizhi}藏干权重必须为正", f"{stem}:{weight}"))

    expected_samples = {
        ("甲", "甲"): "比肩",
        ("甲", "乙"): "劫财",
        ("甲", "癸"): "正印",
        ("甲", "壬"): "偏印",
        ("甲", "丙"): "食神",
        ("甲", "丁"): "伤官",
        ("甲", "己"): "正财",
        ("甲", "戊"): "偏财",
        ("甲", "辛"): "正官",
        ("甲", "庚"): "七杀",
    }
    for args, expected in expected_samples.items():
        actual = get_ten_god(*args)
        if actual != expected:
            issues.append(_issue("error", "八字", "十神样例计算错误", f"{args}: actual={actual} expected={expected}"))

    for god, group in TEN_GOD_GROUP.items():
        if group not in {"印", "食伤", "官杀", "财", "比劫"}:
            issues.append(_issue("error", "八字", f"{god} 十神分组非法", group))

    try:
        result = analyze_bazi_birth("1990-01-01", 8, 30, "男")
        if len(result.get("pillars", [])) != 4 or len(result.get("bazi", "").split()) != 4:
            issues.append(_issue("error", "八字", "八字样例未生成四柱", str(result.get("bazi"))))
        if len(result.get("luck_cycles", {}).get("cycles", [])) < 8:
            issues.append(_issue("error", "八字", "八字样例未生成完整大运列表"))
        if not result.get("current_year", {}).get("ganzhi"):
            issues.append(_issue("error", "八字", "八字样例未生成当前流年"))
        if len(result.get("hour_candidates", {}).get("candidates", [])) != 3:
            issues.append(_issue("error", "八字", "八字样例未生成三组临界时辰候选"))
        useful = result.get("useful_profile", {})
        if "group_scores" not in useful or not useful.get("principle"):
            issues.append(_issue("error", "八字", "八字样例未生成喜忌取向"))
        timing = result.get("current_timing_analysis", {})
        if "combined_score" not in timing or not timing.get("summary"):
            issues.append(_issue("error", "八字", "八字样例未生成岁运同参"))
    except Exception as exc:
        issues.append(_issue("error", "八字", "八字样例分析失败", str(exc)))

    return issues


def audit_qimen_rules():
    """校验奇门运筹基础表和样例起局。"""
    issues = []
    valid_elements = {"木", "火", "土", "金", "水"}

    if len(QIMEN_PALACES) != 9:
        issues.append(_issue("error", "奇门", "九宫表数量不是 9", str(len(QIMEN_PALACES))))
    palace_keys = [item.get("key") for item in QIMEN_PALACES]
    if len(set(palace_keys)) != len(palace_keys):
        issues.append(_issue("error", "奇门", "九宫 key 存在重复", str(palace_keys)))
    if set(OUTER_PALACE_KEYS) != (set(palace_keys) - {"center"}):
        issues.append(_issue(
            "error",
            "奇门",
            "外八宫 key 与九宫表不一致",
            f"outer={OUTER_PALACE_KEYS} palaces={palace_keys}",
        ))

    for palace in QIMEN_PALACES:
        if palace.get("element") not in valid_elements:
            issues.append(_issue("error", "奇门", f"{palace.get('name')} 五行非法", palace.get("element", "")))
        if palace.get("key") != "center" and not palace.get("direction"):
            issues.append(_issue("error", "奇门", f"{palace.get('name')} 缺少方位"))

    if len(EIGHT_DOORS) != 8:
        issues.append(_issue("error", "奇门", "八门数量不是 8", str(len(EIGHT_DOORS))))
    for door, data in EIGHT_DOORS.items():
        if data.get("element") not in valid_elements:
            issues.append(_issue("error", "奇门", f"{door}门五行非法", data.get("element", "")))
        if "score" not in data or "strategy" not in data:
            issues.append(_issue("error", "奇门", f"{door}门缺少评分或策略"))

    if len(NINE_STARS) != 9:
        issues.append(_issue("error", "奇门", "九星数量不是 9", str(len(NINE_STARS))))
    if "天禽" not in NINE_STARS:
        issues.append(_issue("error", "奇门", "九星缺少中宫天禽"))
    for star, data in NINE_STARS.items():
        if data.get("element") not in valid_elements:
            issues.append(_issue("error", "奇门", f"{star}五行非法", data.get("element", "")))

    if len(EIGHT_GODS) != 8:
        issues.append(_issue("error", "奇门", "八神数量不是 8", str(len(EIGHT_GODS))))
    if len(set(QIMEN_STEM_ORDER)) != 9 or set(QIMEN_STEM_ORDER) != set(THREE_QI + SIX_YI):
        issues.append(_issue("error", "奇门", "三奇六仪顺序未覆盖 9 个天干", str(QIMEN_STEM_ORDER)))

    expected_xunshou = {"甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅"}
    if set(SIX_JIA_DUN) != expected_xunshou:
        issues.append(_issue(
            "error",
            "奇门",
            "六甲遁仪表未覆盖六个旬首",
            f"missing={sorted(expected_xunshou - set(SIX_JIA_DUN))} extra={sorted(set(SIX_JIA_DUN) - expected_xunshou)}",
        ))
    if set(SIX_YI_TO_HIDDEN_JIA) != set(SIX_YI):
        issues.append(_issue("error", "奇门", "六仪反查藏甲未覆盖六仪", str(SIX_YI_TO_HIDDEN_JIA)))
    for xunshou, data in SIX_JIA_DUN.items():
        instrument = data.get("instrument")
        if instrument not in SIX_YI:
            issues.append(_issue("error", "奇门", f"{xunshou}遁入未知六仪", str(instrument)))
        if SIX_YI_TO_HIDDEN_JIA.get(instrument) != xunshou:
            issues.append(_issue("error", "奇门", f"{xunshou}六仪反查不一致", str(instrument)))
        stem_data = QIMEN_STEM_MEANING.get(instrument, {})
        if stem_data.get("hidden_jia") != xunshou:
            issues.append(_issue("error", "奇门", f"{instrument}的 hidden_jia 与六甲遁仪表不一致", str(stem_data)))
    for stem in THREE_QI:
        if QIMEN_STEM_MEANING.get(stem, {}).get("hidden_jia"):
            issues.append(_issue("error", "奇门", f"{stem}为三奇，不应藏甲", str(QIMEN_STEM_MEANING.get(stem))))

    for key, rule in QIMEN_SCENARIO_RULES.items():
        for field in ("name", "prefer_doors", "avoid_doors", "prefer_stars", "avoid_stars", "prefer_gods", "avoid_gods", "action"):
            if field not in rule:
                issues.append(_issue("error", "奇门", f"{key} 场景规则缺少字段 {field}"))
        for door in rule.get("prefer_doors", []) + rule.get("avoid_doors", []):
            if door not in EIGHT_DOORS:
                issues.append(_issue("error", "奇门", f"{key} 场景引用未知八门", door))
        for star in rule.get("prefer_stars", []) + rule.get("avoid_stars", []):
            if star not in NINE_STARS:
                issues.append(_issue("error", "奇门", f"{key} 场景引用未知九星", star))
        for god in rule.get("prefer_gods", []) + rule.get("avoid_gods", []):
            if god not in EIGHT_GODS:
                issues.append(_issue("error", "奇门", f"{key} 场景引用未知八神", god))

    try:
        result = analyze_qimen(
            topic="明天谈判从哪个方位切入更有利",
            direction="东南",
            current=datetime.datetime(2026, 7, 5, 15, 30),
        )
        if len(result.get("board", [])) != 9:
            issues.append(_issue("error", "奇门", "样例起局未生成九宫盘"))
        if len(result.get("best_palaces", [])) != 3 or len(result.get("avoid_palaces", [])) != 3:
            issues.append(_issue("error", "奇门", "样例起局未生成推荐/慎用方位"))
        if result.get("scenario", {}).get("key") != "negotiation":
            issues.append(_issue("error", "奇门", "样例谈判场景识别错误", str(result.get("scenario"))))
        if "风后奇门" not in result.get("fenghou_boundary", ""):
            issues.append(_issue("error", "奇门", "样例结果缺少风后奇门边界声明"))
        dunjia = result.get("dunjia_profile", {})
        if not dunjia.get("xunshou") or not dunjia.get("commander_palace"):
            issues.append(_issue("error", "奇门", "样例结果缺少遁甲旬首或藏甲宫", str(dunjia)))
        if not dunjia.get("geng_palace") or len(dunjia.get("three_qi_palaces", [])) != 3:
            issues.append(_issue("error", "奇门", "样例结果缺少庚方或三奇护局", str(dunjia)))
        if not any("遁甲" in line for line in result.get("operation_logic", [])):
            issues.append(_issue("error", "奇门", "样例结果缺少遁甲运筹逻辑"))
        zhifu = result.get("zhifu_zhishi", {})
        if not zhifu.get("zhi_fu_star") or not zhifu.get("zhi_shi_door"):
            issues.append(_issue("error", "奇门", "样例结果缺少值符值使参照", str(zhifu)))
        three_qi = result.get("three_qi_analysis", {})
        if len(three_qi.get("items", [])) != 3 or not three_qi.get("best"):
            issues.append(_issue("error", "奇门", "样例结果缺少三奇助力分析", str(three_qi)))
        geng_risk = result.get("geng_risk", {})
        if not geng_risk.get("level") or "summary" not in geng_risk:
            issues.append(_issue("error", "奇门", "样例结果缺少庚格风险分析", str(geng_risk)))
        pattern = result.get("pattern_diagnostics", {})
        required_pattern_counts = {"favorable_doors", "hard_doors", "empty_palaces", "fu_yin", "fan_yin", "aligned_good", "hard_combos"}
        if not pattern.get("name") or not pattern.get("summary") or not pattern.get("boundary"):
            issues.append(_issue("error", "奇门", "样例结果缺少格局诊断摘要或边界", str(pattern)))
        if set(pattern.get("counts", {})) != required_pattern_counts:
            issues.append(_issue("error", "奇门", "样例结果格局诊断计数字段不完整", str(pattern.get("counts"))))
        posture = result.get("tactical_posture", {})
        if not posture.get("name") or not posture.get("summary"):
            issues.append(_issue("error", "奇门", "样例结果缺少主客态势分析", str(posture)))
        host_guest_matrix = result.get("host_guest_matrix", {})
        role_names = {item.get("role") for item in host_guest_matrix.get("roles", [])}
        required_roles = {"主位承接", "客压识别", "转化铺垫", "禁区止损"}
        if not host_guest_matrix.get("summary") or not host_guest_matrix.get("scenario_tactic"):
            issues.append(_issue("error", "奇门", "样例结果缺少主客攻守矩阵摘要或场景打法", str(host_guest_matrix)))
        if not required_roles.issubset(role_names):
            issues.append(_issue("error", "奇门", "样例结果主客攻守矩阵角色不完整", str(role_names)))
        action_plan = result.get("action_plan", {})
        if not action_plan.get("go_signal") or len(action_plan.get("phases", [])) < 4:
            issues.append(_issue("error", "奇门", "样例结果缺少可执行行动方案", str(action_plan)))
        guardrails = result.get("execution_guardrails", {})
        if not guardrails.get("level") or not guardrails.get("mode") or not guardrails.get("summary"):
            issues.append(_issue("error", "奇门", "样例结果缺少执行闸门摘要", str(guardrails)))
        for field in ("must_verify", "go_conditions", "stop_conditions", "fallback_steps"):
            if len(guardrails.get(field, [])) < 2:
                issues.append(_issue("error", "奇门", f"样例结果执行闸门字段不足：{field}", str(guardrails.get(field))))
        timing_windows = result.get("timing_windows", {})
        if len(timing_windows.get("items", [])) != 3 or not timing_windows.get("best"):
            issues.append(_issue("error", "奇门", "样例结果缺少三时辰时机窗口", str(timing_windows)))
        if not timing_windows.get("summary") or not timing_windows.get("ranked"):
            issues.append(_issue("error", "奇门", "样例结果缺少时机窗口摘要或排序", str(timing_windows)))
        integrated = result.get("integrated_decision", {})
        if not integrated.get("final_signal") or not integrated.get("priority") or not integrated.get("summary"):
            issues.append(_issue("error", "奇门", "样例结果缺少综合裁决摘要", str(integrated)))
        if not integrated.get("primary_direction") or "综合裁决" not in integrated.get("summary", ""):
            issues.append(_issue("error", "奇门", "样例结果综合裁决缺少主位或摘要标识", str(integrated)))
        confidence = result.get("confidence_profile", {})
        if not isinstance(confidence.get("score"), int) or not (0 <= confidence.get("score", -1) <= 100):
            issues.append(_issue("error", "奇门", "样例结果置信度分数非法", str(confidence)))
        if not confidence.get("level") or not confidence.get("summary") or not confidence.get("boundary"):
            issues.append(_issue("error", "奇门", "样例结果缺少置信度摘要或边界", str(confidence)))
        if not confidence.get("reasons") or not confidence.get("improve"):
            issues.append(_issue("error", "奇门", "样例结果置信度缺少支撑因素或提纯路径", str(confidence)))
    except Exception as exc:
        issues.append(_issue("error", "奇门", "样例起局失败", str(exc)))

    return issues


def run_rule_audit():
    """运行完整规则审计。"""
    checks = [
        ("凝神入口", audit_focus_seed_wiring),
        ("Web 请求", audit_web_request_wiring),
        ("历史记录", audit_history_wiring),
        ("姓名笔画", audit_name_stroke_data),
        ("八宫矩阵", audit_palace_hexagram_matrix),
        ("世应规则", audit_shi_ying_rules),
        ("纳甲规则", audit_najia_rules),
        ("六神规则", audit_liushen_rules),
        ("六十四卦象义校准", audit_hexagram_calibration),
        ("起卦法选择器", audit_method_selector_profiles),
        ("八字规则", audit_bazi_rules),
        ("奇门规则", audit_qimen_rules),
    ]
    issues = []
    for _, check in checks:
        issues.extend(check())

    error_count = sum(1 for item in issues if item["level"] == "error")
    warning_count = sum(1 for item in issues if item["level"] == "warning")
    return {
        "passed": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "issue_count": len(issues),
        "issues": issues,
    }


def format_rule_audit_report(audit_result=None):
    """格式化审计报告，适合 CLI 或维护日志输出。"""
    result = audit_result or run_rule_audit()
    status = "通过" if result["passed"] else "未通过"
    lines = [
        f"规则审计：{status}",
        f"错误：{result['error_count']}；警告：{result['warning_count']}",
    ]
    if not result["issues"]:
        lines.append("凝神入口、Web 请求、历史记录、姓名笔画、纳甲、世应、八宫、六十四卦象义校准、八字规则、奇门规则、多选最优和起卦法选择器配置均已通过一致性校验。")
        return "\n".join(lines)

    for issue in result["issues"]:
        detail = f"｜{issue['detail']}" if issue.get("detail") else ""
        lines.append(f"[{issue['level']}] {issue['area']}：{issue['message']}{detail}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_rule_audit_report())
