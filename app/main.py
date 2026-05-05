#!/usr/bin/env python3
"""
app/main.py — SwiftDeploy API Service

Runs in stable or canary mode via MODE env var.
Canary adds X-Mode header and activates /chaos endpoint.
"""

import os
import time
import random
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Config from environment (injected by Docker Compose) ──────────────────────
MODE        = os.getenv("MODE", "stable")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_PORT    = int(os.getenv("APP_PORT", "3000"))

# ── Process start time for uptime ─────────────────────────────────────────────
PROCESS_START = time.time()

# ── In-memory chaos state (resets on container restart) ───────────────────────
chaos_state = {
    "mode":       None,
    "duration":   0,
    "error_rate": 0.0,
    "active":     False,
}

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SwiftDeploy Service",
    description="Managed by swiftdeploy CLI",
    version=APP_VERSION,
    docs_url="/docs" if MODE == "canary" else None,
)


# ── Middleware: X-Mode and X-Deployed-By headers ──────────────────────────────
@app.middleware("http")
async def add_headers(request: Request, call_next):
    response = await call_next(request)
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    response.headers["X-Deployed-By"] = "swiftdeploy"
    return response


# ── Middleware: Chaos effects ─────────────────────────────────────────────────
@app.middleware("http")
async def apply_chaos(request: Request, call_next):
    # Never chaos the control endpoints
    if request.url.path in ["/chaos", "/healthz"]:
        return await call_next(request)

    if MODE != "canary" or not chaos_state["active"]:
        return await call_next(request)

    if chaos_state["mode"] == "slow":
        await asyncio.sleep(chaos_state["duration"])

    elif chaos_state["mode"] == "error":
        if random.random() < chaos_state["error_rate"]:
            return JSONResponse(
                status_code=500,
                content={
                    "error":  "Chaos-induced internal server error",
                    "mode":   "canary",
                    "chaos":  "error",
                    "rate":   chaos_state["error_rate"],
                }
            )

    return await call_next(request)


# ── Pydantic request model ────────────────────────────────────────────────────
class ChaosRequest(BaseModel):
    mode:     str
    duration: Optional[int]   = None
    rate:     Optional[float] = None


# ── GET / ─────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return JSONResponse({
        "service":        "SwiftDeploy API",
        "message":        f"Running in {MODE.upper()} mode — everything is nominal",
        "mode":           MODE,
        "version":        APP_VERSION,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - PROCESS_START, 2),
        "chaos_active":   chaos_state["active"] if MODE == "canary" else "n/a",
    })


# ── GET /healthz ──────────────────────────────────────────────────────────────
@app.get("/healthz")
async def healthz():
    return JSONResponse(
        status_code=200,
        content={
            "status":         "healthy",
            "mode":           MODE,
            "version":        APP_VERSION,
            "uptime_seconds": round(time.time() - PROCESS_START, 2),
            "pid":            os.getpid(),
        }
    )


# ── POST /chaos ───────────────────────────────────────────────────────────────
@app.post("/chaos")
async def chaos(body: ChaosRequest):
    if MODE != "canary":
        return JSONResponse(
            status_code=403,
            content={
                "error":        "Chaos endpoint is only available in canary mode",
                "current_mode": MODE,
            }
        )

    if body.mode == "slow":
        duration = body.duration or 5
        chaos_state.update({"mode": "slow", "duration": duration, "active": True})
        return JSONResponse({
            "chaos":            "activated",
            "mode":             "slow",
            "duration_seconds": duration,
            "message":          f"Responses will be delayed by {duration}s",
        })

    elif body.mode == "error":
        rate = body.rate or 0.5
        chaos_state.update({"mode": "error", "error_rate": rate, "active": True})
        return JSONResponse({
            "chaos":      "activated",
            "mode":       "error",
            "error_rate": rate,
            "message":    f"~{int(rate*100)}% of requests will return 500",
        })

    elif body.mode == "recover":
        chaos_state.update({"mode": None, "duration": 0, "error_rate": 0.0, "active": False})
        return JSONResponse({
            "chaos":   "deactivated",
            "message": "Service is fully recovered",
        })

    else:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown chaos mode: {body.mode}. Use slow, error, or recover"}
        )
