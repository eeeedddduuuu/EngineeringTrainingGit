from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserInfo
from app.utils.security import hash_password, verify_password, create_access_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["认证"])


def __extract_token(authorization: str = Header(default="")):
    """从 Authorization Header 提取 token，自动去除 Bearer 前缀"""
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail={"error": "user_exists", "detail": "用户名已被注册"})
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email or ""
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "message": "注册成功"}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"error": "invalid_credentials", "detail": "用户名或密码错误"})
    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, username=user.username).model_dump()


@router.get("/me")
def get_me(token: str = Depends(__extract_token), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail={"error": "invalid_token", "detail": "Token 无效或已过期"})
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail={"error": "user_not_found", "detail": "用户不存在"})
    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email or None,
        created_at=str(user.created_at)
    ).model_dump()
