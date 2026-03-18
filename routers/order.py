from fastapi import APIRouter, Depends
from schema.order import CreateOrder, UpdateOrder
from utils.auth import get_current_active_user
from fastapi import HTTPException
import models
from datetime import datetime
from utils.getdb import db_dependency
router = APIRouter()


@router.post("/create-order")
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
        product_id=product.id,
        product_name=product.name,
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
        product_name=product.name,
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
        "Product name": {orders.product_name},
        "total_amount": {orders.total_amount}

    }


@router.get("/get-all-orders-admin")
def all_orders(db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=401, detail="Unauthorized"
        )

    all_order = db.query(models.OrderItem).join(models.Product, models.Product.id == models.OrderItem.product_id).filter(
        models.Product.owner_id == current_user.id).all()

    return all_order


@router.get("/my-order")
def my_order(db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "customer":
        raise HTTPException(
            status_code=403, detail="Unauthorized"
        )

    item = db.query(models.OrderItem).join(models.Order, models.Order.id ==
                                           models.OrderItem.order_id).filter(models.Order.customer_id == current_user.id).all()
    if not item:
        raise HTTPException(status_code=403, detail="Cart Empty")
    return item


"""
@router.put("/update-order")
def update_order(order_id: int, change_order: UpdateOrder, db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, details="Unauthorized")

    product = db.query(models.Order).filter(
        models.Order.id == order_id).first()



   if product.

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
"""
