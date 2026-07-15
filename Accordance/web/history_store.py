# -*- coding: utf-8 -*-
"""匿名设备隔离的问题历史存储。"""

import os
import re
import threading
import uuid

from core.question_history import (
    MAX_HISTORY_BYTES,
    MAX_HISTORY_ENTRIES,
    QuestionHistory,
    build_duplicate_decision,
)


CLIENT_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_LOCK = threading.Lock()


def web_data_dir():
    """返回 Web 匿名历史目录；实际建目录由可容错的保存流程负责。"""
    configured = os.getenv("ACCORDANCE_WEB_DATA_DIR")
    if configured:
        path = configured
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, ".data", "web_clients")
    return path


def new_client_id():
    """生成不含用户身份信息的匿名设备 ID。"""
    return uuid.uuid4().hex


def normalize_client_id(client_id):
    """校验匿名设备 ID；无效时返回新 ID。"""
    candidate = (client_id or "").strip().lower()
    if CLIENT_ID_RE.match(candidate):
        return candidate
    return new_client_id()


def _history_file(client_id):
    safe_id = normalize_client_id(client_id)
    return os.path.join(web_data_dir(), f"{safe_id}.json")


def get_history(client_id):
    """获取某个匿名设备自己的历史对象。"""
    return QuestionHistory(history_file=_history_file(client_id))


def check_duplicate(client_id, question, module_label, match_mode="semantic"):
    with _LOCK:
        return build_duplicate_decision(
            question,
            module_label,
            get_history(client_id),
            match_mode=match_mode,
        )


def record_question(client_id, question, module_label, result_summary, context=""):
    with _LOCK:
        return get_history(client_id).add_question(
            question,
            module_label,
            result_summary,
            context=context,
        )


def recent_history(client_id, limit=20):
    with _LOCK:
        history = get_history(client_id)
        return {
            "items": history.get_recent(limit),
            "stats": history.stats(),
            "limits": {
                "max_entries": MAX_HISTORY_ENTRIES,
                "max_bytes": MAX_HISTORY_BYTES,
            },
        }


def clear_history(client_id):
    with _LOCK:
        return get_history(client_id).clear()
