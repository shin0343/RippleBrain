from __future__ import annotations
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router

app = FastAPI(title="RippleBrain API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.middleware("http")
async def internal_token_gate(request: Request, call_next):
    """Optional service-to-service gate for the SaaS integration.

    When INTERNAL_API_TOKEN is set (deployment behind the NestJS gateway),
    compute/mutation routes require the matching X-Internal-Token header, so
    the engine cannot be driven anonymously around the gateway's
    organization auth. Read-only routes stay public. When unset (local
    development), all routes stay open.
    """
    token = os.environ.get("INTERNAL_API_TOKEN", "")
    protected = (
        ("POST", "/api/changes/analyze"),
        ("POST", "/api/actions/"),
    )
    needs_token = token and any(
        request.method == method and request.url.path.startswith(prefix)
        for method, prefix in protected
    )
    if needs_token and request.headers.get("x-internal-token", "") != token:
        return JSONResponse(status_code=401, content={"detail": "Internal token required"})
    return await call_next(request)

@app.get("/")
def root():
    return {"service": "ripplebrain-backend", "docs": "/docs"}
