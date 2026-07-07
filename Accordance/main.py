# -*- coding: utf-8 -*-
"""
周易风水决策系统主程序入口

main.py 只负责：
1. 显示标题
2. 显示菜单
3. 接收用户选择
4. 调用 modules 中的功能模块
"""

from modules.full_divination import run_full_divination
from modules.quick_divination import run_quick_divination
from modules.name_divination import run_name_divination
from modules.daily_fortune import run_daily_fortune
from modules.item_search import run_item_search
from modules.decision_helper import run_decision_helper
from modules.method_selector import run_method_selector
from modules.bazi import run_bazi_analysis
from modules.qimen import run_qimen_analysis
from core.question_history import show_history


def print_separator():
    print("=" * 70)


def print_title():
    """打印系统标题"""
    print_separator()
    print(" " * 10 + "《周易》六爻纳甲 · 梅花易数 · 四柱八字 · 奇门运筹")
    print(" " * 18 + "—— 易为君子谋，卦为镜鉴，人为本 ——")
    print_separator()
    print("  核心准则：无意则为天意，天意勿去刻意")
    print("  根本要义：人为本 —— 卦象为镜，你的选择与德行决定一切")
    print("  郑重声明：本系统仅为传统文化研究与决策参考，请勿过度迷信")
    print_separator()


def main_menu():
    """显示主菜单并获取用户选择"""
    print("\n【功能菜单 —— 易经术数体系】")
    print("1. 六爻详占（京房纳甲筮法，重大决策用，前因后果尽显）")
    print("2. 三爻快占（梅花易数单卦，紧急场景快速指引）")
    print("3. 姓名起卦（笔画成卦，六爻纳甲体系解卦）")
    print("4. 当日气运指引（日卦为基，查看当日整体运势基调）")
    print("5. 寻物专项占（八卦方位 + 物品特征推理）")
    print("6. 二选一决策辅助（双卦对比 + 风险分析）")
    print("7. 四柱八字基础分析（十神/强弱/阶段/格局倾向）")
    print("8. 奇门运筹分析（方位/时机/格局/裁决/置信度）")
    print("9. 查看近期起卦记录")
    print("10. 起卦法选择器（按问题推荐入口）")
    print("0. 退出系统")

    print_separator()

    choice = input("请输入您的选择（数字）：").strip()
    return choice


def main():
    """主程序循环"""
    print_title()

    while True:
        choice = main_menu()

        if choice == "0":
            print("\n感谢使用，愿您顺势而为，守正持中。")
            print_separator()
            break

        elif choice == "1":
            run_full_divination()

        elif choice == "2":
            run_quick_divination()

        elif choice == "3":
            run_name_divination()

        elif choice == "4":
            run_daily_fortune()

        elif choice == "5":
            run_item_search()

        elif choice == "6":
            run_decision_helper()

        elif choice == "7":
            run_bazi_analysis()

        elif choice == "8":
            run_qimen_analysis()

        elif choice == "9":
            show_history()

        elif choice == "10":
            run_method_selector()

        else:
            print("输入错误，请重新选择！")
            continue


if __name__ == "__main__":
    main()



