from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta


class CreateOrder(BaseModel):
    product_id: int
    quantity: int


class UpdateOrder(BaseModel):
    quantity: int
