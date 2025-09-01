from __future__ import annotations

import os
from typing import List, Union

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel


app = FastAPI(title="LLM SupportBot Inference API")


class GenerateRequest(BaseModel):
    prompt: Union[str, List[str]]


class GenerateResponse(BaseModel):
    generated_text: Union[str, List[str]]


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = os.getenv("API_KEY", "devkey")
    if x_api_key is None or x_api_key != expected:
        # Using 401 with WWW-Authenticate is a common choice; keep simple stub here
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse, dependencies=[Depends(require_api_key)])
def generate(req: GenerateRequest) -> GenerateResponse:
    # Placeholder generation logic; echo back prompt(s)
    def _gen(p: str) -> str:
        return f"placeholder response for: {p}"

    if isinstance(req.prompt, list):
        outputs = [_gen(p) for p in req.prompt]
        return GenerateResponse(generated_text=outputs)
    else:
        return GenerateResponse(generated_text=_gen(req.prompt))

