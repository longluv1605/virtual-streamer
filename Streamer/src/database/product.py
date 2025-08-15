from sqlalchemy.orm import Session
from src.models import Product, ProductCreate
from typing import List, Optional
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class ProductDatabaseService:
    @staticmethod
    def create_product(db: Session, product: ProductCreate) -> Product:
        try:
            db_product = Product(**product.model_dump())
            db.add(db_product)
            db.commit()
            db.refresh(db_product)
            return db_product
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_products(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
        category: str = None,
        search: str = None,
        min_price: float = None,
        max_price: float = None,
    ) -> List[Product]:
        try:
            query = db.query(Product)

            if active_only:
                query = query.filter(Product.is_active == True)

            if category:
                query = query.filter(Product.category == category)

            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    Product.name.ilike(search_term)
                    | Product.description.ilike(search_term)
                )

            if min_price is not None:
                query = query.filter(Product.price >= min_price)

            if max_price is not None:
                query = query.filter(Product.price <= max_price)

            products = query.offset(skip).limit(limit).all()
            logger.info(
                f"Retrieved {len(products)} products with filters: active_only={active_only}, category={category}, search={search}"
            )
            return products
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            raise

    @staticmethod
    def count_products(
        db: Session,
        active_only: bool = True,
        category: str = None,
        search: str = None,
        min_price: float = None,
        max_price: float = None,
    ) -> int:
        try:
            query = db.query(Product)

            if active_only:
                query = query.filter(Product.is_active == True)

            if category:
                query = query.filter(Product.category == category)

            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    Product.name.ilike(search_term)
                    | Product.description.ilike(search_term)
                )

            if min_price is not None:
                query = query.filter(Product.price >= min_price)

            if max_price is not None:
                query = query.filter(Product.price <= max_price)

            count = query.count()
            logger.info(
                f"Product count: {count} with filters: active_only={active_only}, category={category}, search={search}"
            )
            return count
        except Exception as e:
            logger.error(f"Error counting products: {e}")
            raise

    @staticmethod
    def get_product(db: Session, product_id: int) -> Optional[Product]:
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            logger.info(
                f"Retrieved product {product_id}: {'Found' if product else 'Not found'}"
            )
            return product
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            raise

    @staticmethod
    def update_product(
        db: Session, product_id: int, product_update: dict
    ) -> Optional[Product]:
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                logger.info(f"Updating product {product_id} with data: {product_update}")
                for key, value in product_update.items():
                    if hasattr(db_product, key):
                        setattr(db_product, key, value)
                db.commit()
                db.refresh(db_product)
                logger.info(f"Successfully updated product {product_id}")
            else:
                logger.warning(f"Product {product_id} not found for update")
            return db_product
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        """Soft delete - mark as inactive"""
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                logger.info(f"Soft deleting product {product_id}: {db_product.name}")
                db_product.is_active = False
                db.commit()
                logger.info(f"Successfully soft deleted product {product_id}")
                return True
            else:
                logger.warning(f"Product {product_id} not found for deletion")
                return False
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def restore_product(db: Session, product_id: int) -> Optional[Product]:
        """Restore a soft-deleted product"""
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                logger.info(f"Restoring product {product_id}: {db_product.name}")
                db_product.is_active = True
                db.commit()
                db.refresh(db_product)
                logger.info(f"Successfully restored product {product_id}")
            else:
                logger.warning(f"Product {product_id} not found for restoration")
            return db_product
        except Exception as e:
            logger.error(f"Error restoring product {product_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def hard_delete_product(db: Session, product_id: int) -> bool:
        """Permanently delete a product"""
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                logger.info(f"Hard deleting product {product_id}: {db_product.name}")
                db.delete(db_product)
                db.commit()
                logger.info(f"Successfully hard deleted product {product_id}")
                return True
            else:
                logger.warning(f"Product {product_id} not found for hard deletion")
                return False
        except Exception as e:
            logger.error(f"Error hard deleting product {product_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_categories(db: Session) -> List[str]:
        """Get list of all unique categories"""
        try:
            categories = (
                db.query(Product.category)
                .filter(Product.is_active == True)
                .distinct()
                .all()
            )
            category_list = [cat[0] for cat in categories if cat[0]]
            logger.info(f"Retrieved {len(category_list)} categories: {category_list}")
            return category_list
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            raise

    @staticmethod
    def get_product_stats(db: Session) -> dict:
        """Get product statistics"""
        try:
            from sqlalchemy import func

            logger.info("Calculating product statistics...")

            # Basic counts
            total_products = db.query(Product).filter(Product.is_active == True).count()
            total_inactive = (
                db.query(Product).filter(Product.is_active == False).count()
            )
            active_products = (
                total_products  # Same as total_products since we filter active
            )

            # Low stock products (less than 10 items)
            low_stock_count = (
                db.query(Product)
                .filter(Product.is_active == True, Product.stock_quantity < 10)
                .count()
            )

            # Total value (sum of all products * stock)
            total_value = (
                db.query(func.sum(Product.price * Product.stock_quantity))
                .filter(Product.is_active == True)
                .scalar()
                or 0
            )

            # Category breakdown
            category_stats = (
                db.query(Product.category, func.count(Product.id).label("count"))
                .filter(Product.is_active == True)
                .group_by(Product.category)
                .all()
            )

            # Top products by value (price * stock)
            top_products_by_value = (
                db.query(
                    Product.name,
                    (Product.price * Product.stock_quantity).label("total_value"),
                )
                .filter(Product.is_active == True)
                .order_by((Product.price * Product.stock_quantity).desc())
                .limit(5)
                .all()
            )

            # Products by category for chart
            products_by_category = [
                {"category": cat or "Không phân loại", "count": count}
                for cat, count in category_stats
            ]

            # Price statistics
            price_stats = (
                db.query(
                    func.min(Product.price).label("min_price"),
                    func.max(Product.price).label("max_price"),
                    func.avg(Product.price).label("avg_price"),
                )
                .filter(Product.is_active == True)
                .first()
            )

            # Stock statistics
            stock_stats = (
                db.query(
                    func.sum(Product.stock_quantity).label("total_stock"),
                    func.avg(Product.stock_quantity).label("avg_stock"),
                )
                .filter(Product.is_active == True)
                .first()
            )

            stats = {
                "total_products": total_products,
                "active_products": active_products,
                "total_inactive": total_inactive,
                "low_stock_products": low_stock_count,
                "total_value": float(total_value),
                "top_products_by_value": [
                    {"name": name, "total_value": float(total_value)}
                    for name, total_value in top_products_by_value
                ],
                "products_by_category": products_by_category,
                "categories": {cat: count for cat, count in category_stats},
                "price_stats": {
                    "min_price": (
                        float(price_stats.min_price) if price_stats.min_price else 0
                    ),
                    "max_price": (
                        float(price_stats.max_price) if price_stats.max_price else 0
                    ),
                    "avg_price": (
                        float(price_stats.avg_price) if price_stats.avg_price else 0
                    ),
                },
                "stock_stats": {
                    "total_stock": (
                        int(stock_stats.total_stock) if stock_stats.total_stock else 0
                    ),
                    "avg_stock": (
                        float(stock_stats.avg_stock) if stock_stats.avg_stock else 0
                    ),
                    "low_stock_count": low_stock_count,
                },
            }

            logger.info(
                f"Product stats calculated: {total_products} total, {active_products} active, {low_stock_count} low stock"
            )
            return stats
        except Exception as e:
            logger.error(f"Error calculating product stats: {e}")
            raise
