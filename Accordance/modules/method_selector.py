# -*- coding: utf-8 -*-
"""起卦法选择器 CLI。"""

from core.method_selector import format_method_recommendation


def _sep(char="─", width=62):
    print(char * width)


def _dispatch(menu, question):
    if menu == "1":
        from modules.full_divination import run_full_divination
        run_full_divination(prefilled_question=question)
    elif menu == "2":
        from modules.quick_divination import run_quick_divination
        run_quick_divination(prefilled_question=question)
    elif menu == "3":
        from modules.name_divination import run_name_divination
        run_name_divination()
    elif menu == "4":
        from modules.daily_fortune import run_daily_fortune
        run_daily_fortune()
    elif menu == "5":
        from modules.item_search import run_item_search
        run_item_search()
    elif menu == "6":
        from modules.decision_helper import run_decision_helper
        run_decision_helper(prefilled_question=question)
    elif menu == "7":
        from modules.multi_decision import run_multi_decision
        run_multi_decision(prefilled_question=question)
    elif menu == "8":
        from modules.bazi import run_bazi_analysis
        run_bazi_analysis()
    elif menu == "9":
        from modules.qimen import run_qimen_analysis
        run_qimen_analysis(prefilled_topic=question)


def run_method_selector():
    """运行起卦法选择器。"""
    print()
    _sep("═")
    print("  起卦法选择器")
    _sep("═")

    question = input("请简述你要问的事：").strip()
    text, ranked = format_method_recommendation(question)
    print()
    print(text)
    print()
    print("传统取法：事大、事杂、要看过程者取六爻；事急、单点、短期者取三爻；")
    print("名号相关取姓名起卦；当日整体基调用日卦；失物用寻物专项；两案取舍用二选一。")
    print("三案以上取多选最优；出生结构取八字；方位、择时、谈判竞争布局取奇门运筹。")
    _sep("═")

    first = ranked[0]
    choice = input(f"是否直接进入推荐功能「菜单{first['menu']} {first['name']}」？(y/N)：").strip().lower()
    if choice == "y":
        _dispatch(first["menu"], question)
