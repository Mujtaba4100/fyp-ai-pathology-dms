from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import UserRegister, UserLogin, UserOut, Token
from app.security import get_password_hash, verify_password, create_access_token, get_current_user
from datetime import timedelta
import os

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Mock in-memory database (will be replaced with real SQL database in Phase 6)
fake_users_db = {}

@router.post("/register", response_model=UserOut)
async def register(user_data: UserRegister):
    """
    Register a new user
    
    Roles: doctor, lab_tech, admin
    """
    if user_data.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Store in mock database
    user_id = len(fake_users_db) + 1
    fake_users_db[user_data.username] = {
        "id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": hashed_password,
        "role": user_data.role
    }
    
    return {
        "id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "role": user_data.role
    }

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login with username and password
    
    Returns JWT access token
    """
    user = fake_users_db.get(credentials.username)
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create JWT token
    access_token_expires = timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    )
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current logged-in user information
    
    Requires: Valid JWT token
    """
    user = fake_users_db.get(current_user.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"]
    }

@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """
    Logout user (client-side: delete JWT token from localStorage)
    """
    return {"message": f"User {current_user.username} logged out successfully"}
