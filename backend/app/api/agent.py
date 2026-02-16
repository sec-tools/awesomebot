"""Agent mode endpoints"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.services.agent_service import AgentService
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()

# Global service
agent_service = AgentService()


class AgentTaskRequest(BaseModel):
    """Agent task request"""
    task: str


@router.post("/execute")
async def execute_agent_task(
    request: AgentTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute a task using agent mode"""
    
    async def generate():
        async for event in agent_service.execute_task(request.task):
            yield json.dumps(event) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")


