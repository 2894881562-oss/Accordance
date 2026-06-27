# -*- coding: utf-8 -*-
"""FastAPI mobile web entrypoint."""

import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from web.history_store import clear_history, normalize_client_id, recent_history
from web.schemas import DivinationRequest, MethodSelectorRequest
from web.services import FEATURES, recommend_methods, run_divination


WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Accordance Mobile Web",
    description="传统术数辅助分析系统移动端 Web 版",
    version="1.0.0",
)

templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

RATE_WINDOW_SECONDS = 60
RATE_LIMIT = 60
_rate_bucket = defaultdict(deque)


def _client_ip(request):
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit(request, client_id):
    key = f"{_client_ip(request)}:{client_id}"
    now = time.time()
    bucket = _rate_bucket[key]
    while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")
    bucket.append(now)


def _ensure_client_id(request):
    return normalize_client_id(request.cookies.get("client_id", ""))


def _with_client_cookie(response, client_id):
    response.set_cookie(
        "client_id",
        client_id,
        max_age=3600 * 24 * 365,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _wants_json(request):
    return "application/json" in request.headers.get("accept", "")


@app.middleware("http")
async def privacy_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    client_id = _ensure_client_id(request)
    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "features": FEATURES, "title": "Accordance"},
    )
    return _with_client_cookie(response, client_id)


@app.get("/features/{key}", response_class=HTMLResponse)
def feature_form(request: Request, key: str):
    if key not in FEATURES:
        raise HTTPException(status_code=404, detail="功能不存在")
    client_id = _ensure_client_id(request)
    response = templates.TemplateResponse(
        request=request,
        name="feature.html",
        context={"request": request, "feature": FEATURES[key], "key": key, "title": FEATURES[key]["name"]},
    )
    return _with_client_cookie(response, client_id)


@app.post("/api/divinations/{key}")
async def api_divination(request: Request, key: str):
    if key not in FEATURES:
        raise HTTPException(status_code=404, detail="功能不存在")
    client_id = _ensure_client_id(request)
    _rate_limit(request, client_id)
    try:
        data = await request.json()
    except Exception:
        data = dict(await request.form())
    try:
        payload = DivinationRequest.model_validate(data)
        result = run_divination(key, payload, client_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if _wants_json(request):
        response = JSONResponse(jsonable_encoder(result))
    else:
        response = templates.TemplateResponse(
            request=request,
            name="partials/result.html",
            context={"request": request, "result": result, "feature": FEATURES[key], "key": key},
        )
    return _with_client_cookie(response, client_id)


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    client_id = _ensure_client_id(request)
    data = recent_history(client_id, limit=20)
    # 不向页面暴露服务端文件路径，只展示属于当前匿名设备的统计。
    stats = dict(data["stats"])
    stats.pop("file", None)
    response = templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"request": request, "items": data["items"], "stats": stats, "title": "近期记录"},
    )
    return _with_client_cookie(response, client_id)


@app.post("/history/clear")
def history_clear(request: Request):
    client_id = _ensure_client_id(request)
    clear_history(client_id)
    response = RedirectResponse("/history", status_code=303)
    return _with_client_cookie(response, client_id)


@app.get("/method-selector", response_class=HTMLResponse)
def method_selector(request: Request):
    client_id = _ensure_client_id(request)
    response = templates.TemplateResponse(
        request=request,
        name="method_selector.html",
        context={"request": request, "title": "起卦法选择器", "result": None},
    )
    return _with_client_cookie(response, client_id)


@app.post("/api/method-selector")
async def api_method_selector(request: Request):
    client_id = _ensure_client_id(request)
    _rate_limit(request, client_id)
    try:
        data = await request.json()
    except Exception:
        data = dict(await request.form())
    payload = MethodSelectorRequest.model_validate(data)
    result = recommend_methods(payload.question)
    if _wants_json(request):
        response = JSONResponse(jsonable_encoder(result))
    else:
        response = templates.TemplateResponse(
            request=request,
            name="partials/method_result.html",
            context={"request": request, "result": result},
        )
    return _with_client_cookie(response, client_id)
