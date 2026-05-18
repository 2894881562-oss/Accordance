# -*- coding: utf-8 -*-
"""
六爻详占模块

适合重大决策、趋势判断、前因后果分析。

当前版本：
使用动态时间起卦法，整合完整的京房纳甲装卦、
梅花易数体用分析、互错综卦等多维传统术数体系。
"""

from core.divination import dynamic_time_qi_gua
from core.interpretation import interpret_hexagram
from core.qi_context import collect_focus_seed, get_accurate_day_ganzhi
from core.question_history import handle_duplicate_check, record_question


def print_separator():
    print("=" * 70)


def run_full_divination():
    """运行六爻详占流程"""

    print_separator()
    print("【六爻详占】")
    print("说明：本功能采用京房纳甲筮法 + 梅花易数体用体系。")
    print("包含完整装卦、世应、六亲、六神、十二长生、互错综卦、体用生克分析。")
    print("同一问题在不同起卦瞬间可能得到不同结果，但并非纯随机。")
    print_separator()

    question = input("请输入你所问之事：").strip()

    if not question:
        question = "未命名问题"

    should_proceed, question = handle_duplicate_check(question, "六爻详占")
    if not should_proceed:
        return

    external_omen = input("若起卦前后有明显外应（声音、言语、物象、突发事件等）请输入，无则回车：").strip()

    focus_info = collect_focus_seed(
        "请静心凝神，专注于所问之事。准备好后，按回车确认起卦..."
    )

    hexagram_info = dynamic_time_qi_gua(
        question=question,
        mode="full",
        extra_text=f"六爻详占|外应:{external_omen}",
        focus_seed=focus_info["focus_seed"]
    )
    hexagram_info["external_omen"] = external_omen

    interpret_result = interpret_hexagram(hexagram_info)

    record_question(
        question, "六爻详占",
        f"{interpret_result['gua_name']}（{interpret_result['ji_xiong']}），"
        f"体用：{interpret_result.get('tiyong_info', {}).get('relation', '未知')}"
    )

    # ========== 卦象基本 ==========
    print_separator()
    print("【起卦结果】")
    print(f"卦名：{interpret_result['gua_name']}")
    print(f"卦辞：{interpret_result['gua_ci']}")
    print(f"吉凶等级：{interpret_result['ji_xiong']}")
    print(f"核心意象：{'、'.join(interpret_result['core_meaning'])}")

    # ========== 体用分析 ==========
    print_separator()
    print("【体用生克分析（梅花易数）】")
    print(interpret_result['tiyong_tip'])

    # ========== 五行生克 ==========
    print_separator()
    print("【五行生克与旺衰】")
    print(interpret_result['qian_yin_hou_guo'])
    print(interpret_result['sheng_ke_analysis'])
    print(interpret_result['wang_shuai_analysis'])

    # ========== 动爻与变卦 ==========
    print_separator()
    print("【动爻与变卦】")
    print(interpret_result['dong_yao_tip'])
    if interpret_result.get("yao_ci_tip"):
        print(interpret_result['yao_ci_tip'])
    if interpret_result.get("bian_gua_tip"):
        print(interpret_result['bian_gua_tip'])

    # ========== 互卦 ==========
    print_separator()
    print("【互卦 · 过程视角】")
    print(interpret_result['hu_gua_tip'])
    print(interpret_result['hu_cuo_zong_tip'])

    # ========== 错卦/综卦 ==========
    print_separator()
    print("【错卦 · 反面视角】")
    print(interpret_result['cuo_gua_tip'])
    print()
    print("【综卦 · 换位视角】")
    print(interpret_result['zong_gua_tip'])

    # ========== 完整装卦表（纳甲） ==========
    print_separator()
    print("【六爻纳甲装卦表（京房筮法）】")
    print(interpret_result['zhuanggua_table'])

    print_separator()
    print("【空破刑冲与纳音力量】")
    print(interpret_result['line_strength_summary'])
    print(interpret_result['bian_line_relation_tip'])
    print(interpret_result['dizhi_relation_summary'])
    print(interpret_result['nayin_summary'])
    print(interpret_result['liushen_zhihua_summary'])

    # ========== 六亲格局 ==========
    print_separator()
    print("【用神与六亲格局分析】")
    print(interpret_result['yongshen_system_summary'])
    print(interpret_result['liuqin_summary'])
    if interpret_result.get("dong_yao_liuqin_tip"):
        print(interpret_result['dong_yao_liuqin_tip'])
    if interpret_result.get("liuqin_interpretation"):
        print(interpret_result['liuqin_interpretation'])

    # ========== 六亲象义 ==========
    if interpret_result.get("shishen_info"):
        shishen = interpret_result.get("shishen_liuqin", "")
        shishen_info = interpret_result.get("shishen_info", {})
        print()
        print(f"世爻六亲「{shishen}」象义：{shishen_info.get('description', '')}")
        print(f"所主：{'、'.join(shishen_info.get('zhu_xiang', []))}")

    # ========== 气机 ==========
    print_separator()
    print("【气机信息】")
    print(f"日干支：{get_accurate_day_ganzhi()}")
    print(f"人念停顿：{focus_info['focus_seconds']:.3f} 秒")
    print(f"气机种子：{hexagram_info['qi_seed']}")

    print_separator()
    print("【外应参考（梅花克应）】")
    print(interpret_result['external_omen_tip'])

    # ========== 决策建议 ==========
    print_separator()
    print(f"【综合决策建议】")
    print(interpret_result['traditional_evidence_chain'])
    print()
    print(interpret_result['decision_suggest'])
    print_separator()
    print("【使用提醒】")
    print("1. 以上六爻纳甲装卦按京房正统筮法规则排列")
    print("2. 体用生克出自梅花易数体系，六亲六神出自纳甲筮法")
    print("3. 本系统仅为传统文化研究与决策参考，不替代现实分析")
    print_separator()
