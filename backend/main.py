"""
EdgePulse backend entry point.

Run with:
    uvicorn backend.main:app --reload --port 8000

Then open http://localhost:8000 for the dashboard.

Endpoints:
    GET  /                          -> dashboard (frontend/index.html)
    WS   /ws                        -> live stream of ReasoningCycleResult objects
    POST /api/scenario/{name}       -> switch the injected telemetry scenario
    POST /api/connectivity/{state}  -> force connectivity on/off (state = "on" | "off")
    GET  /api/health                -> basic liveness check
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from backend.reasoning_loop import loop
from backend.telemetry_generator import VALID_SCENARIOS

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(loop.run_forever())
    yield
    task.cancel()


app = FastAPI(title="EdgePulse", lifespan=lifespan)


@app.get("/")
async def dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/scenario/{name}")
async def set_scenario(name: str):
    if name not in VALID_SCENARIOS:
        return {"error": f"Unknown scenario. Valid options: {sorted(VALID_SCENARIOS)}"}
    loop.set_scenario(name)
    return {"scenario": name}


@app.post("/api/connectivity/{state}")
async def set_connectivity(state: str):
    if state not in ("on", "off"):
        return {"error": "state must be 'on' or 'off'"}
    loop.set_connectivity(state == "on")
    return {"connectivity": state == "on"}


@app.get("/api/state")
async def get_state():
    return loop.get_state()


@app.post("/api/recorded-demo/{state}")
async def set_recorded_demo(state: str):
    if state not in ("on", "off"):
        return {"error": "state must be 'on' or 'off'"}
    loop.set_recorded_demo(state == "on")
    return {"recorded_demo": state == "on"}


@app.websocket("/ws")
async def ws_stream(websocket: WebSocket):
    await websocket.accept()
    queue = loop.subscribe()
    try:
        while True:
            result = await queue.get()
            await websocket.send_json(result.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    finally:
        loop.unsubscribe(queue)


# Serve any static assets the dashboard needs (kept separate from "/" itself).
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
