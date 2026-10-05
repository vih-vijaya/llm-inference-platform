import json
import logging
import os
import secrets
import time
import uuid

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
API_KEY = os.getenv("GATEWAY_API_KEY", "dev-secret-key")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gateway")

app = FastAPI(title="LLM Gateway")


class GenerateRequest(BaseModel):
    prompt: str
    model: str = "qwen2.5:0.5b"


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/generate")
async def generate(body: GenerateRequest, x_api_key: str = Header(default="")):
    request_id = str(uuid.uuid4())[:8]

    if not secrets.compare_digest(x_api_key, API_KEY):
        log.info(json.dumps({"request_id": request_id, "event": "auth_failed"}))
        raise HTTPException(status_code=401, detail="Invalid API key")

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": body.model, "prompt": body.prompt, "stream": False},
            )
            resp.raise_for_status()
    except httpx.HTTPError:
        log.info(json.dumps({"request_id": request_id, "event": "model_error"}))
        raise HTTPException(status_code=502, detail="Model server error")

    data = resp.json()
    latency = round(time.time() - start, 3)
    tokens = data.get("eval_count", 0)
    gen_seconds = data.get("eval_duration", 1) / 1_000_000_000

    log.info(json.dumps({
        "request_id": request_id,
        "event": "generate_ok",
        "model": body.model,
        "prompt_chars": len(body.prompt),
        "tokens": tokens,
        "latency_sec": latency,
        "tokens_per_sec": round(tokens / gen_seconds, 1),
    }))

    return {
        "request_id": request_id,
        "response": data["response"],
        "tokens": tokens,
        "latency_sec": latency,
    }