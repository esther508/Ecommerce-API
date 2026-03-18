from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta


class CreateProduct(BaseModel):
    name: str
    description: str
    price: int
    stock: int

    class Config:
        from_attributes = True


class UpdateProduct(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    stock: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True
