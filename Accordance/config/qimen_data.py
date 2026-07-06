# -*- coding: utf-8 -*-
"""奇门遁甲运筹基础数据。

本数据层先服务于工程内的传统奇门运筹骨架：九宫、八门、九星、
八神、三奇六仪和常见现实场景。它不是完整专业排盘软件的数据全集。
"""

QIMEN_PALACES = [
    {
        "key": "kan",
        "name": "坎一宫",
        "short": "坎",
        "number": 1,
        "direction": "北",
        "element": "水",
        "branches": ["子"],
        "image": "险中求通、流动、隐伏、沟通。",
    },
    {
        "key": "kun",
        "name": "坤二宫",
        "short": "坤",
        "number": 2,
        "direction": "西南",
        "element": "土",
        "branches": ["未", "申"],
        "image": "承载、资源、团队、后勤。",
    },
    {
        "key": "zhen",
        "name": "震三宫",
        "short": "震",
        "number": 3,
        "direction": "东",
        "element": "木",
        "branches": ["卯"],
        "image": "发动、突破、消息、竞争。",
    },
    {
        "key": "xun",
        "name": "巽四宫",
        "short": "巽",
        "number": 4,
        "direction": "东南",
        "element": "木",
        "branches": ["辰", "巳"],
        "image": "渗透、谈判、文书、传播。",
    },
    {
        "key": "center",
        "name": "中五宫",
        "short": "中",
        "number": 5,
        "direction": "中",
        "element": "土",
        "branches": [],
        "image": "统摄全局，不作单独出行方位。",
    },
    {
        "key": "qian",
        "name": "乾六宫",
        "short": "乾",
        "number": 6,
        "direction": "西北",
        "element": "金",
        "branches": ["戌", "亥"],
        "image": "权责、领导、规则、远方。",
    },
    {
        "key": "dui",
        "name": "兑七宫",
        "short": "兑",
        "number": 7,
        "direction": "西",
        "element": "金",
        "branches": ["酉"],
        "image": "口舌、交易、表达、喜悦。",
    },
    {
        "key": "gen",
        "name": "艮八宫",
        "short": "艮",
        "number": 8,
        "direction": "东北",
        "element": "土",
        "branches": ["丑", "寅"],
        "image": "止守、门槛、积累、转折。",
    },
    {
        "key": "li",
        "name": "离九宫",
        "short": "离",
        "number": 9,
        "direction": "南",
        "element": "火",
        "branches": ["午"],
        "image": "显现、声名、文采、公开。",
    },
]

OUTER_PALACE_KEYS = ["kan", "kun", "zhen", "xun", "qian", "dui", "gen", "li"]

EIGHT_DOORS = {
    "休": {
        "element": "水",
        "level": "吉",
        "score": 2.0,
        "meaning": "休整、人缘、调和、求助、修复。",
        "strategy": "宜缓和关系、整理节奏、求助协商；不宜急攻。",
    },
    "生": {
        "element": "土",
        "level": "大吉",
        "score": 3.0,
        "meaning": "生发、资源、财气、健康、增长。",
        "strategy": "宜求财、开源、养成、推进可控增长。",
    },
    "伤": {
        "element": "木",
        "level": "小凶",
        "score": -1.0,
        "meaning": "冲突、损伤、竞争、破局、强攻。",
        "strategy": "可用于突破和竞争，但要控制伤损与口舌。",
    },
    "杜": {
        "element": "木",
        "level": "平",
        "score": 0.0,
        "meaning": "闭藏、保密、阻隔、研究、内修。",
        "strategy": "宜保密、调研、守口、蓄势；忌公开硬推。",
    },
    "景": {
        "element": "火",
        "level": "小吉",
        "score": 1.0,
        "meaning": "显现、文书、传播、形象、声名。",
        "strategy": "宜展示、汇报、宣传、争取看见；防虚火浮名。",
    },
    "死": {
        "element": "土",
        "level": "凶",
        "score": -3.0,
        "meaning": "停滞、终结、沉重、病象、阻断。",
        "strategy": "宜收尾、止损、复盘；忌冒进开局。",
    },
    "惊": {
        "element": "金",
        "level": "凶",
        "score": -2.0,
        "meaning": "惊扰、口舌、突发、恐慌、争执。",
        "strategy": "宜预案、防口舌、控情绪；不宜仓促表态。",
    },
    "开": {
        "element": "金",
        "level": "大吉",
        "score": 3.0,
        "meaning": "开启、通达、拜访、签约、公开行动。",
        "strategy": "宜开局、拜访、签约、求见、发布。",
    },
}

EIGHT_DOOR_ORDER = ["休", "生", "伤", "杜", "景", "死", "惊", "开"]

NINE_STARS = {
    "天蓬": {
        "element": "水",
        "score": -1.0,
        "meaning": "冒险、欲望、暗流、机会与风险并存。",
    },
    "天任": {
        "element": "土",
        "score": 2.0,
        "meaning": "稳健、承载、可靠、积累。",
    },
    "天冲": {
        "element": "木",
        "score": 1.0,
        "meaning": "行动、速度、竞争、突破。",
    },
    "天辅": {
        "element": "木",
        "score": 2.0,
        "meaning": "学习、文书、贵助、专业支持。",
    },
    "天英": {
        "element": "火",
        "score": 1.0,
        "meaning": "名声、展示、审美、公开表达。",
    },
    "天芮": {
        "element": "土",
        "score": -2.0,
        "meaning": "问题、病象、负担、需要修补之处。",
    },
    "天柱": {
        "element": "金",
        "score": -1.0,
        "meaning": "阻隔、口舌、制度压力、反复。",
    },
    "天心": {
        "element": "金",
        "score": 2.0,
        "meaning": "谋略、医药、规则、领导与决策。",
    },
    "天禽": {
        "element": "土",
        "score": 1.0,
        "meaning": "中枢、统摄、调停、承上启下。",
    },
}

NINE_STAR_ORDER = ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心"]

EIGHT_GODS = {
    "值符": {
        "score": 3.0,
        "meaning": "主令、权威、贵助、核心资源。",
    },
    "螣蛇": {
        "score": -1.0,
        "meaning": "缠绕、疑虑、幻象、反复。",
    },
    "太阴": {
        "score": 2.0,
        "meaning": "暗助、文书、细节、隐性资源。",
    },
    "六合": {
        "score": 2.0,
        "meaning": "合作、和合、谈判、资源联结。",
    },
    "白虎": {
        "score": -2.0,
        "meaning": "冲突、伤损、强硬、压力。",
    },
    "玄武": {
        "score": -2.0,
        "meaning": "隐瞒、盗失、暗线、信息不透明。",
    },
    "九地": {
        "score": 1.0,
        "meaning": "稳守、落地、耐心、防御。",
    },
    "九天": {
        "score": 2.0,
        "meaning": "远行、扩张、公开、抬升格局。",
    },
}

EIGHT_GOD_ORDER = ["值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]

THREE_QI = ["乙", "丙", "丁"]
SIX_YI = ["戊", "己", "庚", "辛", "壬", "癸"]
QIMEN_STEM_ORDER = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]

SIX_JIA_DUN = {
    "甲子": {
        "xun_name": "甲子旬",
        "instrument": "戊",
        "label": "甲子遁戊",
        "role": "主帅藏于戊土根基，重资源、资本、根盘与承载。",
        "strategy": "核心目标宜藏在稳定资源和主线计划之后，先稳根基再开局。",
    },
    "甲戌": {
        "xun_name": "甲戌旬",
        "instrument": "己",
        "label": "甲戌遁己",
        "role": "主帅藏于己土细务，重落实、流程、修补与内控。",
        "strategy": "核心目标宜藏在流程细节中，先补漏洞、控节奏，再向外推进。",
    },
    "甲申": {
        "xun_name": "甲申旬",
        "instrument": "庚",
        "label": "甲申遁庚",
        "role": "主帅藏于庚金阻力，重冲突、对手、硬约束与破局压力。",
        "strategy": "此旬尤其忌暴露底牌，宜借规则、证据和外部条件化解硬冲。",
    },
    "甲午": {
        "xun_name": "甲午旬",
        "instrument": "辛",
        "label": "甲午遁辛",
        "role": "主帅藏于辛金修正，重精细、代价、错误校正与边界。",
        "strategy": "核心目标宜藏在校准与修正中，先纠错、降损，再求表现。",
    },
    "甲辰": {
        "xun_name": "甲辰旬",
        "instrument": "壬",
        "label": "甲辰遁壬",
        "role": "主帅藏于壬水流动，重信息、远路、变化与调度。",
        "strategy": "核心目标宜藏在信息流和路线调度中，先掌握动态，再决定进退。",
    },
    "甲寅": {
        "xun_name": "甲寅旬",
        "instrument": "癸",
        "label": "甲寅遁癸",
        "role": "主帅藏于癸水隐伏，重收束、暗线、等待与细节。",
        "strategy": "核心目标宜藏在隐蔽准备中，先收信息、养条件，不急于摊牌。",
    },
}

SIX_YI_TO_HIDDEN_JIA = {
    data["instrument"]: xunshou
    for xunshou, data in SIX_JIA_DUN.items()
}

QIMEN_STEM_MEANING = {
    "乙": {"type": "三奇", "hidden_jia": "", "score": 1.4, "meaning": "日奇，主柔和、生机、文书与人缘。"},
    "丙": {"type": "三奇", "hidden_jia": "", "score": 1.2, "meaning": "月奇，主显达、光明、声势与传播。"},
    "丁": {"type": "三奇", "hidden_jia": "", "score": 1.3, "meaning": "星奇，主灵感、精细、贵助与机巧。"},
    "戊": {"type": "六仪", "hidden_jia": "甲子", "score": 0.4, "meaning": "甲子戊，主资本、根基、主帅与承载。"},
    "己": {"type": "六仪", "hidden_jia": "甲戌", "score": 0.0, "meaning": "甲戌己，主细碎、落实、隐患与修补。"},
    "庚": {"type": "六仪", "hidden_jia": "甲申", "score": -1.2, "meaning": "甲申庚，主阻力、对抗、硬冲与变故。"},
    "辛": {"type": "六仪", "hidden_jia": "甲午", "score": -0.4, "meaning": "甲午辛，主错误、精细压力、修正与代价。"},
    "壬": {"type": "六仪", "hidden_jia": "甲辰", "score": 0.1, "meaning": "甲辰壬，主流动、变化、远路与信息。"},
    "癸": {"type": "六仪", "hidden_jia": "甲寅", "score": -0.1, "meaning": "甲寅癸，主隐伏、迟疑、收束与细节。"},
}

QIMEN_SCENARIO_RULES = {
    "general": {
        "name": "综合运筹",
        "keywords": [],
        "prefer_doors": ["开", "生", "休"],
        "avoid_doors": ["死", "惊"],
        "prefer_stars": ["天心", "天任", "天辅"],
        "avoid_stars": ["天芮", "天柱"],
        "prefer_gods": ["值符", "六合", "太阴"],
        "avoid_gods": ["白虎", "玄武"],
        "action": "先取可用方位，再按门星神组合决定快进、协商、守势或止损。",
    },
    "negotiation": {
        "name": "谈判协商",
        "keywords": ["谈判", "协商", "沟通", "合作", "签约", "合同", "客户", "见面"],
        "prefer_doors": ["开", "休", "生"],
        "avoid_doors": ["惊", "死", "伤"],
        "prefer_stars": ["天辅", "天心", "天任"],
        "avoid_stars": ["天柱", "天芮"],
        "prefer_gods": ["六合", "太阴", "值符"],
        "avoid_gods": ["白虎", "玄武"],
        "action": "重在占据能打开话题、降低对抗、形成合作的方位与时机。",
    },
    "competition": {
        "name": "竞争对峙",
        "keywords": ["竞争", "对手", "竞标", "比赛", "考试", "克敌", "制胜", "对峙", "冲突", "攻防"],
        "prefer_doors": ["开", "景", "伤"],
        "avoid_doors": ["死", "惊"],
        "prefer_stars": ["天冲", "天英", "天心"],
        "avoid_stars": ["天芮"],
        "prefer_gods": ["九天", "值符"],
        "avoid_gods": ["白虎", "玄武", "螣蛇"],
        "action": "可借开门、景门与天冲之势主动出招，但必须控制伤门和白虎的损耗。",
    },
    "wealth": {
        "name": "财务资源",
        "keywords": ["财", "钱", "收入", "业务", "资源", "客户", "交易", "投资", "现金流"],
        "prefer_doors": ["生", "开"],
        "avoid_doors": ["死", "惊"],
        "prefer_stars": ["天任", "天心", "天辅"],
        "avoid_stars": ["天芮"],
        "prefer_gods": ["六合", "值符", "九地"],
        "avoid_gods": ["玄武", "白虎"],
        "action": "重在资源落地、现金流可控和合作对象可信，不宜贪快。",
    },
    "travel": {
        "name": "出行拜访",
        "keywords": ["出行", "旅行", "拜访", "搬家", "外出", "方向", "方位", "路线", "远行"],
        "prefer_doors": ["开", "休"],
        "avoid_doors": ["死", "惊"],
        "prefer_stars": ["天冲", "天心", "天辅"],
        "avoid_stars": ["天芮", "天柱"],
        "prefer_gods": ["九天", "六合"],
        "avoid_gods": ["玄武", "白虎"],
        "action": "重在路线通达、信息明确和留出缓冲，忌向凶门硬冲。",
    },
    "career": {
        "name": "事业项目",
        "keywords": ["事业", "工作", "升职", "求职", "项目", "领导", "老板", "岗位", "团队"],
        "prefer_doors": ["开", "生", "景"],
        "avoid_doors": ["死", "惊"],
        "prefer_stars": ["天心", "天辅", "天任"],
        "avoid_stars": ["天芮", "天柱"],
        "prefer_gods": ["值符", "六合", "九天"],
        "avoid_gods": ["白虎", "玄武"],
        "action": "重在找准授权、资源、汇报与可见成果，不宜空耗在无主线事务上。",
    },
    "study": {
        "name": "学习文书",
        "keywords": ["学习", "考试", "论文", "研究", "证书", "文书", "写作", "资料"],
        "prefer_doors": ["景", "休", "开"],
        "avoid_doors": ["惊", "死"],
        "prefer_stars": ["天辅", "天心", "天英"],
        "avoid_stars": ["天芮"],
        "prefer_gods": ["太阴", "六合", "值符"],
        "avoid_gods": ["螣蛇", "玄武"],
        "action": "重在资料、表达、证明材料和稳定输出，少被噪音牵走。",
    },
    "health": {
        "name": "健康修复",
        "keywords": ["健康", "疾病", "病", "治疗", "手术", "康复", "医院", "身体"],
        "prefer_doors": ["休", "生"],
        "avoid_doors": ["死", "惊", "伤"],
        "prefer_stars": ["天心", "天任"],
        "avoid_stars": ["天芮", "天柱"],
        "prefer_gods": ["太阴", "六合", "九地"],
        "avoid_gods": ["白虎", "玄武"],
        "action": "重在休整、求医、证据和恢复节律，任何判断都应服从专业医疗意见。",
    },
}

TRADITIONAL_QIMEN_BOUNDARY = (
    "传统奇门以时间、空间和固定盘局为依据，使用者只能顺势择时、择方、运筹，"
    "不能随意改动天地格局。"
)

FENGHOU_QIMEN_BOUNDARY = (
    "王也风后奇门属于动漫《一人之下》的文艺设定，核心是阵主重定方位与吉凶；"
    "本工程不把这种设定纳入传统奇门计算。"
)
