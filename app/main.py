from fastapi import FastAPI

app = FastAPI(title="FinTrack API")

@app.get("/")
def read_root():
    return {"message": "FinTrack API rodando com sucesso no Docker!"}