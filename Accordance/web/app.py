# -*- coding: utf-8 -*-
"""FastAPI mobile web entrypoint."""

import ipaddress
import json
import os
import socket
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from web.history_store import (
    clear_history,
    history_storage_status,
    normalize_client_id,
    recent_history,
)
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
RATE_LIMIT_PER_CLIENT = 60
RATE_LIMIT_PER_IP = 120
MAX_RATE_BUCKETS = 4096
MAX_REQUEST_BYTES = 64 * 1024
PROXY_DNS_TTL_SECONDS = 60
_rate_bucket = defaultdict(deque)
_last_rate_prune = 0.0
_proxy_dns_cache = {}


def _trusted_proxy_specs():
    configured = os.getenv("ACCORDANCE_TRUSTED_PROXIES", "")
    specs = ["127.0.0.1", "::1"]
    specs.extend(item.strip() for item in configured.split(",") if item.strip())
    return tuple(dict.fromkeys(specs))


TRUSTED_PROXY_NETWORKS = []
TRUSTED_PROXY_HOSTS = []
for _proxy_spec in _trusted_proxy_specs():
    try:
        TRUSTED_PROXY_NETWORKS.append(ipaddress.ip_network(_proxy_spec, strict=False))
    except ValueError:
        TRUSTED_PROXY_HOSTS.append(_proxy_spec)

SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-Robots-Tag": "noindex, nofollow",
}


def _parse_ip(value):
    candidate = (value or "").strip().strip("[]").split("%", 1)[0]
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return getattr(address, "ipv4_mapped", None) or address


def _resolved_proxy_addresses(hostname):
    now = time.monotonic()
    cached = _proxy_dns_cache.get(hostname)
    if cached and now - cached[0] < PROXY_DNS_TTL_SECONDS:
        return cached[1]
    try:
        addresses = {
            address
            for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
            if (address := _parse_ip(item[4][0])) is not None
        }
    except OSError:
        addresses = set()
    _proxy_dns_cache[hostname] = (now, addresses)
    return addresses


def _is_trusted_proxy(request):
    peer = _parse_ip(request.client.host if request.client else "")
    if peer is None:
        return False
    if any(
        peer in network
        for network in TRUSTED_PROXY_NETWORKS
        if peer.version == network.version
    ):
        return True
    return any(peer in _resolved_proxy_addresses(hostname) for hostname in TRUSTED_PROXY_HOSTS)


def _client_ip(request):
    peer = _parse_ip(request.client.host if request.client else "")
    if _is_trusted_proxy(request):
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0]
        forwarded_ip = _parse_ip(forwarded)
        if forwarded_ip is not None:
            return str(forwarded_ip)
    return str(peer) if peer is not None else "unknown"


def _prune_rate_buckets(now, incoming_keys):
    global _last_rate_prune
    if now - _last_rate_prune >= RATE_WINDOW_SECONDS:
        for key, bucket in list(_rate_bucket.items()):
            while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
                bucket.popleft()
            if not bucket:
                _rate_bucket.pop(key, None)
        _last_rate_prune = now

    incoming_keys = set(incoming_keys)
    new_key_count = sum(key not in _rate_bucket for key in incoming_keys)
    if len(_rate_bucket) + new_key_count > MAX_RATE_BUCKETS:
        overflow = len(_rate_bucket) + new_key_count - MAX_RATE_BUCKETS
        oldest_keys = sorted(
            (key for key in _rate_bucket if key not in incoming_keys),
            key=lambda key: _rate_bucket[key][-1],
        )
        for key in oldest_keys[:overflow]:
            _rate_bucket.pop(key, None)


def _rate_limit(request, client_id):
    limits = (
        (f"ip:{_client_ip(request)}", RATE_LIMIT_PER_IP),
        (f"client:{client_id}", RATE_LIMIT_PER_CLIENT),
    )
    now = time.monotonic()
    _prune_rate_buckets(now, [key for key, _ in limits])
    for key, limit in limits:
        bucket = _rate_bucket[key]
        while bucket and now - bucket[0] > RATE_WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")
    for key, _ in limits:
        _rate_bucket[key].append(now)


def _ensure_client_id(request):
    return normalize_client_id(request.cookies.get("client_id", ""))


def _apply_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


def _is_https_request(request):
    if request.url.scheme == "https":
        return True
    if not _is_trusted_proxy(request):
        return False
    forwarded_proto = (
        request.headers.get("x-forwarded-proto", "")
        .split(",", 1)[0]
        .strip()
        .lower()
    )
    return forwarded_proto == "https"


def _with_client_cookie(response, client_id, request):
    response.set_cookie(
        "client_id",
        client_id,
        max_age=3600 * 24 * 365,
        httponly=True,
        path="/",
        samesite="lax",
        secure=_is_https_request(request),
    )
    return _apply_security_headers(response)


def _wants_json(request):
    return "application/json" in request.headers.get("accept", "")


async def _read_request_data(request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/json":
        try:
            return await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=400, detail="请求正文不是有效 JSON") from exc
    if content_type in {"", "application/x-www-form-urlencoded", "multipart/form-data"}:
        return dict(await request.form())
    raise HTTPException(status_code=415, detail="仅支持 JSON 或表单请求")


@app.middleware("http")
async def privacy_headers(request, call_next):
    content_length = request.headers.get("content-length", "")
    oversized = content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES
    if not oversized and request.method in {"POST", "PUT", "PATCH"}:
        oversized = len(await request.body()) > MAX_REQUEST_BYTES
    if oversized:
        response = JSONResponse(
            status_code=413,
            content={"detail": "请求内容过大，请精简后重试"},
        )
    else:
        response = await call_next(request)
    return _apply_security_headers(response)


@app.get("/health")
def health():
    history_status = history_storage_status()
    return {
        "status": "degraded" if history_status == "degraded" else "ok",
        "history": history_status,
    }


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
    return _with_client_cookie(response, client_id, request)


@app.get("/features/{key}", response_class=HTMLResponse)
def feature_form(request: Request, key: str):
    if key not in FEATURES:
        raise HTTPException(status_code=404, detail="功能不存在")
    client_id = _ensure_client_id(request)
    initial_question = request.query_params.get("question", "").strip()[:200]
    response = templates.TemplateResponse(
        request=request,
        name="feature.html",
        context={
            "request": request,
            "feature": FEATURES[key],
            "key": key,
            "title": FEATURES[key]["name"],
            "initial_question": initial_question,
        },
    )
    return _with_client_cookie(response, client_id, request)


@app.post("/api/divinations/{key}")
async def api_divination(request: Request, key: str):
    if key not in FEATURES:
        raise HTTPException(status_code=404, detail="功能不存在")
    client_id = _ensure_client_id(request)
    _rate_limit(request, client_id)
    data = await _read_request_data(request)
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
    return _with_client_cookie(response, client_id, request)


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
        context={
            "request": request,
            "items": data["items"],
            "stats": stats,
            "title": "近期记录",
            "cleared": request.query_params.get("cleared") == "1",
            "clear_failed": request.query_params.get("clear_failed") == "1",
        },
    )
    return _with_client_cookie(response, client_id, request)


@app.post("/history/clear")
def history_clear(request: Request):
    client_id = _ensure_client_id(request)
    _rate_limit(request, client_id)
    cleared = clear_history(client_id)
    target = "/history?cleared=1" if cleared else "/history?clear_failed=1"
    response = RedirectResponse(target, status_code=303)
    return _with_client_cookie(response, client_id, request)


@app.get("/method-selector", response_class=HTMLResponse)
def method_selector(request: Request):
    client_id = _ensure_client_id(request)
    response = templates.TemplateResponse(
        request=request,
        name="method_selector.html",
        context={"request": request, "title": "起卦法选择器", "result": None},
    )
    return _with_client_cookie(response, client_id, request)


@app.post("/api/method-selector")
async def api_method_selector(request: Request):
    client_id = _ensure_client_id(request)
    _rate_limit(request, client_id)
    data = await _read_request_data(request)
    try:
        payload = MethodSelectorRequest.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    result = recommend_methods(payload.question)
    if _wants_json(request):
        response = JSONResponse(jsonable_encoder(result))
    else:
        response = templates.TemplateResponse(
            request=request,
            name="partials/method_result.html",
            context={"request": request, "result": result},
        )
    return _with_client_cookie(response, client_id, request)
