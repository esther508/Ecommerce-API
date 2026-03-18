from fastapi import APIRouter, status, Depends, BackgroundTasks
from schema.user import CreateUser, UserLogin, UpdateProfile
from utils.auth import get_password_hash, authenticate_user, create_access_token, get_current_active_user, get_subject_for_token_type, create_confirmation_token, send_email
from fastapi import HTTPException
import models
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from utils.getdb import db_dependency
TOKEN_EXPIRE = 30
router = APIRouter()


# 201 successfully created
@router.post('/create-user', response_model=CreateUser, status_code=201)
def create_user(user: UserLogin, background_tasks: BackgroundTasks, db: db_dependency):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The User exists already",
        )

    hashed_password = get_password_hash(user.password)

    db_user = models.User(
        username=user.username,
        email=user.email,
        phone=user.phone,
        role=user.role,
        password_hash=hashed_password,
        confirmed=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Generate confirmation token and link
    token = create_confirmation_token({"email": user.email})
    confirmation_link = f"http://127.0.0.1:8000/confirm-email?token={token}"

    # Send confirmation email
    background_tasks.add_task(send_email, user.email, confirmation_link)
    return {
        "details": "User created.please confirm your email",
        "confirmation_email": create_confirmation_token(user.email)


    }


@router.get("/confirm-email")
def confirm_email(token: str, db: db_dependency):
    """
    Endpoint to confirm a user's email using a JWT confirmation token.
    """
    # Verify token and get email
    email = get_subject_for_token_type(token, type="confirmation")
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Get the user from DB
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    #  Mark user as verified
    user.is_verified = True  # make sure your User model has this column
    db.commit()

    return {"message": "Email confirmed successfully!"}


@router.post("/token")
def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password)

    if not user.is_active:
        raise HTTPException(
            status_code=400, detail="Inactive User")
    access_token_expires = timedelta(minutes=TOKEN_EXPIRE)
    access_token = create_access_token(
        user.email, expires_delta=access_token_expires)
    return {
        " access_token ": access_token,
        "token_type": "bearer"
    }


@router.get("/verify_token")
def verify_token_endpoints(current_user: models.User = Depends(get_current_active_user)):

    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,

        }
    }


@router.get("/confirm/{token}")
def confirm_email(token: str, db: db_dependency):
    email = get_subject_for_token_type(token, "confirmation")
    user = db.query(models.User).filter(models.User.email == email).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.confirmed = True

    db.commit()
    return {"Message": "User confirmed successfully"}


@router.get("/profile", response_model=CreateUser)
def get_profile(current_user: models.User = Depends(get_current_active_user)):
    return current_user


@router.put("/update-profile")
def update_profile(user: UpdateProfile, db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    db_user = current_user
    if user.username is not None:
        db_user.username = user.username

    if user.email is not None:
        if current_user.is_verified != True:
            raise HTTPException(status_code=401, detail="Not Verified")
        db_user.email = user.email

    if user.phone is not None:
        db_user.phone = user.phone

    db.commit()
    db.refresh(db_user)
    return "Information updated"
