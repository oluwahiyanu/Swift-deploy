#!/usr/bin/env python3
"""
app/main.py — SwiftDeploy API Service

Runs in stable or canary mode via MODE env var.
Canary adds X-Mode header and activates /chaos endpoint.
"""

"""
app/main.py — SwiftDeploy API Service (Phase 2)

New in Phase 2:
- /metrics endpoint in Prometheus text format
- Counters, histograms, and gauges tracked via prometheus_client
- All existing endpoints unchanged
"""

import os
import time
import random
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel


from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
    REGISTRY
)


http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "path", "status_code"]
)


http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Gauges — single values that go up and down
app_uptime_seconds = Gauge(
    "app_uptime_seconds",
    "Seconds since the application started"
)
app_mode_gauge = Gauge(
    "app_mode",
    "Current deployment mode (0=stable, 1=canary)"
)
chaos_active_gauge = Gauge(
    "chaos_active",
    "Active chaos mode (0=none, 1=slow, 2=error)"
)

# ─── Configuration ────────────────────────────────────────────────────────────
MODE        = os.getenv("MODE", "stable")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_PORT    = int(os.getenv("APP_PORT", "3000"))
PROCESS_START = time.time()

# ─── Chaos state ──────────────────────────────────────────────────────────────
chaos_state = {
    "mode": None,
    "duration": 0,
    "error_rate": 0.0,
    "active": False,
}

# ─── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="SwiftDeploy Service",
    version=APP_VERSION,
    docs_url="/docs" if MODE == "canary" else None,
)


# ─── Middleware: Prometheus metrics collection ────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    
   
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    path   = request.url.path
    method = request.method
    status = str(response.status_code)

    # Increment request counter
    http_requests_total.labels(
        method=method,
        path=path,
        status_code=status
    ).inc()

    # Record duration in histogram
    http_request_duration_seconds.labels(
        method=method,
        path=path
    ).observe(duration)

    return response


# ─── Middleware: Mode header ──────────────────────────────────────────────────
@app.middleware("http")
async def add_mode_header(request: Request, call_next):
    response = await call_next(request)
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    response.headers["X-Deployed-By"] = "swiftdeploy"
    return response


# ─── Middleware: Chaos effects ────────────────────────────────────────────────
@app.middleware("http")
async def apply_chaos(request: Request, call_next):
    if request.url.path in ["/chaos", "/healthz", "/metrics"]:
        return await call_next(request)
    if MODE != "canary" or not chaos_state["active"]:
        return await call_next(request)
    if chaos_state["mode"] == "slow":
        await asyncio.sleep(chaos_state["duration"])
    elif chaos_state["mode"] == "error":
        if random.random() < chaos_state["error_rate"]:
            return JSONResponse(
                status_code=500,
                content={"error": "Chaos-induced error", "mode": "canary"}
            )
    return await call_next(request)


# ─── Background task: Update gauges ──────────────────────────────────────────
async def update_gauges():
   
    while True:
        app_uptime_seconds.set(time.time() - PROCESS_START)
        app_mode_gauge.set(1 if MODE == "canary" else 0)

        if not chaos_state["active"]:
            chaos_active_gauge.set(0)
        elif chaos_state["mode"] == "slow":
            chaos_active_gauge.set(1)
        elif chaos_state["mode"] == "error":
            chaos_active_gauge.set(2)

        await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    """Start the background gauge updater when FastAPI boots."""
    asyncio.create_task(update_gauges())


# ─── GET /metrics — Prometheus scrape endpoint ────────────────────────────────
@app.get("/metrics")
async def metrics():
    
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# ─── GET / ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return JSONResponse({
        "service":        "SwiftDeploy API",
        "message":        f"🚀 Running in {MODE.upper()} mode",
        "mode":           MODE,
        "version":        APP_VERSION,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - PROCESS_START, 2),
        "chaos_active":   chaos_state["active"] if MODE == "canary" else "n/a",
    })


# ─── GET /healthz ─────────────────────────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return JSONResponse(status_code=200, content={
        "status":         "healthy",
        "mode":           MODE,
        "version":        APP_VERSION,
        "uptime_seconds": round(time.time() - PROCESS_START, 2),
        "pid":            os.getpid(),
    })


# ─── POST /chaos ──────────────────────────────────────────────────────────────
class ChaosRequest(BaseModel):
    mode: str
    duration: Optional[int] = None
    rate: Optional[float] = None


@app.post("/chaos")
async def chaos(request_body: ChaosRequest):
    if MODE != "canary":
        return JSONResponse(status_code=403,
            content={"error": "Chaos only available in canary mode"})

    if request_body.mode == "slow":
        duration = request_body.duration or 5
        chaos_state.update({"mode":"slow","duration":duration,"active":True})
        return JSONResponse({"chaos":"activated","mode":"slow","duration":duration})

    elif request_body.mode == "error":
        rate = request_body.rate or 0.5
        chaos_state.update({"mode":"error","error_rate":rate,"active":True})
        return JSONResponse({"chaos":"activated","mode":"error","error_rate":rate})

    elif request_body.mode == "recover":
        chaos_state.update({"mode":None,"duration":0,"error_rate":0.0,"active":False})
        return JSONResponse({"chaos":"deactivated","message":"Service recovered"})

    return JSONResponse(status_code=400,
        content={"error": f"Unknown mode: {request_body.mode}"})