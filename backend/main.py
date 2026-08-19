from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import run_agent_turn

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Bookly Support Agent")


class ChatRequest(BaseModel):
    messages: list[dict]


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    return run_agent_turn(req.messages)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
