from typing import List, Optional
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

from app.db.models import Card, CardType, Project
from app.schemas.card import CardCreate, CardUpdate, CardTypeCreate, CardTypeUpdate
import logging
# Import dynamic info model
from app.schemas.entity import UpdateDynamicInfo, CharacterCard, DynamicInfoItem
from sqlalchemy import update as sa_update

logger = logging.getLogger(__name__)

# Suggested max items per dynamic info type (retain more important/newer ones if exceeded). Adjust as needed.
MAX_ITEMS_BY_TYPE: dict[str, int] = {
    "心理想法/目标快照": 3,
    "等级/修为境界": 4,
    "功法/技能": 6,
    "装备/法宝": 4,
    "知识/情报": 4,
    "资产/领地": 4,
    "血脉/体质": 4,
    # DynamicInfoType.CONNECTION: 5,
}

# Global weight threshold (default 0.45)
WEIGHT_THRESHOLD =0.45

# ---- : Subtree Tools ----

def _fetch_children(db: Session, parent_ids: List[int]) -> List[Card]:
    """Fetch immediate children of given parent IDs."""
    if not parent_ids:
        return []
    stmt = select(Card).where(Card.parent_id.in_(parent_ids))
    return db.exec(stmt).all()


def _collect_subtree(db: Session, root: Card) -> List[Card]:
    """BFS collect entire subtree including root (order: parent first, children later)."""
    result: List[Card] = []
    queue: List[Card] = [root]
    while queue:
        node = queue.pop(0)
        result.append(node)
        children = _fetch_children(db, [node.id])
        queue.extend(children)
    return result


def _next_display_order(db: Session, project_id: int, parent_id: Optional[int]) -> int:
    """Calculate the next display order for a new card under a parent."""
    stmt = select(Card).where(Card.project_id == project_id, Card.parent_id == parent_id)
    siblings = db.exec(stmt).all()
    return len(siblings)


def _shallow_clone(src: Card, project_id: int, parent_id: Optional[int], display_order: int) -> Card:
    """Create a shallow copy of a card."""
    return Card(
        title=src.title,
        model_name=src.model_name,
        content=dict(src.content or {}),
        parent_id=parent_id,
        card_type_id=src.card_type_id,
        json_schema=dict(src.json_schema or {}) if src.json_schema is not None else None,
        ai_params=dict(src.ai_params or {}) if src.ai_params is not None else None,
        project_id=project_id,
        display_order=display_order,
        ai_context_template=src.ai_context_template,
    )

# ---- Title Suffix Generation ----

def _generate_non_conflicting_title(db: Session, project_id: int, base_title: str) -> str:
    """Generate a unique title by appending a number suffix if necessary."""
    title = (base_title or '').strip() or 'New Card'
    # Collect all titles starting with base_title and form base_title(number) in same project
    stmt = select(Card.title).where(Card.project_id == project_id)
    titles = db.exec(stmt).all() or []
    existing_titles = set(titles)
    if title not in existing_titles:
        return title
    # Find max suffix
    import re
    pattern = re.compile(rf"^{re.escape(title)}\((\d+)\)$")
    max_n = 0
    for t in existing_titles:
        m = pattern.match(str(t))
        if m:
            try:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
            except Exception:
                continue
    return f"{title}({max_n + 1})"


class CardService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_for_project(self, project_id: int) -> List[Card]:
        """
        Get all cards for a project.

        Args:
            project_id: Project ID.

        Returns:
            List of cards sorted by display order.
        """
        # Get all cards for project, tree structure will be built on client.
        statement = (
            select(Card)
            .where(Card.project_id == project_id)
            .order_by(Card.display_order)
        )
        cards = self.db.exec(statement).all()
        return cards

    def get_by_id(self, card_id: int) -> Optional[Card]:
        """
        Get a card by ID.

        Args:
            card_id: Card ID.

        Returns:
            Card object or None if not found.
        """
        return self.db.get(Card, card_id)

    def create(self, card_create: CardCreate, project_id: int) -> Card:
        """
        Create a new card.

        Args:
            card_create: Card creation data.
            project_id: Project ID.

        Returns:
            Created Card object.

        Raises:
            HTTPException: If card type not found or singleton constraint violated.
        """

        card_type = self.db.get(CardType, card_create.card_type_id)
        if not card_type:
             raise HTTPException(status_code=404, detail=f"CardType with id {card_create.card_type_id} not found")

        # Singleton restriction: Allow in reserved project (__free__)
        proj = self.db.get(Project, project_id)
        is_free_project = getattr(proj, 'name', None) == "__free__"
        if card_type.is_singleton and not is_free_project:
            statement = select(Card).where(Card.project_id == project_id, Card.card_type_id == card_create.card_type_id)
            existing_card = self.db.exec(statement).first()
            if existing_card:
                raise HTTPException(
                    status_code=409, # Conflict
                    detail=f"A card of type '{card_type.name}' already exists in this project, and it is a singleton."
                )

        # Determine display order
        statement = select(Card).where(Card.project_id == project_id, Card.parent_id == card_create.parent_id)
        sibling_cards = self.db.exec(statement).all()
        display_order = len(sibling_cards)

        # If ai_context_template not explicitly provided, inherit default from card type
        ai_context_template = getattr(card_create, 'ai_context_template', None)
        # Free card default no context injection: force clear template
        if is_free_project:
            ai_context_template = None
        elif not ai_context_template:
            ai_context_template = card_type.default_ai_context_template

        # Auto handle title conflict: append (n) to duplicate title
        final_title = _generate_non_conflicting_title(self.db, project_id, getattr(card_create, 'title', '') or card_type.name)

        card = Card(
            **{ **card_create.model_dump(), 'title': final_title },
            project_id=project_id,
            display_order=display_order,
            ai_context_template=ai_context_template,
        )
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return card

    @staticmethod
    def create_initial_cards_for_project(db: Session, project_id: int, template_items: Optional[List[dict]] = None):
        """
        Create initial card set for new project.

        Args:
            db: Database session.
            project_id: Project ID.
            template_items: Optional list of template items defining initial cards.
                            Format: List[ { card_type_id: int, display_order: int, title_override?: str } ]
                            If None, uses built-in default list.
        """
        if template_items is None:
            initial_cards_setup = {
                "作品标签": {"order": 0},
                "金手指": {"order": 1},
                "一句话梗概": {"order": 2},
                "故事大纲": {"order": 3},
                "世界观设定": {"order": 4},
                "核心蓝图": {"order": 5},
            }

            for card_type_name, setup in initial_cards_setup.items():
                try:
                    statement = select(CardType).where(CardType.name == card_type_name)
                    card_type = db.exec(statement).first()
                    if card_type:
                        # Create card
                        new_card = Card(
                            title=card_type_name,
                            content={},
                            project_id=project_id,
                        card_type_id=card_type.id,
                            display_order=setup["order"],
                            ai_context_template=card_type.default_ai_context_template,
                        )
                    db.add(new_card)
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed creating initial card for type {card_type_name}: {e}")
            return

        # Create using template items
        for item in sorted(template_items, key=lambda x: x.get('display_order', 0)):
            try:
                ct = db.get(CardType, item['card_type_id'])
                if not ct:
                    continue
                title = item.get('title_override') or ct.name
                new_card = Card(
                    title=title,
                    content={},
                    project_id=project_id,
                    card_type_id=ct.id,
                    display_order=item.get('display_order', 0),
                    ai_context_template=ct.default_ai_context_template,
                )
                db.add(new_card)
                db.commit()
            except Exception as e:
                logger.error(f"Failed creating initial card by template item {item}: {e}")
        return

    def update(self, card_id: int, card_update: CardUpdate) -> Optional[Card]:
        """
        Update an existing card.

        Args:
            card_id: ID of the card to update.
            card_update: Update data.

        Returns:
            Updated Card object or None if not found.
        """
        card = self.get_by_id(card_id)
        if not card:
            return None
            
        update_data = card_update.model_dump(exclude_unset=True)

        # If parent_id changed, we need to update display_order
        if 'parent_id' in update_data and card.parent_id != update_data['parent_id']:
            # Logic might be complex. Just append to end for now.
            statement = select(Card).where(Card.project_id == card.project_id, Card.parent_id == update_data['parent_id'])
            sibling_cards = self.db.exec(statement).all()
            update_data['display_order'] = len(sibling_cards)


        for key, value in update_data.items():
            setattr(card, key, value)
            
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return card

    def delete(self, card_id: int) -> bool:
        """
        Delete a card.

        Args:
            card_id: ID of the card to delete.

        Returns:
            True if deleted, False if not found.
        """
        # Recursive delete handled by cascade option in relationship
        card = self.get_by_id(card_id)
        if not card:
            return False
        self.db.delete(card)
        self.db.commit()
        return True 

    # ---- Move and Copy ----
    def move_card(self, card_id: int, target_project_id: int, parent_id: Optional[int] = None) -> Optional[Card]:
        """
        Move a card (and its subtree) to another project or parent.

        Args:
            card_id: ID of the card to move.
            target_project_id: ID of the target project.
            parent_id: ID of the new parent card (optional).

        Returns:
            The moved Card object.

        Raises:
            HTTPException: If invalid move operation (cycle, not found, singleton conflict).
        """
        root = self.get_by_id(card_id)
        if not root:
            return None
        # Collect subtree
        subtree = _collect_subtree(self.db, root)
        id_set = {c.id for c in subtree}
        # Check: If parent_id specified, cannot set parent to a descendant of itself (avoid cycle)
        if parent_id and parent_id in id_set and parent_id != root.id:
            raise HTTPException(status_code=400, detail="Cannot set parent to a descendant of itself")
        # Target parent project check
        if parent_id is not None:
            parent_card = self.get_by_id(parent_id)
            if not parent_card:
                raise HTTPException(status_code=404, detail="Target parent card not found")
            if parent_card.project_id != target_project_id:
                raise HTTPException(status_code=400, detail="Target parent card not in target project")
        # Non-reserved project singleton restriction (check when moving across projects)
        if target_project_id != root.project_id:
            target_proj = self.db.get(Project, target_project_id)
            is_target_free = getattr(target_proj, 'name', None) == "__free__"
            if root.card_type and getattr(root.card_type, 'is_singleton', False) and not is_target_free:
                exists_stmt = select(Card).where(Card.project_id == target_project_id, Card.card_type_id == root.card_type_id)
                exists = self.db.exec(exists_stmt).first()
                if exists:
                    raise HTTPException(status_code=409, detail=f"A card of type '{root.card_type.name}' already exists in target project (singleton)")
        # Update project ID (entire subtree)
        for node in subtree:
            node.project_id = target_project_id
        # Adjust root parent and display order
        root.parent_id = parent_id
        # Singleton restriction: Allow multiple same types in reserved project (__free__), so display_order also allow append directly
        root.display_order = _next_display_order(self.db, target_project_id, parent_id)
        # Commit
        for node in subtree:
            self.db.add(node)
        self.db.commit()
        self.db.refresh(root)
        return root

    def copy_card(self, card_id: int, target_project_id: int, parent_id: Optional[int] = None) -> Optional[Card]:
        """
        Copy a card (and its subtree) to another project or parent.

        Args:
            card_id: ID of the card to copy.
            target_project_id: ID of the target project.
            parent_id: ID of the new parent card (optional).

        Returns:
            The new root Card object of the copied subtree.

        Raises:
            HTTPException: If singleton conflict.
        """
        src_root = self.get_by_id(card_id)
        if not src_root:
            return None
        # Non-reserved project singleton restriction (check root type when copying to target)
        target_proj = self.db.get(Project, target_project_id)
        is_target_free = getattr(target_proj, 'name', None) == "__free__"
        if src_root.card_type and getattr(src_root.card_type, 'is_singleton', False) and not is_target_free:
            exists_stmt = select(Card).where(Card.project_id == target_project_id, Card.card_type_id == src_root.card_type_id)
            exists = self.db.exec(exists_stmt).first()
            if exists:
                raise HTTPException(status_code=409, detail=f"A card of type '{src_root.card_type.name}' already exists in target project (singleton)")
        # Collect subtree, copy in order of parent first
        subtree = _collect_subtree(self.db, src_root)
        old_to_new_id: dict[int, int] = {}
        new_nodes_by_old_id: dict[int, Card] = {}
        for node in subtree:
            # Calculate new parent ID
            if node.id == src_root.id:
                new_parent_id = parent_id
                new_order = _next_display_order(self.db, target_project_id, new_parent_id)
            else:
                old_parent_id = node.parent_id
                new_parent_id = old_to_new_id.get(old_parent_id) if old_parent_id is not None else None
                new_order = _next_display_order(self.db, target_project_id, new_parent_id)
            clone = _shallow_clone(node, target_project_id, new_parent_id, new_order)
            # Avoid title conflict when copying too
            clone.title = _generate_non_conflicting_title(self.db, target_project_id, clone.title)
            self.db.add(clone)
            self.db.commit()
            self.db.refresh(clone)
            old_to_new_id[node.id] = clone.id
            new_nodes_by_old_id[node.id] = clone
        return new_nodes_by_old_id.get(src_root.id)


class CardTypeService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[CardType]:
        """Get all card types."""
        return self.db.exec(select(CardType)).all()

    def get_by_id(self, card_type_id: int) -> Optional[CardType]:
        """Get a card type by ID."""
        return self.db.get(CardType, card_type_id)
        
    def create(self, card_type_create: CardTypeCreate) -> CardType:
        """Create a new card type."""
        card_type = CardType.model_validate(card_type_create)
        self.db.add(card_type)
        self.db.commit()
        self.db.refresh(card_type)
        return card_type

    def update(self, card_type_id: int, card_type_update: CardTypeUpdate) -> Optional[CardType]:
        """Update an existing card type."""
        card_type = self.get_by_id(card_type_id)
        if not card_type:
            return None
        for key, value in card_type_update.model_dump(exclude_unset=True).items():
            setattr(card_type, key, value)
        self.db.add(card_type)
        self.db.commit()
        self.db.refresh(card_type)
        return card_type

    def delete(self, card_type_id: int) -> bool:
        """Delete a card type."""
        card_type = self.get_by_id(card_type_id)
        if not card_type:
            return False
        # Consider cascading deletes or checks for associated cards
        self.db.delete(card_type)
        self.db.commit()
        return True
