from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.auth import register_user, authenticate_user, create_access_token, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "viewer"

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/register", response_model=dict)
async def register(req: RegisterRequest):
    success = await register_user(req.username, req.email, req.password, req.role)
    if not success:
        raise HTTPException(status_code=400, detail="Benutzer konnte nicht registriert werden.")
    return {"status": "success", "message": "Benutzer registriert."}

@router.post("/login", response_model=Token)
async def login(req: LoginRequest):
    user = await authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültige Anmeldedaten.")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}
