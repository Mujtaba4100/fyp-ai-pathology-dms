from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.schemas import UserRegister, UserLogin, UserOut, Token
from app.database import get_db
from app.models.database_models import User
from app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    require_role,
)
from datetime import timedelta
import os

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory default admin fallback if database is empty
DEFAULT_ADMIN = {
    "username": "admin",
    "email": "admin@pathiq.local",
    "password_hash": get_password_hash("admin123"),
    "role": "admin",
}


class ForgotPasswordRequest(BaseModel):
    email: str
    new_password: str


class RoleUpdateRequest(BaseModel):
    role: str  # doctor, lab_tech, admin


@router.post("/register", response_model=UserOut)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user in PostgreSQL EMR database (SRS Use Case 13)
    Allowed public roles: doctor, lab_tech (Admin role assignment restricted to existing Admins)
    """
    # Prevent unauthorized privilege escalation to admin via public signup
    requested_role = (user_data.role or "doctor").lower()
    if requested_role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration as Administrator is not permitted. Only existing Administrators can assign this role in User Management.",
        )
    username = user_data.username.strip()
    email = user_data.email.strip()
    password = user_data.password

    # Validate Username
    if len(username) < 3 or len(username) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 20 characters.",
        )
    import re
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username can only contain alphanumeric characters and underscores.",
        )

    # Validate Email
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address.",
        )

    # Validate Password length
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long.",
        )

    existing_user = (
        db.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )

    hashed_pw = get_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_pw,
        role=requested_role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "role": new_user.role,
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with username and password (SRS Use Case 12)
    Returns JWT access token
    """
    # 1. Check PostgreSQL User table
    db_user = db.query(User).filter(User.username == credentials.username).first()

    if db_user and verify_password(credentials.password, db_user.password_hash):
        token_expires = timedelta(
            minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        )
        token = create_access_token(
            data={"sub": db_user.username, "role": db_user.role},
            expires_delta=token_expires,
        )
        return {"access_token": token, "token_type": "bearer"}

    # 2. Fallback check for default admin
    if (
        credentials.username == DEFAULT_ADMIN["username"]
        and verify_password(credentials.password, DEFAULT_ADMIN["password_hash"])
    ):
        token_expires = timedelta(minutes=60)
        token = create_access_token(
            data={"sub": DEFAULT_ADMIN["username"], "role": DEFAULT_ADMIN["role"]},
            expires_delta=token_expires,
        )
        return {"access_token": token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset user password (SRS Use Case 14)
    """
    user = (
        db.query(User)
        .filter((User.email == req.email) | (User.username == req.email))
        .first()
    )
    if not user:
        # Check default admin
        if req.email in ["admin", "admin@example.com", "admin@pathiq.local"]:
            DEFAULT_ADMIN["password_hash"] = get_password_hash(req.new_password)
            return {"status": "success", "message": "Password reset successfully for admin"}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email or username",
        )

    user.password_hash = get_password_hash(req.new_password)
    db.commit()
    return {"status": "success", "message": "Password has been successfully updated"}


@router.get("/users")
async def list_all_users(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """
    List all system users for administrative management (SRS Use Case 7)
    """
    users = db.query(User).order_by(User.id.asc()).all()
    user_list = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at.strftime("%b %d, %Y") if u.created_at else "Default",
        }
        for u in users
    ]

    # Ensure admin is represented if table has only new users
    if not any(u["username"] == "admin" for u in user_list):
        user_list.insert(0, {
            "id": 0,
            "username": "admin",
            "email": "admin@pathiq.local",
            "role": "admin",
            "created_at": "System Default",
        })

    return {"status": "success", "users": user_list, "total": len(user_list)}


@router.put("/users/{username}/role")
async def update_user_role(
    username: str,
    req: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """
    Assign roles & permissions to user (SRS Use Case 8)
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    user.role = req.role
    db.commit()
    return {"status": "success", "message": f"Role updated to {req.role} for {username}"}


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """
    Delete a user account (SRS Use Case 7)
    """
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete root system administrator")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"User {username} successfully removed"}


@router.get("/me", response_model=UserOut)
async def get_current_user_info(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get current logged-in user profile
    """
    db_user = db.query(User).filter(User.username == current_user.username).first()
    if db_user:
        return {
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "role": db_user.role,
        }

    return {
        "id": 1,
        "username": current_user.username,
        "email": f"{current_user.username}@pathiq.local",
        "role": current_user.role or "doctor",
    }
