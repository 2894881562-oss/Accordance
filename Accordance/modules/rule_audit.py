# -*- coding: utf-8 -*-
"""规则数据审计 CLI。"""

from core.rule_audit import format_rule_audit_report, run_rule_audit


def _sep(char="─", width=62):
    print(char * width)


def run_rule_audit_cli():
    """运行规则数据审计。"""
    print()
    _sep("═")
    print("  规则数据审计")
    _sep("═")
    print(format_rule_audit_report(run_rule_audit()))
    _sep("═")
