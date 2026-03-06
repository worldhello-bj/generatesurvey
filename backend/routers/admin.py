import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from config import settings
from services.ops_service import get_cost_trend, get_records, get_today_stats
from utils.auth import create_access_token, get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": body.username})
    return {"success": True, "access_token": token, "token_type": "bearer"}


@router.get("/stats")
async def get_stats(
    _: str = Depends(get_current_admin),
):
    stats = await get_today_stats()
    return {"success": True, "data": stats}


@router.get("/records")
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_type: Optional[str] = None,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    _: str = Depends(get_current_admin),
):
    data = await get_records(page=page, page_size=page_size, task_type=task_type, user_id=user_id, model=model)
    return {"success": True, **data}


@router.get("/cost-trend")
async def cost_trend(
    days: int = 7,
    _: str = Depends(get_current_admin),
):
    data = await get_cost_trend(days=days)
    return {"success": True, "data": data}
