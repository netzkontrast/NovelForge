from typing import List, Optional
from sqlmodel import Session, select
from app.db.models import Knowledge

class KnowledgeService:
    """
    Knowledge Base Service: Provides CRUD for knowledge bases.
    Note: Built-in (built_in=True) knowledge bases cannot be deleted.
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the service with a database session.

        Args:
            db: SQLModel Session.
        """
        self.db = db

    def list(self, skip: int = 0, limit: int = 200) -> List[Knowledge]:
        """
        List knowledge bases.

        Args:
            skip: Offset.
            limit: Limit.

        Returns:
            List of Knowledge objects.
        """
        return self.db.exec(select(Knowledge).offset(skip).limit(limit)).all()

    def get_by_id(self, kid: int) -> Optional[Knowledge]:
        """
        Get a knowledge base by ID.

        Args:
            kid: Knowledge base ID.

        Returns:
            Knowledge object or None.
        """
        return self.db.get(Knowledge, kid)

    def get_by_name(self, name: str) -> Optional[Knowledge]:
        """
        Get a knowledge base by name.

        Args:
            name: Knowledge base name.

        Returns:
            Knowledge object or None.
        """
        return self.db.exec(select(Knowledge).where(Knowledge.name == name)).first()

    def create(self, name: str, content: str, description: Optional[str] = None, built_in: bool = False) -> Knowledge:
        """
        Create a new knowledge base.

        Args:
            name: Name.
            content: Content.
            description: Description.
            built_in: Whether it is built-in.

        Returns:
            Created Knowledge object.
        """
        kb = Knowledge(name=name, content=content, description=description, built_in=built_in)
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def update(self, kid: int, name: Optional[str] = None, content: Optional[str] = None, description: Optional[str] = None) -> Optional[Knowledge]:
        """
        Update a knowledge base.

        Args:
            kid: Knowledge base ID.
            name: New name.
            content: New content.
            description: New description.

        Returns:
            Updated Knowledge object or None if not found.
        """
        kb = self.get_by_id(kid)
        if not kb:
            return None
        if name is not None:
            kb.name = name
        if description is not None:
            kb.description = description
        if content is not None:
            kb.content = content
        self.db.add(kb)
        self.db.commit()
        self.db.refresh(kb)
        return kb

    def delete(self, kid: int) -> bool:
        """
        Delete a knowledge base.

        Args:
            kid: Knowledge base ID.

        Returns:
            True if deleted, False if not found.

        Raises:
            ValueError: If attempting to delete a built-in knowledge base.
        """
        kb = self.get_by_id(kid)
        if not kb:
            return False
        if getattr(kb, 'built_in', False):
            raise ValueError("System built-in knowledge base cannot be deleted")
        self.db.delete(kb)
        self.db.commit()
        return True
