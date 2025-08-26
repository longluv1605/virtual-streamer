from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, ProductDatabaseService
from ..models import (
    ProductCreate, 
    ProductUpdate, 
    ProductResponse, 
    ProductStatsResponse, 
    PaginatedProductResponse
)

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/products", tags=["products"])


# Product endpoints
@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """Get list of all product categories"""
    categories = ProductDatabaseService.get_categories(db)
    return categories


@router.get("/stats/summary", response_model=ProductStatsResponse)
async def get_product_stats(db: Session = Depends(get_db)):
    """Get product statistics summary"""
    stats = ProductDatabaseService.get_product_stats(db)
    return stats


@router.post("", response_model=ProductResponse)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product"""
    return ProductDatabaseService.create_product(db, product)


@router.get("", response_model=PaginatedProductResponse)
async def get_products(
    page: int = 1,
    limit: int = 100,
    active_only: bool = True,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """Get products with filtering options"""
    skip = (page - 1) * limit
    actual_active_only = active_only and not include_inactive

    products = ProductDatabaseService.get_products(
        db=db,
        skip=skip,
        limit=limit,
        active_only=actual_active_only,
        category=category,
        search=search,
        min_price=min_price,
        max_price=max_price,
    )

    total = ProductDatabaseService.count_products(
        db=db,
        active_only=actual_active_only,
        category=category,
        search=search,
        min_price=min_price,
        max_price=max_price,
    )

    pages = (total + limit - 1) // limit

    return PaginatedProductResponse(
        items=products, total=total, page=page, pages=pages, limit=limit
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID"""
    product = ProductDatabaseService.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int, product_update: ProductCreate, db: Session = Depends(get_db)
):
    """Update a product completely"""
    product = ProductDatabaseService.update_product(db, product_id, product_update.dict())
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def patch_product(
    product_id: int, product_update: ProductUpdate, db: Session = Depends(get_db)
):
    """Partially update a product"""
    # Only include non-None fields in the update
    update_data = {k: v for k, v in product_update.model_dump().items() if v is not None}
    product = ProductDatabaseService.update_product(db, product_id, update_data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Soft delete a product (mark as inactive)"""
    success = ProductDatabaseService.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


@router.put("/{product_id}/restore")
async def restore_product(product_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted product"""
    product = ProductDatabaseService.restore_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product restored successfully", "product": product}


@router.delete("/{product_id}/hard")
async def hard_delete_product(product_id: int, db: Session = Depends(get_db)):
    """Permanently delete a product from database"""
    success = ProductDatabaseService.hard_delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product permanently deleted"}

