# -*- coding: utf-8 -*-
"""
起卦气机上下文模块

核心思想：
不使用纯随机作为主要依据，而是采集：
1. 当前天时
2. 用户停顿时间
3. 问题文本
4. 起卦模式
5. 起卦瞬间的分钟、秒、毫秒

用于生成“起卦瞬间”的扰动因子。

这样同一个问题在不同起卦瞬间可能得到不同结果，
但这种变化并不是无意义随机，而是由天时、人念、问题文本共同形成。
"""

import time
import datetime


def text_to_seed(text):
    """
    将文本转换为稳定数值种子。

    中文、英文、数字都可以参与计算。
    同一个文本会得到相同基础种子。
    """
    if not text:
        return 0

    return sum(ord(char) for char in text)


def normalize_mod(value, mod_base):
    """
    取余工具。

    八卦：除尽取 8
    动爻：除尽取 6
    """
    result = value % mod_base
    return mod_base if result == 0 else result


def collect_focus_seed(prompt_text="请静心凝神，按回车起卦..."):
    """
    采集用户从看到提示到按下回车之间的停顿时间。

    这个停顿时间不是随机数，而是用户当下状态、心念、犹豫、
    外部干扰和反应节奏共同形成的结果。
    """

    print(prompt_text)

    start_time = time.perf_counter()
    input()
    end_time = time.perf_counter()

    focus_seconds = end_time - start_time

    # 毫秒级扰动
    focus_seed = int(focus_seconds * 1000)

    return {
        "focus_seconds": focus_seconds,
        "focus_seed": focus_seed,
    }


def get_moment_seed():
    """
    获取起卦瞬间的时间扰动。

    使用分钟、秒、毫秒，避免同一时辰内结果完全固定。
    """

    now = datetime.datetime.now()

    moment_seed = (
        now.minute * 60 * 1000
        + now.second * 1000
        + now.microsecond // 1000
    )

    return {
        "now": now,
        "moment_seed": moment_seed,
    }


def build_qi_seed(question="", mode="default", extra_text="", focus_seed=0):
    """
    构建综合气机种子。

    参数：
        question: 用户问题
        mode: 起卦模式，例如 full、quick、item、decision、daily
        extra_text: 额外文本，例如物品名、选项名
        focus_seed: 用户停顿时间生成的人念扰动

    返回：
        int 综合扰动种子
    """

    moment_info = get_moment_seed()

    question_seed = text_to_seed(question)
    mode_seed = text_to_seed(mode)
    extra_seed = text_to_seed(extra_text)

    qi_seed = (
        moment_info["moment_seed"]
        + question_seed
        + mode_seed
        + extra_seed
        + focus_seed
    )

    return qi_seed



