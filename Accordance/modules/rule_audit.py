# -*- coding: utf-8 -*-
"""传统规则自检 CLI。"""

from core.rule_audit import audit_traditional_rules, format_audit_report


def _sep(char="─", width=62):
    print(char * width)


def run_rule_audit():
    """运行纳甲、八宫、世应与象义校准自检。"""
    print()
    _sep("═")
    print("  纳甲规则与六十四卦数据自检")
    _sep("═")
    print(format_audit_report(audit_traditional_rules()))
    _sep("═")
    print()
