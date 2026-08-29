from typing import Optional
from fastapi import FastAPI, Depends
from pydantic import BaseModel
import httpx
from command_service.config import settings
from command_service.handler import CommandHandler, CommandResult

app = FastAPI(title="JARVIS Command Service")

async def get_memory_client():
    async with httpx.AsyncClient(base_url=settings.memory_service_url) as client:
        yield client

class CommandRequest(BaseModel):
    text: str
    selected_action: str = ""
    last_action: str = ""

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "command-service"}

@app.post("/execute", response_model=CommandResult)
async def execute_command(
    request: CommandRequest,
    memory_client: httpx.AsyncClient = Depends(get_memory_client)
):
    handler = CommandHandler(memory_client=memory_client)
    result = await handler.handle(
        user_input=request.text,
        selected_action=request.selected_action,
        last_action=request.last_action
    )
    return result
