from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, internal, retailers, tracked_products
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(retailers.router, prefix="/api/retailers", tags=["retailers"])
app.include_router(
    tracked_products.router, prefix="/api/tracked-products", tags=["tracked-products"]
)
app.include_router(internal.router, prefix="/api/internal", tags=["internal"])
