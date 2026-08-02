from fastapi import FastAPI
from .routers import auth_router
from .errors import register_exception_handlers

app = FastAPI(title="FinTrack API")

register_exception_handlers(app)
app.include_router(auth_router.router)

@app.get("/")
def read_root():
    return {"message": "FinTrack API rodando com sucesso no Docker!"}