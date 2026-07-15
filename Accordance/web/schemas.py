# -*- coding: utf-8 -*-
"""Web 层请求与响应模型。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DivinationRequest(BaseModel):
    question: Optional[str] = Field("", max_length=200)
    external_omen: Optional[str] = Field("", max_length=160)
    focus_seed: int = Field(0, ge=0, le=24 * 60 * 60 * 1000)
    force: bool = False

    xing: Optional[str] = Field("", max_length=24)
    ming: Optional[str] = Field("", max_length=24)
    xing_stroke: Optional[int] = Field(None, ge=1, le=99)
    ming_stroke: Optional[int] = Field(None, ge=1, le=99)

    item_name: Optional[str] = Field("", max_length=80)
    last_place: Optional[str] = Field("", max_length=120)
    item_feature: Optional[str] = Field("", max_length=120)
    search_scope: Optional[str] = Field("1", max_length=8)

    option_a: Optional[str] = Field("", max_length=120)
    option_b: Optional[str] = Field("", max_length=120)
    options_text: Optional[str] = Field("", max_length=1200)

    birth_date: Optional[str] = Field("", max_length=10)
    birth_hour: Optional[int] = Field(None, ge=0, le=23)
    birth_minute: Optional[int] = Field(0, ge=0, le=59)
    gender: Optional[str] = Field("", max_length=12)


class MethodSelectorRequest(BaseModel):
    question: str = Field("", max_length=200)


class ResultSection(BaseModel):
    title: str
    items: List[str] = Field(default_factory=list)


class DivinationResponse(BaseModel):
    plain_conclusion: str
    summary: str
    sections: List[ResultSection]
    raw_result: Dict[str, Any]
    duplicate_check: Dict[str, Any]
    history_recorded: bool
