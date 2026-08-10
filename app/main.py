from fastapi import FastAPI
from .routers import admin_router, asset_router, auth_router, portfolio_router
from .errors import register_exception_handlers

app = FastAPI(title="FinTrack API")

register_exception_handlers(app)
app.include_router(auth_router.router)
app.include_router(asset_router.router)
app.include_router(portfolio_router.router)
app.include_router(admin_router.router)

@app.get("/")
def read_root():
    return {"message": "FinTrack API rodando com sucesso no Docker!"}