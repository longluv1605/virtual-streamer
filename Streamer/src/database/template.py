from sqlalchemy.orm import Session
from src.models import ScriptTemplate, ScriptTemplateCreate
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] <%(name)s:%(lineno)d> - %(message)s")
logger = logging.getLogger(__name__)

class ScriptTemplateDatabaseService:
    @staticmethod
    def create_template(db: Session, template: ScriptTemplateCreate) -> ScriptTemplate:
        try:
            logger.info(f"Creating template: {template.name}")
            db_template = ScriptTemplate(**template.dict())
            db.add(db_template)
            db.commit()
            db.refresh(db_template)
            logger.info(f"Successfully created template {db_template.id}: {db_template.name}")
            return db_template
        except Exception as e:
            logger.error(f"Error creating template: {e}")
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
            logger.info(
                f"Retrieved {len(templates)} templates{f' for category {category}' if category else ''}"
            )
            return templates
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
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
            logger.info(
                f"Retrieved template {template_id}: {'Found' if template else 'Not found'}"
            )
            return template
        except Exception as e:
            logger.error(f"Error getting template {template_id}: {e}")
            raise
