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


def print_separator():
    print("=" * 70)


def print_title():
    """打印系统标题"""
    print_separator()
    print(" " * 20 + "周易风水决策系统")
    print(" " * 15 + "—— 基于传统术数体系的庄重决策参考 ——")
    print_separator()
    print("⚠️  核心准则：无意则为天意，天意勿去刻意")
    print("📜 郑重声明：本系统仅为传统文化研究与决策参考之用，请勿过度迷信")
    print_separator()


def main_menu():
    """显示主菜单并获取用户选择"""
    print("\n【功能菜单】")
    print("1. 六爻详占（一次性老六，重大决策用，看前因后果）")
    print("2. 三爻快占（一次性老三，紧急场景用，快速出结果）")
    print("3. 姓名起卦")
    print("4. 当日气运指引")
    print("5. 寻物专项占")
    print("6. 二选一决策辅助")
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

        else:
            print("输入错误，请重新选择！")
            continue


if __name__ == "__main__":
    main()



