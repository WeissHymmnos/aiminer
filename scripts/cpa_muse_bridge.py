"""CPA Muse Spark Protocol Bridge.

Bridges OpenAI Chat Completions protocol (/v1/chat/completions) to
OpenCode Go's OpenAI Responses API (/v1/responses) with
muse-spark-1.3-contributor and reasoning: {"effort": "high"}.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from loguru import logger
import uvicorn

UPSTREAM_URL = os.getenv(
    "MUSE_UPSTREAM_URL", "https://opencode.ai/zen/go/v1/responses"
)
UPSTREAM_API_KEY = os.getenv(
    "MUSE_UPSTREAM_API_KEY",
    "sk-Umw80akcfLTaQkLByULxlvUa5Wl5jJdi8z48evbELUMT1QlgoixU45VfYr71hNyh",
)
UPSTREAM_SESSION = os.getenv("MUSE_UPSTREAM_SESSION", "cpa-opencode-session")
UPSTREAM_USER_AGENT = os.getenv("MUSE_UPSTREAM_USER_AGENT", "curl/7.81.0")

app = FastAPI(title="CPA Muse Spark Protocol Bridge")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "cpa-muse-bridge"}


@app.get("/models")
@app.get("/v1/models")
async def list_models() -> Dict[str, Any]:
    models = [
        "muse-spark-1.3-contributor",
        "muse-spark-1.3-contributor-high",
        "go-muse-spark-1.3-contributor",
    ]
    return {
        "object": "list",
        "data": [
            {
                "id": m,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "opencode-go",
            }
            for m in models
        ],
    }


def _build_upstream_headers(
    custom_auth: Optional[str] = None,
) -> Dict[str, str]:
    auth = UPSTREAM_API_KEY
    if custom_auth and custom_auth.startswith("Bearer sk-"):
        auth = custom_auth.split("Bearer ", 1)[1].strip()

    return {
        "Authorization": f"Bearer {auth}",
        "x-opencode-session": UPSTREAM_SESSION,
        "User-Agent": UPSTREAM_USER_AGENT,
        "Content-Type": "application/json",
    }


def _convert_messages_to_input(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    formatted_input = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            # Flatten multi-part content if string
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    parts.append(part)
            content = "\n".join(parts)
        else:
            content = str(content or "")

        formatted_input.append({"role": role, "content": content})
    return formatted_input


async def _stream_responses(
    client: httpx.AsyncClient,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    req_model: str,
) -> AsyncGenerator[str, None]:
    resp_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    async with client.stream(
        "POST",
        UPSTREAM_URL,
        json=payload,
        headers=headers,
        timeout=300.0,
    ) as upstream_resp:
        if upstream_resp.status_code != 200:
            err_body = await upstream_resp.aread()
            logger.error(
                f"[Bridge Stream] Upstream error {upstream_resp.status_code}: {err_body.decode('utf-8', errors='ignore')}"
            )
            err_chunk = {
                "error": {
                    "message": f"Upstream error {upstream_resp.status_code}",
                    "details": err_body.decode("utf-8", errors="ignore"),
                }
            }
            yield f"data: {json.dumps(err_chunk)}\n\n"
            return

        async for line in upstream_resp.aiter_lines():
            line = line.strip()
            if not line:
                continue
            if not line.startswith("data:"):
                continue

            data_str = line[5:].strip()
            if not data_str:
                continue

            try:
                event_data = json.loads(data_str)
            except Exception:
                continue

            event_type = event_data.get("type")

            if event_type == "response.output_text.delta":
                delta_text = event_data.get("delta", "")
                chunk = {
                    "id": resp_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": req_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": delta_text},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            elif event_type == "response.completed":
                chunk = {
                    "id": resp_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": req_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Response:
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    req_model = body.get("model", "muse-spark-1.3-contributor-high")
    messages = body.get("messages", [])
    stream = bool(body.get("stream", False))

    formatted_input = _convert_messages_to_input(messages)
    headers = _build_upstream_headers(authorization)

    upstream_payload: Dict[str, Any] = {
        "model": "muse-spark-1.3-contributor",
        "reasoning": {"effort": "high"},
        "input": formatted_input,
    }

    # Always call upstream in streaming mode to keep TCP alive during long reasoning
    upstream_payload["stream"] = True

    if stream:
        client = httpx.AsyncClient(trust_env=False, timeout=600.0)
        return StreamingResponse(
            _stream_responses(client, upstream_payload, headers, req_model),
            media_type="text/event-stream",
        )

    # Accumulate streaming chunks into standard ChatCompletion JSON response
    output_text = ""
    resp_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())
    prompt_tokens = 0
    completion_tokens = 0
    reasoning_tokens = 0

    async with httpx.AsyncClient(trust_env=False, timeout=600.0) as client:
        try:
            async with client.stream(
                "POST",
                UPSTREAM_URL,
                json=upstream_payload,
                headers=headers,
                timeout=600.0,
            ) as upstream_resp:
                if upstream_resp.status_code != 200:
                    err_body = await upstream_resp.aread()
                    logger.error(
                        f"[Bridge] Upstream HTTP {upstream_resp.status_code}: {err_body.decode('utf-8', errors='ignore')}"
                    )
                    return Response(
                        content=err_body,
                        status_code=upstream_resp.status_code,
                        media_type="application/json",
                    )

                async for line in upstream_resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str:
                        continue

                    try:
                        event_data = json.loads(data_str)
                    except Exception:
                        continue

                    event_type = event_data.get("type")
                    if event_type == "response.output_text.delta":
                        output_text += event_data.get("delta", "")
                    elif event_type == "response.completed":
                        r_obj = event_data.get("response", {})
                        resp_id = r_obj.get("id") or resp_id
                        created_ts = r_obj.get("created_at") or created_ts
                        usage = r_obj.get("usage", {})
                        prompt_tokens = usage.get("input_tokens", prompt_tokens)
                        completion_tokens = usage.get(
                            "output_tokens", completion_tokens
                        )
                        reasoning_tokens = usage.get(
                            "output_tokens_details", {}
                        ).get("reasoning_tokens", reasoning_tokens)
                        # Extract full output text if available
                        for item in r_obj.get("output", []):
                            if item.get("type") == "message":
                                for part in item.get("content", []):
                                    if part.get("type") == "output_text":
                                        full_text = part.get("text", "")
                                        if full_text:
                                            output_text = full_text
        except Exception as e:
            logger.error(
                f"[Bridge] Upstream stream failure: {type(e).__name__}: {e}"
            )
            raise HTTPException(
                status_code=502, detail=f"Upstream gateway error: {e}"
            )

    completion_response = {
        "id": resp_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": req_model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": output_text,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "completion_tokens_details": {
                "reasoning_tokens": reasoning_tokens,
            },
        },
    }
    return JSONResponse(content=completion_response)


def main():
    port = int(os.getenv("PORT", "8318"))
    host = os.getenv("HOST", "127.0.0.1")
    logger.info(f"Starting CPA Muse Spark Protocol Bridge on {host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
