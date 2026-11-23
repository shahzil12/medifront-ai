from sqlalchemy.orm import Session
from app.models.user import AuditLog

def log_action(db: Session, user_id: int | None, action: str, entity: str, entity_id: int | None = None):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id
    )
    db.add(entry)
    db.commit()