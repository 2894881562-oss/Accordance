# -*- coding: utf-8 -*-
"""寻物专项占模块。三爻起卦 + 八卦空间位置专项提示 + 物品特征推理。"""

from core.divination import dynamic_three_yao_quick_divination
from core.interpretation import interpret_three_yao
from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi
from core.question_history import handle_duplicate_check, record_question


def _sep(char="─", width=62):
    print(char * width)


def _hint(gua_name):
    """八卦寻物空间提示。"""
    hints = {
        "乾": "高处、上方、金属物旁、显眼位置。乾主高圆贵重，先查柜顶、架子、桌面、金属器物附近",
        "兑": "开口处、盒口、抽屉口、包口、口袋。兑主口缺，查盒子、包、抽屉、桌边缝隙",
        "离": "明亮处、电器旁、屏幕附近、文书之间。离主明电文，查电脑旁、灯光下、文件书本间",
        "震": "动态区域、门口、走廊、机械旁。震主动移，沿行动路线回溯，查刚经过的位置",
        "巽": "缝隙、夹层、线缆旁、书本间、窗边。巽主入缝，查夹层、桌缝、床缝、包内侧",
        "坎": "低处、暗处、水源附近、黑色物旁。坎主陷藏，查地面、桌下、床下、水杯洗漱区",
        "艮": "固定物旁、墙角、柜角、被压住的位置。艮主止阻，查家具旁、角落、被遮挡处",
        "坤": "低处、地面、衣物中、收纳盒内。坤主地容，查衣服、床铺、包袋、收纳盒、地面",
    }
    return hints.get(gua_name, "暂无专项位置提示，请结合方位与物象综合判断")


def _likelihood(gua_name):
    """寻回概率参考。"""
    tips = {
        "乾": "贵重/金属物品找回概率较高，易在显眼处发现",
        "兑": "可能在开口容器附近，有较大希望找回",
        "离": "明处或电器旁找回概率较高，需仔细翻找",
        "震": "可能被移动过，沿活动路线回溯有希望",
        "巽": "可能在缝隙中，需耐心仔细搜索",
        "坎": "可能在暗处或被遮挡处，找回有一定难度",
        "艮": "可能被卡住或压住，需移动遮挡物",
        "坤": "可能被覆盖或收纳，耐心翻找有希望",
    }
    return tips.get(gua_name, "建议结合方位提示耐心寻找")


def _item_tips(item_name, last_place, item_feature, gua_name):
    """根据物品特征给出针对性建议。"""
    tips = []
    text = f"{item_name}{last_place}{item_feature}".lower()

    if any(w in text for w in ["耳机", "airpods", "充电盒", "电子", "蓝牙", "手机", "phone"]):
        tips.append("小型电子物：优先查桌面、床边、包内侧、充电线附近")
    if any(w in text for w in ["钥匙", "金属", "车钥匙", "门禁"]):
        tips.append("金属件：查门口、桌边、包口、裤袋、抽屉口")
    if any(w in text for w in ["眼镜", "镜片", "太阳镜"]):
        tips.append("眼镜易被压住：查桌面、床头、书本上方、眼镜盒")
    if any(w in text for w in ["u盘", "usb", "硬盘", "内存卡", "数据线"]):
        tips.append("小型存储：查电脑旁、包内夹层、桌缝、文件袋")
    if any(w in text for w in ["钱包", "卡包", "银行卡", "身份证", "证件", "护照"]):
        tips.append("卡证类：查外套口袋、包内夹层、门口柜、最近付款位置")
    if any(w in text for w in ["书", "本子", "笔记", "资料", "文件", "合同", "发票"]):
        tips.append("文书类：查书桌、书架、文件夹、书本夹层、打印机旁")
    if any(w in text for w in ["药", "药盒", "维生素", "创可贴", "口罩"]):
        tips.append("医药小件：查床头、抽屉、包内侧袋、常备药盒")
    if any(w in text for w in ["衣服", "外套", "帽子", "围巾", "手套", "袜子"]):
        tips.append("衣物类：查床铺、衣柜、洗衣篮、椅背、沙发")
    if any(w in text for w in ["化妆", "口红", "粉饼", "镜子", "梳子", "发夹"]):
        tips.append("妆品小件：查洗手台、化妆包、镜子旁、包内小袋")
    if any(w in text for w in ["遥控器", "鼠标", "手柄", "充电器", "插头"]):
        tips.append("常用小件：查沙发缝、桌面、设备旁、插座附近")

    gua_emphasis = {
        "兑": "尤其查开口、盒盖、包口、口袋、抽屉口",
        "坎": "尤其查低处、暗处、黑色物旁、水杯洗漱区",
        "艮": "尤其查墙角、柜边、固定家具旁、被压住处",
        "离": "尤其查电器、灯光、屏幕、充电线、文件间",
        "巽": "尤其查夹层、缝隙、线缆旁、书本间",
        "震": "沿最近行动路线回溯，查刚移动过的位置",
        "坤": "尤其查衣物、被褥、收纳盒、地面覆盖处",
        "乾": "尤其查高处、架子上、金属物旁、贵重物集中处",
    }
    if gua_name in gua_emphasis:
        tips.append(gua_emphasis[gua_name])

    tips.append(f"方位优先：{gua_name}方")
    if not tips:
        tips.append("从最后一次见到的位置开始，结合卦象方位逐层排查")
    return tips


def run_item_search():
    """运行寻物专项占流程"""
    print()
    _sep("═")
    print("  寻物专项占")
    _sep("═")

    item_name = input("请输入要寻找的物品名称：").strip() or "目标物品"
    last_place = input("最后一次见到的大概位置（可回车跳过）：").strip() or "未提供"
    item_feature = input("物品主要特征（可回车跳过）：").strip() or "未提供"
    search_scope = input("搜索范围：1小范围/2大范围或不确定（默认1）：").strip() or "1"
    external_omen = input("若有外应请输入，无则回车：").strip()

    print("\n请静心回想最后一次见到该物品的位置。")
    print("专注于该物品的形状、颜色、用途、最后一次使用场景。")
    focus_info = collect_focus_seed("准备好后，按回车键开始起卦...")

    question_text = f"寻找{item_name}"
    should_proceed, question_text = handle_duplicate_check(question_text, "寻物专项占")
    if not should_proceed:
        return

    extra_text = f"{item_name}|{last_place}|{item_feature}|范围:{search_scope}|外应:{external_omen}"
    three_yao_info = dynamic_three_yao_quick_divination(
        question=question_text, mode="item_search",
        extra_text=extra_text, focus_seed=focus_info["focus_seed"],
    )
    three_yao_info["external_omen"] = external_omen
    r = interpret_three_yao(three_yao_info)

    record_question(
        question_text, "寻物专项占",
        f"得{three_yao_info['gua_info']['name']}卦，方位{three_yao_info['gua_info']['position']}"
    )

    gua_info = three_yao_info["gua_info"]
    gua_name = gua_info["name"]
    tips = _item_tips(item_name, last_place, item_feature, gua_name)

    print()
    _sep("━")
    print(f"  寻找：{item_name}")
    print(f"  最后位置：{last_place}  |  特征：{item_feature}")
    print(f"  {r['core_tip']}")
    print(f"  {r['meaning_tip']}")
    _sep("━")

    print()
    print(f"  【寻回概率】{_likelihood(gua_name)}")
    if search_scope != "1":
        print("  【范围提醒】当前不是明确小范围，三爻只能给方位与物象启示；若物品可能已离开原处，建议改用六爻详占看前因后果。")
    print()
    print(f"  【空间定位】{_hint(gua_name)}")
    print(f"  【方位颜色】{r['direction_tip']}")
    print()
    print(f"  【寻找建议】")
    for i, tip in enumerate(tips, 1):
        print(f"  {i}. {tip}")
    print()
    print(f"  【寻找步骤】")
    print(f"  1. 回到最后见到它的位置，不要扩大范围")
    print(f"  2. 按卦象方位找，再按空间位置排查")
    print(f"  3. 重点查被遮挡、压住、夹住、滑落的位置")
    print(f"  4. 无果则沿最近行动路线反向寻找")
    print(f"  5. 仍找不到可能是范围判断错误或被他人移动")

    omen = r.get("external_omen_tip", "")
    if omen:
        print()
        print(f"  外应：{omen}")

    print()
    print(f"  日干支：{get_accurate_day_ganzhi()}  |  "
          f"人念：{focus_info['focus_seconds']:.2f}秒")
    _sep("═")
    print()
