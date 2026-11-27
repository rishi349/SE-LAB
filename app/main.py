"""Application factory.

Run with:  uvicorn app.main:create_app --factory --reload
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.config import Settings, load_settings
from app.core.handlers import register_exception_handlers
from app.core.rate_limit import SlidingWindowRateLimiter
from app.db.connection import init_db
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.notifications.router import router as notifications_router
from app.modules.reconciliation.router import router as reconciliation_router
from app.modules.transactions.router import router as transactions_router
from app.modules.transfers.router import router as transfers_router
from app.modules.users.router import router as users_router
from app.modules.wallets.router import router as wallets_router

API_PREFIX = "/api/v1"
DEMO_PAGE = Path(__file__).parent / "static" / "demo.html"
request_logger = logging.getLogger("app.request")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    init_db(settings.database_path)

    app = FastAPI(
        title="Financial Ledger & Digital Wallet API",
        version="1.0.0",
        description="Wallets, transfers and an immutable ledger. All amounts are integer paise.",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = settings
    app.state.rate_limiter = SlidingWindowRateLimiter()
    register_exception_handlers(app)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # Safe logging: method, path, status and timing only. No headers, bodies or tokens.
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        request_logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.get(f"{API_PREFIX}/health", tags=["Health"], summary="Liveness check")
    def health() -> dict:
        return {"status": "ok"}

    # Demo client: a single static page that only calls the public /api/v1 endpoints.
    # All rules stay enforced by the API; the page adds no backend behaviour.
    @app.get("/demo", include_in_schema=False)
    def demo_page() -> FileResponse:
        return FileResponse(DEMO_PAGE, media_type="text/html")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/demo")

    for router in (
        auth_router,
        users_router,
        wallets_router,
        transfers_router,
        transactions_router,
        notifications_router,
        admin_router,
        reconciliation_router,
    ):
        app.include_router(router, prefix=API_PREFIX)
    return app
