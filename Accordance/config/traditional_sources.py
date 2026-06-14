# -*- coding: utf-8 -*-
"""传统术数依据与实占校验提示。

本模块只做解释层汇总，不参与起卦和断卦计算。目的在于让输出
能够说明“按什么传统规则看、现实中还要核对什么”。
"""

CLASSICAL_RULE_TRACE = (
    "京房纳甲：先定八宫、世应、飞伏、纳甲干支；"
    "增删卜易：以用神、动变、六冲六合、旬空月破、四时旺衰、生克冲刑为纲；"
    "卜筮正宗：用神为事体，原神生用，忌神克用，仇神制原助忌，飞伏、进退、反吟伏吟不可草看；"
    "梅花易数：体为主、用为事，生体与比和为吉，克体与体生用须审旺衰，并兼看互变与外应。"
)

OPERATION_BOUNDARY = (
    "实占边界：卦象给趋势与警示，不替代事实核验；"
    "钱财看现金流、合同与止损，健康看症状检查与医生意见，法律看证据与专业意见。"
)


def build_source_trace(zhuanggua_result, yongshen_system, bian_relation):
    """生成本卦调用到的传统依据摘要。"""
    infer = yongshen_system.get("inference", {})
    yongshen_name = yongshen_system.get("yongshen_name", "未知")
    palace = zhuanggua_result.get("palace_name", "未知")
    palace_role = zhuanggua_result.get("palace_role", "未知")
    yueling = zhuanggua_result.get("yueling", "未知")
    day_ganzhi = zhuanggua_result.get("day_ganzhi", "未知")
    xunkong = "、".join(zhuanggua_result.get("xunkong", {}).get("empty_branches", [])) or "无"
    relation = bian_relation.get("relation", "无明显回头生克") if isinstance(bian_relation, dict) else "无明显回头生克"

    parts = [
        f"本卦按{palace}宫{palace_role}定世应纳甲，月建{yueling}、日辰{day_ganzhi}、旬空{xunkong}入局。",
        f"问类为{infer.get('category', '泛问')}，取{yongshen_name}为用神；先看用神旺衰，再看原神、忌神、仇神与伏神。",
        f"动变取{relation}，再合参六冲六合、刑冲合害、卦身、神煞与梅花体用。",
        CLASSICAL_RULE_TRACE,
    ]
    return "；".join(parts)


def build_reality_check(category, yongshen_name):
    """按问事门类给出现实校验清单。"""
    category = category or ""
    if "疾病" in category or "医药" in category:
        return "现实校验：记录症状、时间线、诱因和检查结果；按医生意见处理，卦中官鬼/子孙只作病象与医药象参考。"
    if "寻物" in category:
        return "现实校验：先限定最后出现的小范围，按路线回溯、查遮挡夹缝和收纳处；范围过大或已离身，应改用六爻详占看前因后果。"
    if "婚恋" in category:
        return "现实校验：核对双方真实意愿、沟通质量、现实阻力和边界感；卦象不替代当面沟通。"
    if "财货" in category or yongshen_name == "妻财":
        return "现实校验：核对现金流、合同条款、交付能力、合规风险和止损线；不因吉象放大仓位。"
    if "官职" in category or yongshen_name == "官鬼":
        return "现实校验：核对岗位职责、上级反馈、组织变化、竞争者与可交付成果；以事实表现承接卦象。"
    if "文书" in category or yongshen_name == "父母":
        return "现实校验：核对材料清单、截止日期、证明文件、签章流程和备选方案；文书之事最忌疏漏。"
    if "出行" in category:
        return "现实校验：核对天气、路况、票务、时间余量、同行人和备用方案；遇冲破空亡先保守安排。"
    if "同辈" in category or yongshen_name == "兄弟":
        return "现实校验：核对合伙权责、利益分配、沟通记录和退出机制；兄弟旺动多主竞争与分耗。"
    return OPERATION_BOUNDARY
