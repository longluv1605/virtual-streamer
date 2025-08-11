from sqlalchemy.orm import Session
from src.models import ScriptTemplate, ScriptTemplateCreate
from typing import List, Optional

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
