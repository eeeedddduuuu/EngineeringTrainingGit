"""扣子（Coze）账号绑定路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/coze", tags=["Coze绑定"])


class CozeBindRequest(BaseModel):
    api_key: str = Field(..., min_length=10, max_length=255)


@router.post("/bind")
def bind_coze(
    req: CozeBindRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """绑定扣子账号 — 保存用户的 Coze API Token"""
    user = db.query(User).filter(User.id == current_user.id).first()
    user.coze_api_key = req.api_key
    db.commit()
    return {
        "bound": True,
        "platform": "扣子",
        "message": "Coze API Key 已绑定成功",
    }


@router.get("/status")
def coze_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户 Coze 绑定状态"""
    user = db.query(User).filter(User.id == current_user.id).first()
    bound = bool(user.coze_api_key)
    return {
        "bound": bound,
        "platform": "扣子",
        "api_key_preview": (user.coze_api_key[:8] + "****" + user.coze_api_key[-4:]) if bound else None,
    }


@router.delete("/unbind")
def unbind_coze(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """解绑扣子账号"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user.coze_api_key:
        raise HTTPException(status_code=400, detail={"error": "not_bound", "detail": "尚未绑定 Coze 账号"})
    user.coze_api_key = None
    db.commit()
    return {"bound": False, "message": "Coze 账号已解绑"}
