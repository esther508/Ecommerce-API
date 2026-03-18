from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta


class CreateUser(BaseModel):
    username: str
    email: str
    phone: Optional[str] = None
    role: str

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    email: str
    phone: str
    role: str
    password: str

    class Config:
        from_attributes = True


class UpdateProfile(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True
