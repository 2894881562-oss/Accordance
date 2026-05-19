# -*- coding: utf-8 -*-
"""
问题历史追踪模块

基于蒙卦"初筮告，再三渎，渎则不告"的术数原则：
1. 同一会话/跨会话检测重复或高度相似问题
2. 中文语义级相似度（二元Jaccard + 核心词 + 同义词扩展）
3. 基于真实时间跨度的分级拦截（7天/15天/节气）
4. JSON 文件持久化，关程序重开仍然有效
"""

import time
import re
import os
import json
import datetime


# ═══════════════════════════════════════════════════════════
# 1. 持久化路径
# ═══════════════════════════════════════════════════════════

def _data_dir():
    """确保 .data 目录存在并返回路径。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, ".data")
    os.makedirs(path, exist_ok=True)
    return path


HISTORY_FILE = os.path.join(_data_dir(), "question_history.json")


# ═══════════════════════════════════════════════════════════
# 2. 中文同义/近义词映射（核心词级别）
# ═══════════════════════════════════════════════════════════

SYNONYM_GROUPS = [
    # 财运类
    ["钱", "财", "收入", "工资", "奖金", "赚钱", "发财", "盈利", "收益", "进账", "薪", "俸", "利", "挣", "赚", "富裕"],
    ["投资", "股票", "基金", "理财", "买房", "购房", "置业", "投钱", "投机", "炒", "入市"],
    ["破财", "亏", "赔", "损财", "失财", "漏财", "花销", "开销", "花费", "支出", "破费"],
    # 事业类
    ["工作", "事业", "职业", "职位", "岗位", "就业", "上班", "打工", "前程", "前途", "仕途"],
    ["跳槽", "换工作", "辞职", "离职", "转行", "换岗", "换公司", "挪窝", "走人", "离职"],
    ["升职", "晋升", "提拔", "升官", "升级", "升迁", "高升", "上位", "加官"],
    ["求职", "找工作", "面试", "应聘", "投简历", "入职", "报到"],
    ["领导", "上级", "老板", "上司", "主管", "长官", "头儿", "总监", "经理"],
    # 感情类
    ["感情", "恋爱", "爱情", "情感", "恋情", "姻缘", "桃花", "男女"],
    ["婚姻", "结婚", "成家", "嫁", "娶", "婚嫁", "婚事", "联姻", "终身大事"],
    ["分手", "离婚", "分开", "散伙", "离异", "一拍两散", "掰了", "断了"],
    ["复合", "和好", "重修", "挽回", "破镜重圆", "回心转意", "回头"],
    ["对象", "伴侣", "男朋友", "女朋友", "恋人", "情人", "配偶", "另一半", "爱人"],
    # 学业类
    ["考试", "考", "应试", "高考", "考研", "考证", "笔试", "科考", "应考", "备考"],
    ["学业", "学习", "读书", "念书", "功课", "成绩", "学分", "升学"],
    ["文书", "合同", "证件", "证书", "文件", "材料", "契约", "协议", "手续"],
    # 健康类
    ["病", "疾病", "健康", "身体", "患", "恙", "疾", "症", "痛", "不舒服", "住院", "看病"],
    ["治疗", "就医", "求医", "看病", "问诊", "吃药", "手术", "康复", "痊愈"],
    # 决疑类
    ["要不要", "该不该", "能不能", "可不可以", "是否", "值不值得", "合适不", "行不行", "好不好"],
    ["选择", "二选一", "抉择", "取舍", "选哪个", "哪个好", "比较", "对比", "权衡"],
    ["发展", "前景", "未来", "趋势", "走向", "前景如何", "趋势如何", "运势"],
    ["运势", "运气", "运程", "气运", "命途", "时运", "流年", "整体"],
    # 寻物类
    ["丢", "失物", "找", "遗失", "丢失", "掉了", "不见了", "失踪", "下落"],
]

# 构建双向映射：词 → 所属同义组索引
_WORD_TO_GROUP = {}
for _gid, _group in enumerate(SYNONYM_GROUPS):
    for _word in _group:
        _WORD_TO_GROUP[_word] = _gid


def _expand_with_synonyms(text):
    """
    将文本中的词用其同义词组的代表词替换。
    替换后同一语义的不同表述趋向同一文本。
    """
    result = text
    # 按词长降序替换，避免短词误替长词
    sorted_words = sorted(_WORD_TO_GROUP.keys(), key=len, reverse=True)
    for word in sorted_words:
        if word in result:
            rep = SYNONYM_GROUPS[_WORD_TO_GROUP[word]][0]
            result = result.replace(word, f"「{rep}」")
    return result


# ═══════════════════════════════════════════════════════════
# 3. 核心词抽取
# ═══════════════════════════════════════════════════════════

# 高频虚词/停用词（在疑问句中无实质信息的字）
STOP_CHARS = set(
    "的了吗呢吧啊呀嗯哎哦哈呐哇嘿嗨呵嘛啦咧哟"
    "我你他她它我们你们他们她们自己"
    "一个这次现在最近目前当前"
    "什么怎么为什为啥什么样什么样什么情况"
    "请问想问问一下有没有是不是可以吗"
    "大概大约大概也许可能或许恐怕"
    "所以因为但是不过虽然然后"
    "很非常真太极比较最更"
    "来去上去想到给用把被让叫"
    "这那是哪会就都也还再又只"
    "之乎者也矣焉哉"
)


def _extract_core_words(text):
    """
    从问题文本中提取核心实质词，过滤虚词和疑问语气词。
    返回核心词列表（有序）。
    """
    words = []
    for ch in text:
        if ch not in STOP_CHARS and ord(ch) > 127:
            words.append(ch)
    # 合并连续字为词（简单策略：2-4字为一词）
    result = []
    i = 0
    while i < len(words):
        # 尝试取2-3字词
        for wlen in (3, 2, 1):
            if i + wlen <= len(words):
                result.append("".join(words[i:i + wlen]))
        i += max(1, min(3, len(words) - i - 1))
    return result


# ═══════════════════════════════════════════════════════════
# 4. 相似度计算
# ═══════════════════════════════════════════════════════════

def _normalize(text):
    """去空格、去标点、统一小写，保留中文核心内容。"""
    text = text.strip()
    text = re.sub(
        r'[\s,，。！？、；：""''（）\(\)\[\]【】\?\!\.;:\'"\-—…～~`·]+',
        '',
        text,
    )
    return text.lower()


def _char_bigrams(text):
    """生成字符级二元组集合。"""
    chars = list(text)
    if len(chars) < 2:
        return set(chars)
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def _jaccard(set1, set2):
    """Jaccard 相似系数。"""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _question_similarity(text1, text2):
    """
    计算两个问题文本的语义相似度，综合五种策略：

    1. 完全一致 → 1.0
    2. 子串包含 → 0.85
    3. 同义词归一后二元 Jaccard → 实际值 × 1.3（加权）
    4. 核心词重叠率 → 实际值
    5. 原始二元 Jaccard → 兜底

    返回 0.0~1.0 的综合相似度。
    """
    n1 = _normalize(text1)
    n2 = _normalize(text2)

    if not n1 or not n2:
        return 0.0

    # 策略1：完全一致
    if n1 == n2:
        return 1.0

    # 策略2：子串包含
    if len(n1) >= 4 and len(n2) >= 4:
        if n1 in n2 or n2 in n1:
            return 0.85

    # 策略3：同义词归一化后的二元 Jaccard（权重最高）
    syn1 = _expand_with_synonyms(n1)
    syn2 = _expand_with_synonyms(n2)
    syn_bg1 = _char_bigrams(syn1)
    syn_bg2 = _char_bigrams(syn2)
    syn_score = _jaccard(syn_bg1, syn_bg2) * 1.3

    # 策略4：核心词重叠率
    cw1 = set(_extract_core_words(n1))
    cw2 = set(_extract_core_words(n2))
    core_score = _jaccard(cw1, cw2) if cw1 and cw2 else 0.0

    # 策略5：原始二元 Jaccard（兜底）
    bg1 = _char_bigrams(n1)
    bg2 = _char_bigrams(n2)
    raw_score = _jaccard(bg1, bg2)

    # 综合：取加权最大值
    final = max(
        syn_score,
        core_score * 0.95,
        raw_score * 0.7,
    )

    return min(1.0, final)


# ═══════════════════════════════════════════════════════════
# 5. 节气近似日期（用于时间间隔判断）
# ═══════════════════════════════════════════════════════════

# 2026年近似节气日（±1天精度）
JIEQI_DATES_2026 = [
    (1, 5, "小寒"), (1, 20, "大寒"),
    (2, 4, "立春"), (2, 19, "雨水"),
    (3, 5, "惊蛰"), (3, 20, "春分"),
    (4, 5, "清明"), (4, 20, "谷雨"),
    (5, 5, "立夏"), (5, 21, "小满"),
    (6, 5, "芒种"), (6, 21, "夏至"),
    (7, 7, "小暑"), (7, 22, "大暑"),
    (8, 7, "立秋"), (8, 23, "处暑"),
    (9, 7, "白露"), (9, 23, "秋分"),
    (10, 8, "寒露"), (10, 23, "霜降"),
    (11, 7, "立冬"), (11, 22, "小雪"),
    (12, 7, "大雪"), (12, 22, "冬至"),
]

# 未来年份的节气估算（使用天文算法简化推延，每年偏移约5h49m即0.2422天）
# 此处使用每年 +0.2422 天的简化推延


def _days_since_jieqi(target_date):
    """计算目标日期距离最近已过节气有多少天。"""
    year = target_date.year
    # 找当年已过节气
    passed = []
    for (m, d, name) in JIEQI_DATES_2026:
        # 简化：仅对2026年精确，其余年份用偏移近似
        year_offset = (year - 2026) * 0.2422
        jd = datetime.date(year, m, d) + datetime.timedelta(days=year_offset)
        if jd <= target_date:
            passed.append((jd, name))
    if not passed:
        return 365, "未知"
    last = max(passed, key=lambda x: x[0])
    return (target_date - last[0]).days, last[1]


# ═══════════════════════════════════════════════════════════
# 6. 时间规则定义
# ═══════════════════════════════════════════════════════════

# 时间规则（按重复间隔分级）
TIME_RULES = {
    "block": {
        "days": 7,
        "name": "七日来复",
        "source": "复卦：反复其道，七日来复",
        "action": "拦截",
        "msg": "同一问题在7天内重复起卦，卦气未换，心念未新，强烈建议等待。",
    },
    "warn": {
        "days": 15,
        "name": "一节气",
        "source": "节气轮转，气机已换",
        "action": "警告",
        "msg": "间隔超过7天但不足一节气（约15天），气机初换，勉强可问，但结果参考价值仍有限。",
    },
    "allow": {
        "days": 99999,
        "name": "完全放行",
        "source": "时间充足，视为新问",
        "action": "放行",
        "msg": "",
    },
}


def _classify_time_interval(days):
    """根据天数间隔返回时间规则分类。"""
    if days < TIME_RULES["block"]["days"]:
        return "block"
    elif days < TIME_RULES["warn"]["days"]:
        return "warn"
    else:
        return "allow"


# ═══════════════════════════════════════════════════════════
# 7. 持久化问题历史
# ═══════════════════════════════════════════════════════════

class QuestionHistory:
    """
    跨会话持久化的问题历史。

    存储位置：.data/question_history.json
    自动从文件加载，每次记录后自动保存。
    """

    def __init__(self, similarity_threshold=0.58):
        self._threshold = similarity_threshold
        self._history = []
        self._loaded = False

    def _ensure_loaded(self):
        """惰性加载历史文件。"""
        if self._loaded:
            return
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, list):
                    self._history = raw
        except (json.JSONDecodeError, IOError, OSError):
            self._history = []
        self._loaded = True

    def _save(self):
        """保存到磁盘。"""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except (IOError, OSError):
            pass

    def check_duplicate(self, question, module_name):
        """
        检查当前问题是否与历史记录重复/高度相似。

        返回 (is_duplicate, matched_entry_or_None, similarity_score, time_category)
        """
        self._ensure_loaded()
        best_match = None
        best_score = 0.0

        for entry in self._history:
            sim = _question_similarity(question, entry.get("question", ""))
            if sim > best_score:
                best_score = sim
                best_match = entry

        if best_score >= self._threshold and best_match:
            # 计算时间间隔
            prev_ts = best_match.get("timestamp", 0)
            now_ts = time.time()
            days_elapsed = (now_ts - prev_ts) / 86400.0
            time_cat = _classify_time_interval(days_elapsed)
            return True, best_match, round(best_score, 2), time_cat, round(days_elapsed, 1)

        return False, None, 0.0, "", 0.0

    def add_question(self, question, module_name, result_summary):
        """记录一次起卦并持久化。"""
        self._ensure_loaded()
        entry = {
            "question": question,
            "module": module_name,
            "timestamp": time.time(),
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result_summary": result_summary,
        }
        self._history.append(entry)
        # 保留最近200条，防止文件无限膨胀
        if len(self._history) > 200:
            self._history = self._history[-200:]
        self._save()

    def get_recent(self, n=5):
        """获取最近 n 条记录（最近的在前面）。"""
        self._ensure_loaded()
        return list(reversed(self._history[-n:]))

    def clear(self):
        """清空历史。"""
        self._history = []
        self._save()

    def stats(self):
        """返回历史统计信息。"""
        self._ensure_loaded()
        return {
            "total_questions": len(self._history),
            "oldest": self._history[0]["datetime"] if self._history else "",
            "newest": self._history[-1]["datetime"] if self._history else "",
            "file": HISTORY_FILE,
        }


# ═══════════════════════════════════════════════════════════
# 8. 全局单例
# ═══════════════════════════════════════════════════════════

_session_history = QuestionHistory()


def get_session_history():
    return _session_history


# ═══════════════════════════════════════════════════════════
# 9. 模块集成入口
# ═══════════════════════════════════════════════════════════

def _sep():
    return "=" * 70


def handle_duplicate_check(question, module_label):
    """
    在起卦前调用，检查重复问题并分级处理。

    分级逻辑：
    - 相似度 ≥ 阈值 且 间隔 < 7天  → 拦截（展示蒙卦警告 + 时间规则）
    - 相似度 ≥ 阈值 且 7天 ≤ 间隔 < 15天 → 警告但可坚持
    - 相似度 ≥ 阈值 且 间隔 ≥ 15天 → 放行（仅提示）
    - 相似度 < 阈值 → 正常放行

    返回:
        (should_proceed, question)
    """
    history = get_session_history()
    is_dup, matched, sim_score, time_cat, days_ago = history.check_duplicate(
        question, module_label
    )

    if not is_dup:
        return True, question

    # ── 时间分级处理 ──
    now = datetime.datetime.now()
    prev_dt = matched.get("datetime", "未知时间")

    if time_cat == "allow":
        # 超过15天，仅轻提示
        print()
        print(_sep())
        print(f"  您约{days_ago:.0f}天前（{prev_dt}）问过相似问题：")
        print(f"    「{matched['question']}」")
        print(f"  间隔已超过一节气，气机已换，视为新问。")
        print(_sep())
        return True, question

    # ── block 或 warn：展示蒙卦警告 ──
    print()
    print(_sep())
    print("【术数规则提醒 —— 《周易·蒙卦第四》】")
    print()
    print("  「初筮告，再三渎，渎则不告。」")
    print("  —— 卦辞原文")
    print()
    print("  第一次占筮，天机相应，结果可告；")
    print("  再次、三次追问同一事，是为亵渎；")
    print("  亵渎之后，天机不示，卦不告也。")
    print()
    print(f"  您当前的问题与此前已问过的问题高度相似：")
    print(f"    此前问题：{matched['question']}")
    print(f"    此前时间：{prev_dt}（约{days_ago:.0f}天前）")
    print(f"    此前方式：{matched.get('module', '未知')}")
    print(f"    此前结果：{matched.get('result_summary', '无记录')}")
    print(f"    相似度：{sim_score:.0%}")
    print()
    print(f"  ── 时间规则判定 ──")

    _, nearest_jieqi = _days_since_jieqi(now.date())
    next_jieqi_info = f"，距最近节气「{nearest_jieqi}」后约{_days_since_jieqi(now.date())[0]}天"

    if time_cat == "block":
        rule = TIME_RULES["block"]
        print(f"  间隔 {days_ago:.0f} 天 < {rule['days']} 天：触发「{rule['name']}」拦截")
        print(f"  出处：{rule['source']}")
        print(f"  {rule['msg']}")
        print(f"  建议：再等约 {rule['days'] - days_ago:.0f} 天后再问{next_jieqi_info}")
    else:
        rule = TIME_RULES["warn"]
        print(f"  {rule['days']} 天 > 间隔 {days_ago:.0f} 天 ≥ {TIME_RULES['block']['days']} 天：触发「{rule['name']}」警告")
        print(f"  出处：{rule['source']}")
        print(f"  {rule['msg']}")

    print()
    print("  按照传统术数规则，同一问题不宜反复起卦：")
    print("    1. 心念已散，气机不纯，后续卦象参考价值大幅降低")
    print("    2. 若因对前次结果不满意而重问，属于「渎」，卦不告也")
    print("    3. 若确有新情况、时隔较久、或换角度切入，可视为新问")
    print()
    print("  ── 何时可以重新起卦？──")
    print("    过一节气（约15天）后  —— 节气轮转，气机已换，可视为新问")
    print("    过一旬（10天）后        —— 旬空轮转，干支已变，勉强可重问")
    print("    至少间隔 7 天           —— 部分流派的最短间隔底线")
    print("    事态有实质变化时        —— 如结果已定、条件改变、人事变动")
    print("    换一种起卦方式          —— 如六爻改为三爻，或改用姓名起卦")
    print(_sep())

    while True:
        print()
        if time_cat == "block":
            print("  请选择：")
            print("    [1] 坚持重起（强烈不推荐）")
            print("    [2] 换个问法")
            print("    [3] 返回主菜单")
            choice = input("  → ").strip()
        else:
            print("  请选择：")
            print("    [1] 继续起卦（风险自担）")
            print("    [2] 换个问法")
            print("    [3] 返回主菜单")
            choice = input("  → ").strip()

        if choice == "1":
            if time_cat == "block":
                print()
                print("  已为您重新起卦。但需知：")
                print(f"  距上次仅{days_ago:.0f}天，不足7日，卦气未换。")
                print("  此卦象的参考价值可能大幅降低，请以初次结果为准。")
                print()
            else:
                print()
                print("  已为您重新起卦。气机初换，但间隔有限，结果仅供参考。")
                print()
            return True, question

        elif choice == "2":
            new_question = input("  请输入新的问题表述：").strip()
            if not new_question:
                print("  问题不能为空。")
                continue
            return handle_duplicate_check(new_question, module_label)

        elif choice == "3":
            return False, question

        else:
            print("  输入有误，请重新选择。")


def record_question(question, module_label, result_summary):
    """起卦完成后调用，记录到历史并持久化。"""
    get_session_history().add_question(question, module_label, result_summary)


def show_history():
    """在菜单层展示最近的起卦历史。"""
    history = get_session_history()
    recent = history.get_recent(5)
    if not recent:
        print("暂无起卦记录。")
        return

    stats = history.stats()
    print()
    print(_sep())
    print(f"【近期起卦记录】（共 {stats['total_questions']} 条，存于 {stats['file']}）")
    for i, entry in enumerate(recent, 1):
        dt = entry.get("datetime", "未知时间")
        print(f"  {i}. [{entry['module']}] {entry['question']}")
        print(f"     └ {dt}  → {entry['result_summary']}")
    print(_sep())
