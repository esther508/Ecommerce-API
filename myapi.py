from fastapi import FastAPI, Depends, status
from routers.product import router as product_router
from routers.user import router as user_router
from routers.order import router as order_router
from schema.product import UpdateProduct, CreateProduct
from schema.order import CreateOrder,   UpdateOrder
from schema.user import CreateUser, UserLogin, UpdateProfile
from pydantic import BaseModel
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import jwt  # JSON WEB TOKEN
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os


from sqlalchemy import text

"""
with engine.connect() as conn:
    conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    conn.execute(text("DROP TABLE IF EXISTS users"))
    conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    conn.commit()

"""
load_dotenv()
app = FastAPI()

app.include_router(product_router)
app.include_router(user_router)
app.include_router(order_router)
# models.OrderItem.__table__.drop(engine)
# models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)


class VerifyEmail(BaseModel):
    verify_password: str

    class Config:
        from_attributes = True


"""
@app.post("/token", response_model=Token)
async def create_token_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):

    user = db.query(models.User).filter(
        models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=400, detail="Incorrect username or password")

    if not user.is_active:
        raise HTTPException(
            status_code=400, detail="Inactive User")

    access_token_expires = timedelta(minutes=TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

"""
