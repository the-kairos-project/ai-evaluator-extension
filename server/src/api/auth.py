"""Authentication and authorization module."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
import logging

from src.config.settings import settings
from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)

# Create router - needed for FastAPI to recognize the authentication endpoints
router = APIRouter(prefix="/auth", tags=["auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/token")


class Token(BaseModel):
    """Access token response."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Expiration time in seconds")


class TokenData(BaseModel):
    """Token payload data."""
    
    username: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)


class User(BaseModel):
    """User model."""
    
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: list[str] = Field(default_factory=list)


class UserInDB(User):
    """User in database with hashed password."""
    
    hashed_password: str


class UserCreate(BaseModel):
    """User creation request."""
    
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)


# Temporary in-memory user store (replace with database in production)
fake_users_db: Dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=pwd_context.hash("admin123"),
        disabled=False,
        scopes=["admin", "read", "write"]
    ),
    "user": UserInDB(
        username="user",
        email="user@example.com",
        full_name="Regular User",
        hashed_password=pwd_context.hash("user123"),
        disabled=False,
        scopes=["read"]
    )
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database.
    
    Args:
        username: Username to lookup
        
    Returns:
        Optional[UserInDB]: User if found
    """
    if username in fake_users_db:
        return fake_users_db[username]
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        Optional[UserInDB]: User if authenticated
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        scopes=user.scopes
    )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        User: Active user
        
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class SecurityScopes:
    """Security scope checker."""
    
    def __init__(self, scopes: list[str]) -> None:
        """Initialize with required scopes.
        
        Args:
            scopes: Required scopes
        """
        self.scopes = scopes
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """Check if user has required scopes.
        
        Args:
            current_user: Current active user
            
        Returns:
            User: User if authorized
            
        Raises:
            HTTPException: If user lacks required scopes
        """
        for scope in self.scopes:
            if scope not in current_user.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required scope: {scope}"
                )
        return current_user


# Dependency functions for common scopes
require_admin = SecurityScopes(["admin"])
require_write = SecurityScopes(["write"])
require_read = SecurityScopes(["read"])


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Get an access token using username and password.
    
    This is the only endpoint we actually need for the authentication flow.
    The client will use this endpoint to get a token, and then use that token
    for all subsequent requests.
    
    Args:
        form_data: OAuth2 password request form
        
    Returns:
        Token: Access token
        
    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


def create_user(user_create: UserCreate) -> User:
    """Create a new user.
    
    Args:
        user_create: User creation data
        
    Returns:
        User: Created user
        
    Raises:
        HTTPException: If username already exists
    """
    if user_create.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user_create.password)
    user_in_db = UserInDB(
        username=user_create.username,
        email=user_create.email,
        full_name=user_create.full_name,
        hashed_password=hashed_password,
        disabled=False,
        scopes=user_create.scopes or ["read"]
    )
    
    fake_users_db[user_create.username] = user_in_db
    
    return User(
        username=user_in_db.username,
        email=user_in_db.email,
        full_name=user_in_db.full_name,
        disabled=user_in_db.disabled,
        scopes=user_in_db.scopes
    ) 