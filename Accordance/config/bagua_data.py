# 八卦基础数据库：修正后的正统规范，保留您提供的核心意象
BAGUA_DATA = {
    1: {
        "name": "乾",
        "full_name": "乾为天",
        "gua_hua": "☰",
        "element": "金",
        "position": "西北",
        "color": "白色/金色",
        "core_meaning": ["刚健", "充实", "主动", "创造", "积极", "物盛"],
        "xiang": "天",
        "weather": "晴",
        "wu_xiang": ["金属", "圆形物", "贵重物", "首脑之物"]
    },
    2: {
        "name": "兑",
        "full_name": "兑为泽",
        "gua_hua": "☱",
        "element": "金",
        "position": "正西",
        "color": "白色",
        "core_meaning": ["愉悦", "和合", "口舌", "相处", "谈话", "缺陷"],
        "xiang": "泽",
        "weather": "湿润",
        "wu_xiang": ["口部之物", "金属器皿", "破损物", "带缺口之物"]
    },
    3: {
        "name": "离",
        "full_name": "离为火",
        "gua_hua": "☲",
        "element": "火",
        "position": "正南",
        "color": "红色",
        "core_meaning": ["热情", "明亮", "燃烧", "附着", "延续", "外露", "绚丽"],
        "xiang": "火",
        "weather": "晴热",
        "wu_xiang": ["电器", "发光物", "文书", "火焰", "纹路之物", "鲜艳之物"]
    },
    4: {
        "name": "震",
        "full_name": "震为雷",
        "gua_hua": "☳",
        "element": "木",
        "position": "正东",
        "color": "绿色",
        "core_meaning": ["鸣动", "震惊", "意外", "警戒", "走动", "发动"],
        "xiang": "雷",
        "weather": "雷雨",
        "wu_xiang": ["电器", "能动之物", "植物", "机械", "发声之物", "木质物"]
    },
    5: {
        "name": "巽",
        "full_name": "巽为风",
        "gua_hua": "☴",
        "element": "木",
        "position": "东南",
        "color": "青花色",
        "core_meaning": ["柔软", "渗入", "谦虚", "适应", "弹性", "进入", "跟风"],
        "xiang": "风",
        "weather": "刮风",
        "wu_xiang": ["细长之物", "木质物", "绳索", "风扇", "轻薄之物", "通道"]
    },
    6: {
        "name": "坎",
        "full_name": "坎为水",
        "gua_hua": "☵",
        "element": "水",
        "position": "正北",
        "color": "黑色",
        "core_meaning": ["险难", "陷入", "劳苦", "磨练", "流动", "隐藏"],
        "xiang": "水",
        "weather": "雨天",
        "wu_xiang": ["水物", "液体", "玻璃", "凹凸不平之物", "带轮之物", "隐藏之物"]
    },
    7: {
        "name": "艮",
        "full_name": "艮为山",
        "gua_hua": "☶",
        "element": "土",
        "position": "东北",
        "color": "黑黄色",
        "core_meaning": ["不动", "停止", "沉思", "踏实", "阻隔", "隐藏"],
        "xiang": "山",
        "weather": "多云转阴",
        "wu_xiang": ["坚硬之物", "固定之物", "山石", "家具", "高处之物", "阻隔之物"]
    },
    8: {
        "name": "坤",
        "full_name": "坤为地",
        "gua_hua": "☷",
        "element": "土",
        "position": "西南",
        "color": "黄色",
        "core_meaning": ["包容", "承载", "静止", "贮存", "生育", "柔弱", "消极"],
        "xiang": "地",
        "weather": "阴天",
        "wu_xiang": ["土地", "方形物", "衣物", "被褥", "地下之物", "包容之物"]
    }
}

# 八卦先天数反查
BAGUA_NAME_TO_NUM = {v["name"]: k for k, v in BAGUA_DATA.items()}