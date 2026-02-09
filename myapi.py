from fastapi import FastAPI, Depends, status
from typing import Optional
from typing import Annotated
from pydantic import BaseModel
from fastapi import HTTPException
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import jwt  # JSON WEB TOKEN
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os


load_dotenv()
app = FastAPI()
# models.Base.metadata.drop_all(bind=engine)
models.Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRE = 30


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


class VerifyEmail(BaseModel):
    verify_password: str

    class Config:
        from_attributes = True


class UpdateProfile(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


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


class CreateOrder(BaseModel):
    product_id: int
    quantity: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="could not verify credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return TokenData(email=email)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="could not verify credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    token_data = verify_token(token)
    user = db.query(models.User).filter(
        models.User.email == token_data.email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User doessn't exists",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=404,
            detail="Inactive User",
        )
    return current_user


@app.post('/create-user', response_model=CreateUser)
def create_user(user: UserLogin, db: db_dependency):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(
            status_code=409,
            detail="The User exists already",
        )

    hashed_password = get_password_hash(user.password)

    db_user = models.User(
        username=user.username,
        email=user.email,
        phone=user.phone,
        role=user.role,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return user


@app.get("/profile", response_model=CreateUser)
def get_profile(current_user: models.User = Depends(get_current_active_user)):
    return current_user


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


@app.get("/verify_token")
def verify_token_endpoints(current_user: models.User = Depends(get_current_active_user)):

    return {
        "valid": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,

        }
    }


@app.post("/verify_email")
def verify_email(user: VerifyEmail, db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if not pwd_context.verify(user.verify_password, current_user.password_hash):
        raise HTTPException(
            status_code=409, detail="password mismatch"
        )
    current_user.is_verified = True
    db.commit()
    db.refresh(current_user)
    return {
        "is_verified": "verified"
    }


@app.put("/update-profile")
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


@app.post("/create-product")
def create_product(product: CreateProduct, db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Not an Admin")

    db_product = models.Product(
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        owner_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return "product sucessfully added"


@app.get("/get-all-product")
def all_product(db: db_dependency):
    db_product = db.query(models.Product).filter(
        models.Product.is_active == True).all()

    return db_product


@app.get("/get-product-by-id")
def product_by_id(product_id: int, db: db_dependency):
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product does not exixts")
    return db_product


@app.put("/update-product/{product_id}")
def update_product(product_id: int, product: UpdateProduct, db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Not an Admin")

    db_product = db.query(models.Product).filter(
        models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(
            status_code=404, detail="Product does not exixts")

    if db_product.owner_id != current_user.id:
        raise HTTPException(status_code=401, detail="Not your product")

    if product.name is not None:
        db_product.name = product.name

    if product.description is not None:
        db_product.description = product.description

    if product.price is not None:
        db_product.price = product.price

    if product.stock is not None:
        db_product.stock = product.stock

    db.commit()
    db.refresh(db_product)
    return f" {db_product} updated at : {datetime.utcnow()} "


@app.delete("/delete-product")
def delete_product(product_id: int, db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="product doesn't exist")
    if db_product.owner_id != current_user.id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"
            }


@app.get("/get-my-product")
def get_my_product(db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_product = db.query(models.Product).filter(
        models.Product.owner_id == current_user.id).all()

    return db_product


@app.post("/create-order")
def create_order(order: CreateOrder, db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=401, detail="Unauthorized"
        )

    product = db.query(models.Product).filter(
        models.Product.id == order.product_id,
        models.Product.is_active == True).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product does not exixts")

    if order.quantity <= 0:
        raise HTTPException(
            status_code=400, detail="Quantity must be greater than 0")

    if order.quantity > product.stock:
        raise HTTPException(
            status_code=400, detail="Quantity is more than the available stock")

    total_amount = order.quantity * product.price

    orders = models.Order(
        customer_id=current_user.id,
        total_amount=total_amount,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(orders)
    db.commit()
    db.refresh(orders)

    order_item = models.OrderItem(
        order_id=orders.id,
        product_id=product.id,
        quantity=order.quantity,
        price_at_time=product.price
    )
    db.add(order_item)

    product.stock -= order.quantity

    db.commit()
    return {
        "message": "Order Created",
        "Order_id": {orders.id},
        "status": {orders.status},
        "total_amount": (orders.total_amount)

    }


@app.get("/get-all-orders")
def all_orders(db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=401, detail="Unauthorized"
        )

    all_order = db.query(models.OrderItem).join(models.Product, models.Product.id == models.OrderItem.product_id).filter(
        models.Product.owner_id == current_user.id).all()

    return all_order


"""
@app.get("/my-order")
def my_order(db: db_dependency,current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=401, detail="Unauthorized"
        )
    
    item= db.query(models.OrderItem).join(models.Order, models.Order.id== models.OrderItem.order_id).join(models.Product, models.Product.id == models.OrderItem.product_id).filter (models.Order.customer_id == current_user.id).all()

    return {
        "Product_name" :  item.name,
        "quantity" : item.quantity

    }
"""
