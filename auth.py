from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, APIKeyHeader # Add APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import jwt as pyjwt
import os
from typing import List, Optional
import logging

import schemas # Import schemas module
import crud # Import crud module
from schemas import Token, UserCreate, UserResponse, LoginRequest, UserUpdate, TokenData # Keep specific imports if preferred
from crud import get_user_by_username, create_user, get_all_users, update_user, delete_user # Keep specific imports if preferred
from utils import verify_password, hash_password, audit_log_action
from config import get_async_db
from models import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication & Users"])

# JWT settings
JWT_SECRET = os.getenv("VYOS_JWT_SECRET", "changeme_jwt_secret")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

# Restoring the create_access_token function
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token decoding failed: username (sub) missing.")
            raise credentials_exception
        token_data = TokenData(username=username, roles=payload.get("roles", []))
    except pyjwt.ExpiredSignatureError:
        logger.warning("Token has expired.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.PyJWTError as e:
        logger.error(f"Token decoding error: {e}")
        raise credentials_exception
    
    user = await get_user_by_username(db, username=token_data.username)
    if user is None:
        logger.warning(f"User {token_data.username} from token not found in DB.")
        raise credentials_exception
    # Attach roles from token to user object for this request context if needed,
    # or rely on user.roles from DB. For RBAC, user.roles from DB is authoritative.
    # For simplicity, we'll use user.roles from the DB object.
    return user

# Placeholder for active status if implemented in User model later
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    # if not current_user.is_active: # Assuming an is_active field in User model
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        user_roles = current_user.roles # Access the hybrid property
        
        #logger.debug(f"User {current_user.username} roles: {user_roles}, Allowed roles: {self.allowed_roles}")

        if not any(role in user_roles for role in self.allowed_roles):
            logger.warning(
                f"User {current_user.username} with roles {user_roles} "
                f"attempted action requiring one of {self.allowed_roles}."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires one of roles: {', '.join(self.allowed_roles)}",
            )
        #logger.info(f"User {current_user.username} authorized with roles {user_roles} for roles {self.allowed_roles}")


# Define role requirements
admin_only = RoleChecker(["admin"])
admin_or_owner = RoleChecker(["admin", "user"]) # For owner check, logic needs to be in endpoint

@router.post("/token", response_model=Token)  # Path will be /v1/auth/token
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    user = await get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        audit_log_action(user=form_data.username, action="login", result="failure", details={"reason": "bad credentials"})
        logger.warning(f"Failed login attempt for username: {form_data.username}")  # Log failed login
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles}, expires_delta=access_token_expires
    )
    audit_log_action(user=user.username, action="login", result="success")
    logger.info(f"User {user.username} logged in successfully.")  # Log successful login
    return {"access_token": access_token, "token_type": "bearer"}


# User CRUD operations
# Prefix for these user routes will be /v1/auth/users
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_async_db)):
    # Check if any users exist
    users = await get_all_users(db)
    is_bootstrap = len(users) == 0
    if not is_bootstrap:
        # Only admin can register new users after bootstrap
        from fastapi import Depends
        current_user = await get_current_active_user(db=db)
        if "admin" not in current_user.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can register new users")
    db_user = await get_user_by_username(db, user_in.username)
    if db_user:
        audit_log_action(user=user_in.username, action="register", result="failure", details={"reason": "username exists"})
        logger.warning(f"Attempt to register already existing username: {user_in.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    # Force admin role for first user
    roles = user_in.roles
    if is_bootstrap and "admin" not in roles:
        roles = list(set(roles + ["admin"]))
    user = await create_user(db, username=user_in.username, password=user_in.password, roles=roles)
    audit_log_action(user=user.username, action="register", result="success")
    return user


@router.get("/users/", response_model=List[UserResponse], dependencies=[Depends(admin_only)])
async def read_users(db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_active_user)):
    # Dependency admin_only already checked for admin role
    users = await get_all_users(db)
    return users


@router.get("/users/{username}", response_model=UserResponse)
async def read_user(username: str, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_active_user)):
    # Allow admin to read any user, or user to read their own profile
    if "admin" not in current_user.roles and current_user.username != username:
        logger.warning(f"User {current_user.username} attempted to read user {username} without admin rights.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's information")
    
    user = await get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/users/{username}", response_model=UserResponse)
async def update_existing_user(username: str, user_in: UserUpdate, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_active_user)):
    user_to_update = await get_user_by_username(db, username)
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_admin = "admin" in current_user.roles
    is_self = current_user.username == username

    if not is_admin and not is_self:
        logger.warning(f"User {current_user.username} attempted to update user {username} without admin rights or ownership.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    # Prevent non-admins from changing roles or username of others
    # Prevent non-admins from changing their own roles
    if not is_admin:
        if user_in.roles is not None and user_in.roles != user_to_update.roles: # Check if roles are being changed
            logger.warning(f"Non-admin user {current_user.username} attempted to change roles for user {username}.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to change roles")
        if user_in.username is not None and user_in.username != username:
             logger.warning(f"Non-admin user {current_user.username} attempted to change username for user {username}.")
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to change username")


    # If user_in.roles is None, it means no update to roles is requested by the input schema.
    # The crud.update_user function will only update roles if roles_new is not None.
    # Admin can change roles, username. User can change their own password, and potentially their own username if allowed by admin.
    # Current logic: admin can change anything. User can change their own password and username.
    
    # If an admin is updating roles, and user_in.roles is None, it means roles are not part of this update request.
    # If a user is updating themselves, and user_in.roles is provided (even if same as current), it should be rejected if not admin.
    # The schema UserUpdate allows roles to be None.

    roles_to_pass = user_in.roles
    if not is_admin and user_in.roles is not None: # Non-admins cannot change roles, so ensure roles_new is None for them.
        roles_to_pass = None # Non-admins cannot change roles, so ensure roles_new is None for them.
        if user_in.roles is not None: # If a non-admin *tried* to send roles
             logger.warning(f"Non-admin user {current_user.username} attempted to include roles in update payload for user {username}.")
             # This case is already covered by the HTTPException above if user_in.roles was not None.
             # If user_in.roles was None, roles_to_pass is correctly None.

    username_to_pass = user_in.username
    # Non-admins cannot change username of others. They can change their own.
    # If a non-admin tries to change another user's username, it's blocked by the check:
    # `if not is_admin and not is_self:`
    # If a non-admin tries to change their own username, username_to_pass will be user_in.username.
    # If an admin tries to change a username, username_to_pass will be user_in.username.

    updated_user = await update_user(db, user_to_update, username_new=username_to_pass, password_new=user_in.password, roles_new=roles_to_pass)
    return updated_user


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
async def remove_user(username: str, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_active_user)):
    # Dependency admin_only already checked for admin role
    user_to_delete = await get_user_by_username(db, username)
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_to_delete.id == current_user.id:
        logger.warning(f"Admin user {current_user.username} attempted to delete themselves.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot delete themselves.")
    await delete_user(db, user_to_delete)
    return

# API Key Management Endpoints for Users
api_key_router = APIRouter(
    prefix="/users/me/api-keys",
    tags=["User API Keys"],
    dependencies=[Depends(get_current_active_user)] # Ensures user is authenticated
)

@api_key_router.post("/", response_model=schemas.APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_user_api_key(
    api_key_in: schemas.APIKeyCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    db_api_key = await crud.create_api_key_for_user(
        db, 
        user_id=current_user.id, 
        description=api_key_in.description,
        expires_at=api_key_in.expires_at
    )
    return db_api_key

@api_key_router.get("/", response_model=List[schemas.APIKeyResponse])
async def list_user_api_keys(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    api_keys = await crud.get_api_keys_for_user(db, user_id=current_user.id)
    return api_keys

@api_key_router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_api_key(
    api_key_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user)
):
    success = await crud.delete_api_key_for_user(db, api_key_id=api_key_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found or not owned by user")
    return

# Include the new API key router in the main auth router or app
router.include_router(api_key_router)

# Global API Key Authentication (modified)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key_auth(
    api_key_value: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_async_db)
) -> User: # Returns the User associated with the API key
    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated with API Key"
        )
    
    db_api_key = await crud.get_api_key_by_value(db, api_key_value=api_key_value)
    
    if not db_api_key:
        logger.warning(f"Invalid API Key used: {api_key_value[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        logger.warning(f"Expired API Key used: ID {db_api_key.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key has expired"
        )
    
    # Fetch the user associated with this API key
    # The APIKey model should have a user relationship loaded or accessible via user_id
    # Assuming db_api_key.user is available if relationships are configured for eager/lazy loading
    # or we fetch it explicitly.
    user = await get_user_by_username(db, db_api_key.user.username) # Assuming user relationship is loaded
    if not user:
        logger.error(f"API Key {db_api_key.id} has no associated user or user not found.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key configuration error."
        )
    return user # Return the user model, which includes roles

# Example of how to protect an endpoint with the new API key auth:
# @some_other_router.get("/protected-by-api-key", dependencies=[Depends(get_api_key_auth)])
# async def protected_route(current_user: User = Depends(get_api_key_auth)):
#     # current_user is the user associated with the valid API key
#     # Role checks can be added here too, e.g., if "admin" in current_user.roles:
#     return {"message": f"Hello {current_user.username}, you are authenticated via API key."}