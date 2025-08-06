from sqlalchemy.orm import Session
from src.models import (
    Product,
    StreamSession,
    StreamProduct,
    Comment,
    ScriptTemplate,
    Avatar,
    ProductCreate,
    StreamSessionCreate,
    CommentCreate,
    ScriptTemplateCreate,
)
from typing import List, Optional
import json


class ProductService:
    @staticmethod
    def create_product(db: Session, product: ProductCreate) -> Product:
        try:
            db_product = Product(**product.model_dump())
            db.add(db_product)
            db.commit()
            db.refresh(db_product)
            return db_product
        except Exception as e:
            print(f"Error creating product: {e}")
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
            print(
                f"Retrieved {len(products)} products with filters: active_only={active_only}, category={category}, search={search}"
            )
            return products
        except Exception as e:
            print(f"Error getting products: {e}")
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
            print(
                f"Product count: {count} with filters: active_only={active_only}, category={category}, search={search}"
            )
            return count
        except Exception as e:
            print(f"Error counting products: {e}")
            raise

    @staticmethod
    def get_product(db: Session, product_id: int) -> Optional[Product]:
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            print(
                f"Retrieved product {product_id}: {'Found' if product else 'Not found'}"
            )
            return product
        except Exception as e:
            print(f"Error getting product {product_id}: {e}")
            raise

    @staticmethod
    def update_product(
        db: Session, product_id: int, product_update: dict
    ) -> Optional[Product]:
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                print(f"Updating product {product_id} with data: {product_update}")
                for key, value in product_update.items():
                    if hasattr(db_product, key):
                        setattr(db_product, key, value)
                db.commit()
                db.refresh(db_product)
                print(f"Successfully updated product {product_id}")
            else:
                print(f"Product {product_id} not found for update")
            return db_product
        except Exception as e:
            print(f"Error updating product {product_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def delete_product(db: Session, product_id: int) -> bool:
        """Soft delete - mark as inactive"""
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                print(f"Soft deleting product {product_id}: {db_product.name}")
                db_product.is_active = False
                db.commit()
                print(f"Successfully soft deleted product {product_id}")
                return True
            else:
                print(f"Product {product_id} not found for deletion")
                return False
        except Exception as e:
            print(f"Error deleting product {product_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def restore_product(db: Session, product_id: int) -> Optional[Product]:
        """Restore a soft-deleted product"""
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                print(f"Restoring product {product_id}: {db_product.name}")
                db_product.is_active = True
                db.commit()
                db.refresh(db_product)
                print(f"Successfully restored product {product_id}")
            else:
                print(f"Product {product_id} not found for restoration")
            return db_product
        except Exception as e:
            print(f"Error restoring product {product_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def hard_delete_product(db: Session, product_id: int) -> bool:
        """Permanently delete a product"""
        try:
            db_product = db.query(Product).filter(Product.id == product_id).first()
            if db_product:
                print(f"Hard deleting product {product_id}: {db_product.name}")
                db.delete(db_product)
                db.commit()
                print(f"Successfully hard deleted product {product_id}")
                return True
            else:
                print(f"Product {product_id} not found for hard deletion")
                return False
        except Exception as e:
            print(f"Error hard deleting product {product_id}: {e}")
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
            print(f"Retrieved {len(category_list)} categories: {category_list}")
            return category_list
        except Exception as e:
            print(f"Error getting categories: {e}")
            raise

    @staticmethod
    def create_products_bulk(
        db: Session, products: List[ProductCreate]
    ) -> List[Product]:
        """Create multiple products at once"""
        try:
            print(f"Creating {len(products)} products in bulk")
            db_products = []
            for i, product_data in enumerate(products):
                print(f"Creating product {i+1}: {product_data.name}")
                db_product = Product(**product_data.dict())
                db.add(db_product)
                db_products.append(db_product)

            db.commit()
            for product in db_products:
                db.refresh(product)
            print(f"Successfully created {len(db_products)} products in bulk")
            return db_products
        except Exception as e:
            print(f"Error creating products in bulk: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_products_bulk(db: Session, updates: List[dict]) -> int:
        """Update multiple products at once"""
        try:
            print(f"Updating {len(updates)} products in bulk")
            updated_count = 0
            for i, update_data in enumerate(updates):
                if "id" not in update_data:
                    print(f"Update {i+1}: Missing id field, skipping")
                    continue

                product_id = update_data.pop("id")
                print(
                    f"Update {i+1}: Updating product {product_id} with data: {update_data}"
                )
                db_product = db.query(Product).filter(Product.id == product_id).first()

                if db_product:
                    for key, value in update_data.items():
                        if hasattr(db_product, key):
                            setattr(db_product, key, value)
                    updated_count += 1
                    print(f"Update {i+1}: Successfully updated product {product_id}")
                else:
                    print(f"Update {i+1}: Product {product_id} not found")

            db.commit()
            print(f"Successfully updated {updated_count} products in bulk")
            return updated_count
        except Exception as e:
            print(f"Error updating products in bulk: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_product_stats(db: Session) -> dict:
        """Get product statistics"""
        try:
            from sqlalchemy import func

            print("Calculating product statistics...")

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

            print(
                f"Product stats calculated: {total_products} total, {active_products} active, {low_stock_count} low stock"
            )
            return stats
        except Exception as e:
            print(f"Error calculating product stats: {e}")
            raise


class StreamSessionService:
    @staticmethod
    def create_session(db: Session, session_data: StreamSessionCreate) -> StreamSession:
        try:
            print(
                f"Creating session: {session_data.title} with {len(session_data.product_ids)} products"
            )
            print(f"Using avatar_path: {session_data.avatar_path}")

            # Get or create avatar from path
            from src.services import AvatarService

            avatar = AvatarService.get_or_create_avatar(db, session_data.avatar_path)
            print(f"Avatar resolved: {avatar.name} (ID: {avatar.id})")

            # Create stream session
            db_session = StreamSession(
                title=session_data.title,
                description=session_data.description,
                avatar_id=avatar.id,
                status="preparing",
            )
            db.add(db_session)
            db.commit()
            db.refresh(db_session)

            # Add products to session
            for i, product_id in enumerate(session_data.product_ids):
                stream_product = StreamProduct(
                    session_id=db_session.id,
                    product_id=product_id,
                    order_in_stream=i + 1,
                )
                db.add(stream_product)

            db.commit()
            print(
                f"Successfully created session {db_session.id}: {db_session.title} with avatar {avatar.name}"
            )
            return db_session
        except Exception as e:
            print(f"Error creating session: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_sessions(
        db: Session, skip: int = 0, limit: int = 100
    ) -> List[StreamSession]:
        try:
            sessions = db.query(StreamSession).offset(skip).limit(limit).all()
            print(f"Retrieved {len(sessions)} sessions")
            return sessions
        except Exception as e:
            print(f"Error getting sessions: {e}")
            raise

    @staticmethod
    def get_session(db: Session, session_id: int) -> Optional[StreamSession]:
        try:
            session = (
                db.query(StreamSession).filter(StreamSession.id == session_id).first()
            )
            print(
                f"Retrieved session {session_id}: {'Found' if session else 'Not found'}"
            )
            return session
        except Exception as e:
            print(f"Error getting session {session_id}: {e}")
            raise

    @staticmethod
    def get_session_products(db: Session, session_id: int) -> List[StreamProduct]:
        try:
            products = (
                db.query(StreamProduct)
                .filter(StreamProduct.session_id == session_id)
                .order_by(StreamProduct.order_in_stream)
                .all()
            )
            print(f"Retrieved {len(products)} products for session {session_id}")
            return products
        except Exception as e:
            print(f"Error getting session products for session {session_id}: {e}")
            raise

    @staticmethod
    def update_session_status(
        db: Session, session_id: int, status: str
    ) -> Optional[StreamSession]:
        try:
            db_session = (
                db.query(StreamSession).filter(StreamSession.id == session_id).first()
            )
            if db_session:
                print(
                    f"Updating session {session_id} status from {db_session.status} to {status}"
                )
                db_session.status = status
                db.commit()
                db.refresh(db_session)
                print(f"Successfully updated session {session_id} status to {status}")
            else:
                print(f"Session {session_id} not found for status update")
            return db_session
        except Exception as e:
            print(f"Error updating session {session_id} status: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_stream_product(
        db: Session, stream_product_id: int, update_data: dict
    ) -> Optional[StreamProduct]:
        try:
            print(
                f"Updating stream product {stream_product_id} with data: {update_data}"
            )
            db_stream_product = (
                db.query(StreamProduct)
                .filter(StreamProduct.id == stream_product_id)
                .first()
            )
            if db_stream_product:
                for key, value in update_data.items():
                    setattr(db_stream_product, key, value)
                db.commit()
                db.refresh(db_stream_product)
                print(f"Successfully updated stream product {stream_product_id}")
            else:
                print(f"Stream product {stream_product_id} not found")
            return db_stream_product
        except Exception as e:
            print(f"Error updating stream product {stream_product_id}: {e}")
            db.rollback()
            raise


class CommentService:
    @staticmethod
    def create_comment(db: Session, session_id: int, comment: CommentCreate) -> Comment:
        try:
            print(
                f"Creating comment for session {session_id}: {comment.username} - {comment.message[:50]}..."
            )
            db_comment = Comment(session_id=session_id, **comment.dict())
            db.add(db_comment)
            db.commit()
            db.refresh(db_comment)
            print(f"Successfully created comment {db_comment.id}")
            return db_comment
        except Exception as e:
            print(f"Error creating comment for session {session_id}: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_session_comments(
        db: Session, session_id: int, skip: int = 0, limit: int = 100
    ) -> List[Comment]:
        try:
            comments = (
                db.query(Comment)
                .filter(Comment.session_id == session_id)
                .order_by(Comment.timestamp.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            print(f"Retrieved {len(comments)} comments for session {session_id}")
            return comments
        except Exception as e:
            print(f"Error getting comments for session {session_id}: {e}")
            raise

    @staticmethod
    def get_unanswered_questions(db: Session, session_id: int) -> List[Comment]:
        try:
            questions = (
                db.query(Comment)
                .filter(
                    Comment.session_id == session_id,
                    Comment.is_question == True,
                    Comment.answered == False,
                )
                .order_by(Comment.timestamp)
                .all()
            )
            print(
                f"Retrieved {len(questions)} unanswered questions for session {session_id}"
            )
            return questions
        except Exception as e:
            print(f"Error getting unanswered questions for session {session_id}: {e}")
            raise

    @staticmethod
    def mark_comment_answered(db: Session, comment_id: int) -> Optional[Comment]:
        try:
            print(f"Marking comment {comment_id} as answered")
            db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if db_comment:
                db_comment.answered = True
                db.commit()
                db.refresh(db_comment)
                print(f"Successfully marked comment {comment_id} as answered")
            else:
                print(f"Comment {comment_id} not found")
            return db_comment
        except Exception as e:
            print(f"Error marking comment {comment_id} as answered: {e}")
            db.rollback()
            raise

    @staticmethod
    def update_comment_answer_video(
        db: Session, comment_id: int, video_path: str
    ) -> Optional[Comment]:
        """Update comment with answer video path and mark as answered"""
        try:
            print(f"Updating comment {comment_id} with answer video: {video_path}")
            db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if db_comment:
                db_comment.answered = True
                db_comment.answer_video_path = video_path
                db.commit()
                db.refresh(db_comment)
                print(f"Successfully updated comment {comment_id} with answer video")
            else:
                print(f"Comment {comment_id} not found")
            return db_comment
        except Exception as e:
            print(f"Error marking comment {comment_id} as answered: {e}")
            db.rollback()
            raise


class ScriptTemplateService:
    @staticmethod
    def create_template(db: Session, template: ScriptTemplateCreate) -> ScriptTemplate:
        try:
            print(f"Creating template: {template.name}")
            db_template = ScriptTemplate(**template.dict())
            db.add(db_template)
            db.commit()
            db.refresh(db_template)
            print(f"Successfully created template {db_template.id}: {db_template.name}")
            return db_template
        except Exception as e:
            print(f"Error creating template: {e}")
            db.rollback()
            raise

    @staticmethod
    def get_templates(
        db: Session, category: Optional[str] = None
    ) -> List[ScriptTemplate]:
        try:
            query = db.query(ScriptTemplate).filter(ScriptTemplate.is_active == True)
            if category:
                query = query.filter(ScriptTemplate.category == category)
            templates = query.all()
            print(
                f"Retrieved {len(templates)} templates{f' for category {category}' if category else ''}"
            )
            return templates
        except Exception as e:
            print(f"Error getting templates: {e}")
            raise

    @staticmethod
    def get_template(db: Session, template_id: int) -> Optional[ScriptTemplate]:
        try:
            template = (
                db.query(ScriptTemplate)
                .filter(
                    ScriptTemplate.id == template_id, ScriptTemplate.is_active == True
                )
                .first()
            )
            print(
                f"Retrieved template {template_id}: {'Found' if template else 'Not found'}"
            )
            return template
        except Exception as e:
            print(f"Error getting template {template_id}: {e}")
            raise


# Initialize database with sample data
def init_sample_data(db: Session):
    """Initialize database with sample products and templates"""
    try:
        print("Initializing sample data...")

        # Check if data already exists
        if db.query(Product).first():
            print("Sample data already exists, skipping initialization")
            return

        # Sample products
        sample_products = [
            {
                "name": "iPhone 15 Pro Max",
                "description": "Smartphone cao cấp với chip A17 Pro, camera 48MP, màn hình 6.7 inch",
                "price": 29999000,
                "category": "Electronics",
                "stock_quantity": 50,
                "image_url": "https://example.com/iphone15.jpg",
            },
            {
                "name": "MacBook Air M2",
                "description": "Laptop siêu mỏng với chip M2, 13.6 inch, 8GB RAM, 256GB SSD",
                "price": 27999000,
                "category": "Electronics",
                "stock_quantity": 30,
                "image_url": "https://example.com/macbook.jpg",
            },
            {
                "name": "AirPods Pro 2",
                "description": "Tai nghe không dây với chống ồn chủ động, chip H2",
                "price": 5999000,
                "category": "Electronics",
                "stock_quantity": 100,
                "image_url": "https://example.com/airpods.jpg",
            },
            {
                "name": "Apple Watch Series 9",
                "description": "Đồng hồ thông minh với GPS, màn hình Always-On Retina",
                "price": 8999000,
                "category": "Electronics",
                "stock_quantity": 75,
                "image_url": "https://example.com/watch.jpg",
            },
        ]

        for product_data in sample_products:
            product = Product(**product_data)
            db.add(product)

        # Sample script templates
        sample_templates = [
            {
                "name": "Product Introduction",
                "template": """Xin chào các bạn! Hôm nay tôi rất vui được giới thiệu đến các bạn sản phẩm {product_name}. 

    {product_description}

    Với mức giá chỉ {price} VNĐ, đây thực sự là một cơ hội tuyệt vời mà các bạn không nên bỏ lỡ. 

    Sản phẩm này có những đặc điểm nổi bật như: {features}

    Hiện tại chúng tôi chỉ còn {stock_quantity} sản phẩm trong kho, vì vậy các bạn hãy nhanh tay đặt hàng để không bỏ lỡ cơ hội này nhé!

    Các bạn có câu hỏi gì về sản phẩm này không? Tôi sẽ trả lời ngay cho các bạn!""",
                "category": "introduction",
            },
            {
                "name": "Product Features Detail",
                "template": """Bây giờ tôi sẽ đi sâu vào chi tiết về {product_name}.

    {detailed_description}

    Những lợi ích mà sản phẩm này mang lại cho các bạn:
    - {benefit_1}
    - {benefit_2}
    - {benefit_3}

    So với các sản phẩm cùng loại trên thị trường, {product_name} có những ưu điểm vượt trội:
    {comparison}

    Đặc biệt hôm nay, chúng tôi có chương trình khuyến mãi đặc biệt cho {product_name}. Các bạn sẽ được:
    - Miễn phí vận chuyển
    - Bảo hành chính hãng
    - Hỗ trợ kỹ thuật 24/7

    Các bạn còn điều gì thắc mắc về sản phẩm này không?""",
                "category": "detailed",
            },
        ]

        for template_data in sample_templates:
            template = ScriptTemplate(**template_data)
            db.add(template)

            db.commit()
            print("Sample data initialized successfully!")

    except Exception as e:
        print(f"Error initializing sample data: {e}")
        db.rollback()
        raise


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database configuration
DATABASE_URL = "sqlite:///./virtual_streamer.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


# Database dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables
def create_tables():
    """Create all tables"""
    try:
        from src.models import (
            Product,
            StreamSession,
            StreamProduct,
            Comment,
            ScriptTemplate,
            Avatar,
        )

        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise
