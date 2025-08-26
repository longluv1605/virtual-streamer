from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.models import Base, Product, ScriptTemplate, Avatar

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "sqlite:///./virtual_streamer.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

# Initialize database with sample data
def init_sample_data(db: Session):
    """Initialize database with sample products and templates"""
    try:
        logger.info("Initializing sample data...")

        # Check if data already exists
        if db.query(Product).first():
            logger.info("Sample data already exists, skipping initialization")
            return

        # Sample products
        sample_products = [
            {
                "name": "iPhone 15 Pro Max",
                "description": "Smartphone cao cấp với chip A17 Pro, camera 48MP, màn hình 6.7 inch",
                "price": 29999000,
                "category": "Electronics",
                "stock_quantity": 50,
                "image_url": "https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-15-pro-max_2__5_2_1_1.jpg",
            },
            {
                "name": "MacBook Air M2",
                "description": "Laptop siêu mỏng với chip M2, 13.6 inch, 8GB RAM, 256GB SSD",
                "price": 27999000,
                "category": "Electronics",
                "stock_quantity": 30,
                "image_url": "https://cdn2.fptshop.com.vn/unsafe/macbook_air_13_m2_midnight_1_35053fbcf9.png",
            },
            {
                "name": "AirPods Pro 2",
                "description": "Tai nghe không dây với chống ồn chủ động, chip H2",
                "price": 5999000,
                "category": "Electronics",
                "stock_quantity": 100,
                "image_url": "https://store.storeimages.cdn-apple.com/1/as-images.apple.com/is/airpods-pro-2-hero-select-202409_FMT_WHH?wid=750&hei=556&fmt=jpeg&qlt=90&.v=1724041668836",
            },
            {
                "name": "Apple Watch Series 9",
                "description": "Đồng hồ thông minh với GPS, màn hình Always-On Retina",
                "price": 8999000,
                "category": "Electronics",
                "stock_quantity": 75,
                "image_url": "https://cdsassets.apple.com/live/7WUAS350/images/tech-specs/apple-watch-series-9.png",
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

        # Sample avatar
        sample_avatars = [
            {
                "video_path": "/static/avatars/long.mp4",
                "name": "Long",
                "default": True,
            },
            {
                "video_path": "/static/avatars/sun.mp4",
                "name": "Sun",
                "default": True,
            },
            {
                "video_path": "/static/avatars/yongen.mp4",
                "name": "Yongen",
                "default": True,
            },
        ]
        
        for avatar_data in sample_avatars:
            avatar = Avatar(**avatar_data)
            db.add(avatar)
            
        db.commit()
        logger.info("Sample data init successfully...")
        
    except Exception as e:
        logger.error(f"Error initializing sample data: {e}")
        db.rollback()
        raise

