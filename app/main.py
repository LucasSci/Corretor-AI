from fastapi import FastAPI
from pydantic import BaseModel, Field
from app.db.init_db import init_db
from app.services.agent import handle_message


app = FastAPI(title="CorretorIA - MVP")

class MessageIn(BaseModel):
    contact_id: str = Field(..., max_length=80)
    text: str = Field(..., max_length=1000)

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/")
async def root():
    return {"name": "CorretorIA", "status": "running", "docs": "/docs"}

@app.post("/chat")
async def chat(payload: MessageIn):
    result = await handle_message(payload.contact_id, payload.text)
    return {"contact_id": payload.contact_id, **result}

