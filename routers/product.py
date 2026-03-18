# ​An API router is basically a fast API app. But instead of running on its own, ​it can be included into an existing app. ​Then it basically lets you use these endpoints in the original app.
from fastapi import APIRouter, Depends
from schema.product import CreateProduct, UpdateProduct
from utils.auth import get_current_active_user
from fastapi import HTTPException
import models
from datetime import datetime
from utils.getdb import db_dependency
router = APIRouter()


@router.post("/create-product-admin")
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


@router.get("/get-all-product")
def all_product(db: db_dependency):
    db_product = db.query(models.Product).filter(
        models.Product.is_active == True).all()

    return db_product


@router.get("/get-product-by-id")
def product_by_id(product_id: int, db: db_dependency):
    db_product = db.query(models.Product).filter(
        models.Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product does not exixts")
    return db_product


@router.get("/get-my-product-admin")
def get_my_product(db: db_dependency, current_user: models.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=401, detail="Unauthorized")

    db_product = db.query(models.Product).filter(
        models.Product.owner_id == current_user.id).all()

    return db_product


@router.delete("/delete-product-admin")
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


@router.put("/update-product-admin/{product_id}")
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
