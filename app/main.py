from fastapi import FastAPI
from .database import engine
from .models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FinTrack API")

@app.get("/")
def read_root():
    return {"message": "FinTrack API rodando com sucesso no Docker!"}