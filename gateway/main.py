import json
import logging
import os
import secrets
import time
import uuid

import httpx
from fastapi import FastAPI, Header, HTTPException, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
API_KEY = os.getenv("GATEWAY_API_KEY", "dev-secret-key")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gateway")

app = FastAPI(title="LLM Gateway")

# ---- Metrics ----
REQUESTS = Counter(
    "gateway_requests_total", "Total generate requests", ["status"]
)
LATENCY = Histogram(
    "gateway_request_latency_seconds",
    "End-to-end latency of successful generate requests",
    buckets=[0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120],
)
TOKENS = Counter("gateway_generated_tokens_total", "Total tokens generated")
TOKENS_PER_SEC = Histogram(
    "gateway_tokens_per_second",
    "Generation speed per request",
    buckets=[10, 25, 50, 75, 100, 150, 200, 300],
)
INFLIGHT = Gauge("gateway_inflight_requests", "Requests currently in progress")


class GenerateRequest(BaseModel):
    prompt: str
    model: str = "qwen2.5:0.5b"


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/generate")
async def generate(body: GenerateRequest, x_api_key: str = Header(default="")):
    request_id = str(uuid.uuid4())[:8]

    if not secrets.compare_digest(x_api_key, API_KEY):
        REQUESTS.labels(status="unauthorized").inc()
        log.info(json.dumps({"request_id": request_id, "event": "auth_failed"}))
        raise HTTPException(status_code=401, detail="Invalid API key")

    start = time.time()
    try:
        with INFLIGHT.track_inprogress():
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": body.model, "prompt": body.prompt, "stream": False},
                )
                resp.raise_for_status()
    except httpx.HTTPError:
        REQUESTS.labels(status="error").inc()
        log.info(json.dumps({"request_id": request_id, "event": "model_error"}))
        raise HTTPException(status_code=502, detail="Model server error")

    data = resp.json()
    latency = time.time() - start
    tokens = data.get("eval_count", 0)
    gen_seconds = data.get("eval_duration", 1) / 1_000_000_000
    tps = tokens / gen_seconds

    REQUESTS.labels(status="ok").inc()
    LATENCY.observe(latency)
    TOKENS.inc(tokens)
    TOKENS_PER_SEC.observe(tps)

    log.info(json.dumps({
        "request_id": request_id,
        "event": "generate_ok",
        "model": body.model,
        "prompt_chars": len(body.prompt),
        "tokens": tokens,
        "latency_sec": round(latency, 3),
        "tokens_per_sec": round(tps, 1),
    }))

    return {
        "request_id": request_id,
        "response": data["response"],
        "tokens": tokens,
        "latency_sec": round(latency, 3),
    }