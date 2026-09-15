import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.health import router as health_router
from app.api.targets import router as targets_router
from app.core.logging import configure_logging

configure_logging(os.getenv("SERVICE_NAME", "api"))

app = FastAPI(title="Ops Appliance", version="0.1.0")
app.include_router(health_router)
app.include_router(targets_router)


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database unavailable"},
    )
