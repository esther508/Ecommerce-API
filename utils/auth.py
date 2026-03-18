from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from utils.getdb import get_db
from jose import ExpiredSignatureError, jwt
import os
from passlib.context import CryptContext
from typing import Optional, Literal
from utils.authtoken import TokenData
import models
from datetime import datetime, timedelta


import resend
from dotenv import load_dotenv
load_dotenv()
if not os.environ["RESEND_API_KEY"]:
    raise EnvironmentError("RESEND_API_KEY is missing")

resend.api_key = os.getenv("RESEND_API_KEY")
# resend = Resend(api_key=resend.api_key)


def send_email(to_email: str, confirmation_link: str):
    try:
        resend.Emails.send(
            {
                "from": "estheromole08@gmail.com",
                "to": [to_email],
                "subject": "Confirm your email",
                "text": f"Click this link to confirm your account: {confirmation_link}"
            }
        )
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print("Error sending email:", e)


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


SECRET_KEY = os.getenv("SECRET_KEY")
# print("SECRET_KEY:", SECRET_KEY)
ALGORITHM = "HS256"


def create_credentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def access_token_expire_minutes() -> int:
    return 15


def confirm_token_expire_minutes() -> int:
    return 1440


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=access_token_expire_minutes)
    to_encode.update({"sub": "email", "exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_confirmation_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=confirm_token_expire_minutes)
    to_encode.update({"sub": "email", "exp": expire, "type": "confirmation"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(email: str, password: str):
    user = get_current_user(email)
    if not user:
        create_credentials_exception("Invalid email or password")
    if not verify_password(password, user.password_hash):
        create_credentials_exception("Invalid email or password")
    if not user.confirmed:
        raise create_credentials_exception("User has not confirmed email")
    return user


def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            create_credentials_exception("Token is missing 'sub' filed")

        type = payload.get("type")
        if type is None or type != "access":
            raise create_credentials_exception(
                "Token has incorrect type, expected'{type} ")
        # return TokenData(email=email)
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Expired",
            headers={"WWW-Authenticate": "Bearer"}
        )from e
    except jwt.PyJWTError:
        raise create_credentials_exception("Invalid Token ")


def get_subject_for_token_type(token: str, type: Literal["access", "confirmation"]) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    except ExpiredSignatureError as e:
        raise create_access_token("Token Expired") from e
    except jwt.PyJWTError:
        raise create_credentials_exception("Invalid Token ")

    email: str = payload.get("sub")
    if email is None:
        raise create_credentials_exception("Token is missing 'sub' filed")

    token_type = payload.get("type")
    if token_type is None or token_type != type:
        raise create_credentials_exception(
            "Token has incorrect type, expected'{type} ")

    return email


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # token_data = verify_token(token)
    # email = get_subject_for_token_type(token, "access")
    # Verify token
    token_data = verify_token(token)
    # Fetch user
    user = db.query(models.User).filter(
        models.User.email == token_data.email).first()
    # email = get_subject_for_token_type(token, "access")
    # Check if email is confirmed
    if not user.confirmed:
        raise create_credentials_exception(
            "could not find user for this token")
    return user


def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=404,
            detail="Inactive User",
        )
    return current_user
