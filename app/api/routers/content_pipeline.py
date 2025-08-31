"""
Content pipeline management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from uuid import UUID

from app.api import deps
from app.db.models.user import User
from app.core.celery_app import celery_app
from app.core.config import settings
from celery.result import AsyncResult

router = APIRouter(
    prefix="/content",
    tags=["admin_content_pipeline"],
    dependencies=[Depends(deps.get_current_admin_user)],  # Only admins can access these endpoints
)

@router.post("/pipeline/trigger")
async def trigger_content_pipeline(
    ai_provider: str = Body("claude", description="AI provider to use (gemini, claude)"),
    num_problems: int = Body(1, description="Number of problems to generate"),
    auto_approve: bool = Body(False, description="Whether to auto-approve generated problems"),
    github_params: Optional[Dict[str, Any]] = Body(
        None,
        description="GitHub source parameters"
    ),
    stackoverflow_params: Optional[Dict[str, Any]] = Body(
        None,
        description="Stack Overflow source parameters"
    ),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Trigger the content pipeline to generate new problems.
    
    Only accessible by admin users.
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log admin triggered content pipeline
    log_admin_action(
        user=current_user,
        action="trigger_content_pipeline",
        details={
            "ai_provider": ai_provider,
            "num_problems": num_problems,
            "auto_approve": auto_approve,
            "github_params": github_params,
            "stackoverflow_params": stackoverflow_params
        }
    )
    
    # Validate parameters
    if ai_provider not in ["gemini", "claude"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid AI provider. Must be 'gemini' or 'claude'."
        )
    
    if num_problems < 1 or num_problems > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of problems must be between 1 and 10."
        )
    
    # Set default values if parameters are None
    if github_params is None and stackoverflow_params is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one source (GitHub or Stack Overflow) is required"
        )
    
    # Set default GitHub params if provided
    if github_params is not None:
        # Ensure required fields exist
        if not github_params.get("repo"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub repository is required when using GitHub as a source"
            )
            
        # Set default values if not provided
        github_params.setdefault("content_type", "code")
        github_params.setdefault("max_items", 5)
    
    # Set default Stack Overflow params if provided
    if stackoverflow_params is not None:
        # Ensure required fields exist
        if not stackoverflow_params.get("tags") or not isinstance(stackoverflow_params["tags"], list) or len(stackoverflow_params["tags"]) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one Stack Overflow tag is required when using Stack Overflow as a source"
            )
            
        # Set default values if not provided
        stackoverflow_params.setdefault("content_type", "questions")
        stackoverflow_params.setdefault("sort", "votes")
        stackoverflow_params.setdefault("max_items", 5)
    
    # Send celery task
    try:
        result = celery_app.send_task(
            'complete_content_pipeline',
            kwargs={
                'ai_provider': ai_provider,
                'num_problems': num_problems,
                'auto_approve': auto_approve,
                'github_params': github_params,
                'stackoverflow_params': stackoverflow_params
            }
        )
        
        return {
            "success": True,
            "message": "Content pipeline triggered successfully",
            "task_id": result.id,
            "details": {
                "ai_provider": ai_provider,
                "num_problems": num_problems,
                "auto_approve": auto_approve,
                "github_params": github_params,
                "stackoverflow_params": stackoverflow_params
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger content pipeline: {str(e)}"
        )


@router.get("/pipeline/task/{task_id}")
async def get_task_status(
    task_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Get the status of a content pipeline task.
    
    Returns the current status and result (if available).
    """
    try:
        # Import logging utility for admin actions
        from app.utils.logging_utils import log_admin_action
        
        # Log admin checked task status
        log_admin_action(
            user=current_user,
            action="check_pipeline_task_status",
            details={"task_id": task_id}
        )
        
        # Get task result
        task_result = AsyncResult(task_id, app=celery_app)
        
        # Get task state
        task_state = task_result.state
        
        response = {
            "task_id": task_id,
            "status": task_state.lower()
        }
        
        # If task is complete, get the result
        if task_state == "SUCCESS":
            task_info = task_result.get()
            response["result"] = {
                "success": task_info.get("success", False),
                "problems_generated": task_info.get("problems_generated", 0),
                "problems_saved": task_info.get("problems_saved", 0),
                "saved_problem_ids": task_info.get("saved_problem_ids", [])
            }
        elif task_state == "FAILURE":
            response["error"] = str(task_result.result)
            
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check task status: {str(e)}"
        )

