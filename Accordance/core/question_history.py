# -*- coding: utf-8 -*-
"""
问题历史追踪模块

基于蒙卦"初筮告，再三渎，渎则不告"的术数原则，
在同一会话中检测重复或高度相似的问题，防止亵渎式重复起卦。
"""

import time
import re


# ── 文本标准化 ──

def _normalize(text):
    """去空格、去标点、统一小写，保留中文核心内容。"""
    text = text.strip()
    text = re.sub(
        r'[\s,，。！？、；：""''（）\(\)\[\]【】\?\!\.;:\'"\-—…～~`·]+',
        '',
        text,
    )
    return text.lower()


# ── 相似度计算 ──

def _char_bigrams(text):
    """生成字符级二元组集合，用于中文文本相似度计算。"""
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
    计算两个问题文本的相似度，综合三种策略：
    1. 完全一致 → 1.0
    2. 子串包含 → 0.85
    3. 二元组 Jaccard → 实际值
    """
    n1 = _normalize(text1)
    n2 = _normalize(text2)

    if not n1 or not n2:
        return 0.0

    # 完全一致
    if n1 == n2:
        return 1.0

    # 子串包含（短文本在长文本中）
    if len(n1) >= 4 and len(n2) >= 4:
        if n1 in n2 or n2 in n1:
            return 0.85

    # 二元组 Jaccard
    bg1 = _char_bigrams(n1)
    bg2 = _char_bigrams(n2)
    return _jaccard(bg1, bg2)


# ── 问题历史 ──

class QuestionHistory:
    """会话级问题历史，防止同一问题反复占问。"""

    def __init__(self, similarity_threshold=0.65):
        self._history = []
        self._threshold = similarity_threshold

    def check_duplicate(self, question, module_name):
        """
        检查当前问题是否与历史记录重复/高度相似。

        返回 (is_duplicate, matched_entry_or_None)
        """
        for entry in self._history:
            sim = _question_similarity(question, entry["question"])
            if sim >= self._threshold:
                return True, entry
        return False, None

    def add_question(self, question, module_name, result_summary):
        """记录一次起卦。"""
        self._history.append({
            "question": question,
            "module": module_name,
            "timestamp": time.time(),
            "result_summary": result_summary,
        })

    def get_recent(self, n=5):
        """获取最近 n 条记录（最近的在前面）。"""
        return list(reversed(self._history[-n:]))

    def clear(self):
        """清空历史。"""
        self._history.clear()


# ── 全局单例 ──

_session_history = QuestionHistory()


def get_session_history():
    return _session_history


# ── 模块集成入口 ──

def _sep():
    return "=" * 70


def handle_duplicate_check(question, module_label):
    """
    在起卦前调用，检查重复问题并处理用户交互。

    参数:
        question: 用户输入的问题文本
        module_label: 模块中文名（如"六爻详占"），用于展示

    返回:
        (should_proceed, question)
        - should_proceed=True  → 可继续起卦
        - should_proceed=False → 用户选择返回
    """
    history = get_session_history()
    is_dup, matched = history.check_duplicate(question, module_label)

    if not is_dup:
        return True, question

    # ── 展示蒙卦警告 ──
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
    print(f"    此前方式：{matched['module']}")
    print(f"    此前结果：{matched['result_summary']}")
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
        choice = input("请选择：[1] 坚持重起（不推荐） [2] 换个问法 [3] 返回主菜单：").strip()

        if choice == "1":
            print()
            print("已为您重新起卦。但需知：此卦象的参考价值可能已降低，请以初次结果为准。")
            print()
            return True, question

        elif choice == "2":
            new_question = input("请输入新的问题表述：").strip()
            if not new_question:
                print("问题不能为空。")
                continue
            # 递归检查新问题
            return handle_duplicate_check(new_question, module_label)

        elif choice == "3":
            return False, question

        else:
            print("输入有误，请重新选择。")


def record_question(question, module_label, result_summary):
    """起卦完成后调用，记录到历史。"""
    get_session_history().add_question(question, module_label, result_summary)


def show_history():
    """在菜单层展示最近的起卦历史。"""
    history = get_session_history()
    recent = history.get_recent(5)
    if not recent:
        print("暂无起卦记录。")
        return

    print()
    print(_sep())
    print("【近期起卦记录】")
    for i, entry in enumerate(recent, 1):
        print(f"  {i}. [{entry['module']}] {entry['question']}")
        print(f"     → {entry['result_summary']}")
    print(_sep())
