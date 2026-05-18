# -*- coding: utf-8 -*-
"""寻物专项占模块。"""

from core.divination import dynamic_three_yao_quick_divination
from core.interpretation import interpret_three_yao
from core.qi_context import collect_focus_seed


def print_separator():
    print("=" * 70)


def get_item_search_hint(gua_name):
    hints = {
        "乾": {
            "space_hint": "优先找高处、上方、外露位置、靠近金属物或贵重物的位置",
            "height_hint": "偏高处、柜顶、架子上、桌面上方区域",
            "environment_hint": "可能靠近金属、圆形物、电子设备外壳、钥匙、工具、硬质物品",
            "action_hint": "先从明显位置、高处和常用放置点找，不宜只翻低处角落",
            "logic_hint": "乾主高、圆、金属、贵重、外露，寻物时优先查上方和显眼处",
        },
        "兑": {
            "space_hint": "优先找开口处、缺口处、盒子边、抽屉口、包口、口袋附近",
            "height_hint": "中低位置较多，也可能在桌边、柜边、袋口附近",
            "environment_hint": "可能靠近金属器皿、带口的容器、破损物、白色物体或说话活动区域",
            "action_hint": "重点检查包、盒子、抽屉、口袋、杯子旁、桌面边缘",
            "logic_hint": "兑主口、缺口、白色、金属、开合之物，适合找盒盖、包口、抽屉口附近",
        },
        "离": {
            "space_hint": "优先找明亮处、发光物附近、电器旁、红色或鲜艳物体附近",
            "height_hint": "多在视线容易看到的位置，但可能被亮色物或文书遮挡",
            "environment_hint": "可能靠近电脑、手机、灯、插座、屏幕、文书、带纹路或鲜艳物品",
            "action_hint": "先找电器周围、桌面显眼处、灯光照到的位置、文件书本之间",
            "logic_hint": "离主光、电、明、附着、文书，寻物时重点查电器、灯光、纸张、屏幕周边",
        },
        "震": {
            "space_hint": "优先找动态区域、经常走动的位置、门口、走廊、机械或电器附近",
            "height_hint": "多在中等高度或刚被移动过的位置",
            "environment_hint": "可能靠近能动的东西、机械、电器、植物、木质物、发声物",
            "action_hint": "回想最近一次移动路线，沿行动路径反向寻找",
            "logic_hint": "震主动、移动、声音、启动，寻物时重点查刚经过、刚移动、刚使用过的位置",
        },
        "巽": {
            "space_hint": "优先找缝隙、通道、细长物旁、木质物旁、风扇或空气流动处",
            "height_hint": "偏中低位置，可能夹在缝里、边角、窄处",
            "environment_hint": "可能靠近绳子、线缆、纸张、木条、风扇、窗边、通风口",
            "action_hint": "重点查缝隙、夹层、书本中间、桌缝、床缝、包内侧",
            "logic_hint": "巽主入、缝、风、细长、渗入，寻物时重点查夹层、缝隙、通道和轻薄物之间",
        },
        "坎": {
            "space_hint": "优先找低处、暗处、凹陷处、水源附近、黑色物体附近",
            "height_hint": "偏低处、地面、桌下、床下、柜子底部",
            "environment_hint": "可能靠近水杯、洗手台、液体、玻璃、黑色包、带轮物、隐藏位置",
            "action_hint": "先查低处和暗处，再查水杯、洗漱区、黑色物品附近",
            "logic_hint": "坎主水、陷、暗、藏、低处，寻物时重点查被遮挡、下沉、阴暗位置",
        },
        "艮": {
            "space_hint": "优先找固定物旁、墙角、柜角、家具附近、被挡住的位置",
            "height_hint": "可能在高处或固定不动的位置，也可能被压住、卡住",
            "environment_hint": "可能靠近家具、石块、硬物、墙边、角落、阻隔物后面",
            "action_hint": "重点找角落、柜边、桌脚、墙边、被书本或杂物压住的位置",
            "logic_hint": "艮主止、山、阻隔、固定、隐藏，寻物时重点查不动的家具旁和被挡住的位置",
        },
        "坤": {
            "space_hint": "优先找低处、地面、柔软物、衣物、包裹物、收纳区",
            "height_hint": "偏低处、地面、床上、被褥里、衣服堆中",
            "environment_hint": "可能靠近衣物、被子、袋子、箱子、方形物、黄色或土色物体",
            "action_hint": "重点翻衣服、床铺、包、收纳盒、地面角落和被覆盖的位置",
            "logic_hint": "坤主地、低、柔、包容、覆盖，寻物时重点查衣物、被褥、袋子、收纳盒和地面",
        },
    }
    return hints.get(gua_name, {
        "space_hint": "暂无专项位置提示，请结合方位、颜色、物象综合判断",
        "height_hint": "暂无明确高低提示",
        "environment_hint": "暂无明确环境提示",
        "action_hint": "建议从最近使用地点开始回溯寻找",
        "logic_hint": "暂无专项逻辑提示",
    })


def generate_item_specific_tip(item_name, last_place, item_feature, gua_info):
    """根据用户输入的物品信息生成更贴近现实的寻物建议。"""
    tips = []
    gua_name = gua_info["name"]
    item_text = f"{item_name}{last_place}{item_feature}"
    item_text_lower = item_text.lower()

    if any(w in item_text_lower for w in ["耳机", "airpods", "充电盒", "电子", "蓝牙", "iphone", "手机", "phone"]):
        tips.append("该物品属于小型电子物，优先检查桌面、床边、包内侧、充电线附近、电器旁。")

    if any(w in item_text_lower for w in ["钥匙", "金属", "车钥匙", "门禁"]):
        tips.append("该物品带金属象，优先检查门口、桌边、包口、裤袋、钥匙盘、抽屉口。")

    if any(w in item_text_lower for w in ["眼镜", "镜片", "太阳镜"]):
        tips.append("该物品易被压住或放在显眼处却被忽略，优先查桌面、床头、书本上方、眼镜盒附近。")

    if any(w in item_text_lower for w in ["u盘", "usb", "硬盘", "内存卡", "数据线"]):
        tips.append("该物品体积小，易落入缝隙或夹层，重点查电脑旁、包内夹层、桌缝、文件袋。")

    if any(w in item_text_lower for w in ["宿舍", "房间", "卧室"]):
        tips.append("最后位置在居住空间，建议按：床铺 → 桌面 → 椅子 → 衣物 → 包 → 地面角落 的顺序排查。")

    if any(w in item_text_lower for w in ["书包", "背包", "袋子", "包"]):
        tips.append("涉及包袋信息，重点检查主仓、侧袋、内袋、夹层、包口边缘和包底。")

    if any(w in item_text_lower for w in ["桌", "桌面", "书桌", "工位"]):
        tips.append("涉及桌面信息，重点检查桌面边缘、电脑旁、纸张下、抽屉口、桌下和桌缝。")

    if any(w in item_text_lower for w in ["白色", "白", "银色", "white", "silver"]):
        tips.append("物品颜色偏白/金属色，与兑、乾象相近，容易与纸张、墙面、桌面浅色区域混在一起。")

    if any(w in item_text_lower for w in ["黑色", "黑", "black"]):
        tips.append("物品颜色偏黑，与坎象相近，优先查暗处、黑色包、阴影区域和低处。")

    gua_tips = {
        "兑": "当前得兑象，尤其要查“开口、盒盖、包口、口袋、抽屉口、桌边”这些位置。",
        "坎": "当前得坎象，尤其要查“低处、暗处、黑色物体旁、水杯或洗漱区附近”。",
        "艮": "当前得艮象，尤其要查“墙角、柜边、固定家具旁、被压住或被挡住的位置”。",
        "离": "当前得离象，尤其要查“电器、灯光、屏幕、充电线、文件和显眼处”。",
        "巽": "当前得巽象，尤其要查“夹层、缝隙、线缆旁、书本之间、包内侧”。",
        "震": "当前得震象，尤其要沿最近行动路线回溯，查刚移动过、刚拿过、刚经过的位置。",
        "坤": "当前得坤象，尤其要查“衣物、被褥、包裹、收纳盒、地面、被覆盖处”。",
        "乾": "当前得乾象，尤其要查“高处、架子上、金属物旁、贵重物集中处”。",
    }
    if gua_name in gua_tips:
        tips.append(gua_tips[gua_name])

    tips.append(f"方位优先级：先找{gua_info['position']}方，再按上述空间提示排查。")

    if not tips:
        tips.append("建议先从最后一次见到的位置开始，结合卦象方位、颜色、物象逐层排查。")

    return tips


def run_item_search():
    print_separator()
    print("【寻物专项占】")
    print("说明：本功能适合寻找大概率仍在身边小范围内的物品。")
    print("例如：房间、宿舍、桌面、书包、实验室、办公室、小区附近等。")
    print("若物品已经遗失在大范围公共区域，本结果只能作为启发参考。")
    print("当前版本采用“物品名 + 最后位置 + 物品特征 + 人念 + 起卦瞬间”的动态寻物法。")
    print_separator()

    item_name = input("请输入要寻找的物品名称：").strip() or "目标物品"
    last_place = input("请输入最后一次见到它的大概位置，可直接回车跳过：").strip() or "未提供最后位置"
    item_feature = input("请输入该物品的主要特征，可直接回车跳过：").strip() or "未提供物品特征"

    print("\n请静心回想最后一次见到该物品的位置。")
    print("专注于该物品的形状、颜色、用途、最后一次使用场景。")
    focus_info = collect_focus_seed("准备好后，按回车键开始起卦...")

    question_text = f"寻找{item_name}"
    extra_text = f"{item_name}|{last_place}|{item_feature}"

    three_yao_info = dynamic_three_yao_quick_divination(
        question=question_text,
        mode="item_search",
        extra_text=extra_text,
        focus_seed=focus_info["focus_seed"],
    )
    interpret_result = interpret_three_yao(three_yao_info)
    gua_info = three_yao_info["gua_info"]
    gua_name = gua_info["name"]
    search_hint = get_item_search_hint(gua_name)
    item_tips = generate_item_specific_tip(item_name, last_place, item_feature, gua_info)

    print_separator()
    print(f"【寻物目标】：{item_name}")
    print(f"最后位置：{last_place}")
    print(f"物品特征：{item_feature}")

    print_separator()
    print("【寻物卦象】")
    print(interpret_result["core_tip"])
    print(interpret_result["meaning_tip"])

    print_separator()
    print("【基础定位信息】")
    print(interpret_result["direction_tip"])
    print(interpret_result["wu_xiang_tip"])
    print(interpret_result["weather_tip"])

    print_separator()
    print("【专项寻找提示】")
    print(f"空间位置：{search_hint['space_hint']}")
    print(f"高低判断：{search_hint['height_hint']}")
    print(f"环境特征：{search_hint['environment_hint']}")
    print(f"寻找方法：{search_hint['action_hint']}")
    print(f"象意逻辑：{search_hint['logic_hint']}")

    print_separator()
    print("【结合物品信息的实际建议】")
    for index, tip in enumerate(item_tips, start=1):
        print(f"{index}. {tip}")

    print_separator()
    print("【气机信息】")
    print(f"人念停顿：{focus_info['focus_seconds']:.3f} 秒")
    print(f"气机种子：{three_yao_info['qi_seed']}")
    print(f"三爻结果：{three_yao_info['yao_list']}")

    print_separator()
    print("【实际寻找步骤】")
    print("1. 先回到最后一次见到它的位置，不要先扩大范围。")
    print("2. 按卦象方位找，再按空间位置、高低、颜色和物象排查。")
    print("3. 重点检查容易被遮挡、压住、夹住、滑落的位置。")
    print("4. 若第一轮无果，再沿最近行动路线反向寻找。")
    print("5. 若仍找不到，可能是范围判断错误、被他人移动，或已经离开当前小范围。")
    print_separator()
