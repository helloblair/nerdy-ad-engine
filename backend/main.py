from fastapi import FastAPI

app = FastAPI(title="Nerdy Ad Engine API")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Nerdy Ad Engine is live 🚀"}

