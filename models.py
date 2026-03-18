from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, DECIMAL
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(200), nullable=False, unique=True)
    email = Column(String(200), nullable=False, unique=True)
    phone = Column(String(30), nullable=True)
    role = Column(String(20), nullable=False)
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    join_date = Column(DateTime, default=datetime.utcnow)
    confirmed = Column(Boolean, default=False)


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    # category = Column(String(30), index=True)
    description = Column(String(240), nullable=False)
    price = Column(DECIMAL(12, 2), nullable=False)
    stock = Column(Integer, nullable=False)
    product_img = Column(String(200), nullable=False,
                         default="productDefault.jpg")
    owner_id = Column(Integer, ForeignKey('users.id'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey("products.id"))
    product_name = Column(String(200), ForeignKey("products.name"))
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    status = Column(String(30), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    product_name = Column(String(200))
    quantity = Column(Integer, nullable=False)
    price_at_time = Column(DECIMAL(12, 2), nullable=False)
