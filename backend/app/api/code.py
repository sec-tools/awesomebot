"""Code execution API"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services import CodeExecutor
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()

# Global service
code_executor = CodeExecutor()


class CodeRequest(BaseModel):
    """Code execution request"""
    code: str
    language: str = "python"


class CodeResponse(BaseModel):
    """Code execution response"""
    success: bool
    output: str
    error: str = ""


@router.post("/execute", response_model=CodeResponse)
async def execute_code(
    request: CodeRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute code in a sandbox"""
    
    if request.language != "python":
        return CodeResponse(
            success=False,
            output="",
            error=f"Language '{request.language}' not supported. Only Python is supported."
        )
    
    result = await code_executor.execute_python(request.code)
    
    return CodeResponse(
        success=result["success"],
        output=result["output"],
        error=result.get("error", "")
    )

