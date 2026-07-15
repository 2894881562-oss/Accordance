# -*- coding: utf-8 -*-
"""CLI 输入规范化助手，与 Web 请求边界保持一致。"""


def ask_text(
    prompt,
    label,
    max_length,
    *,
    required=True,
    default="",
    initial=None,
):
    """读取并校验文本；可优先校验选择器预填值。"""
    candidate = initial
    while True:
        if candidate is None:
            candidate = input(prompt)
        value = (candidate or "").strip()
        candidate = None

        if not value:
            if default:
                return default
            if not required:
                return ""
            print(f"{label}不能为空，请重新输入。")
            continue
        if len(value) > max_length:
            print(f"{label}不能超过 {max_length} 个字符，请精简后重试。")
            continue
        return value


def ask_choice(prompt, label, allowed, *, default=None):
    """读取固定枚举；空输入可采用显式默认值。"""
    choices = tuple(str(item) for item in allowed)
    lookup = {item.casefold(): item for item in choices}
    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        normalized = lookup.get(value.casefold())
        if normalized is not None:
            return normalized
        print(f"{label}输入无效，请选择：{' / '.join(choices)}。")


def present_conclusion(conclusion):
    """先显示短结论；仅在用户明确同意时继续输出详细分析。"""
    print()
    print("━" * 62)
    print(f"  【简短结论】{conclusion}")
    print("━" * 62)
    choice = input("是否展开详细分析？(y/N)：").strip().casefold()
    if choice in {"y", "yes", "是"}:
        print()
        print("  【详细分析】")
        return True
    print("═" * 62)
    print()
    return False
