"""
Inspiration Assistant Tool Functions Collection
"""
import json
from typing import Dict, Any, List, Optional
from pydantic_ai import RunContext
from loguru import logger
from app.services import nodes
from app.db.models import Card, CardType
import copy

class AssistantDeps:
    """Inspiration Assistant Dependencies (Used to pass session and project_id)"""
    def __init__(self, session, project_id: int):
        self.session = session
        self.project_id = project_id


def search_cards(
    ctx: RunContext[AssistantDeps],
    card_type: Optional[str] = None,
    title_keyword: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search cards in the project
    
    Args:
        ctx: Pydantic AI RunContext containing AssistantDeps.
        card_type: Card type name (Optional).
        title_keyword: Title keyword (Optional).
        limit: Max number of results (default 10).
    
    Returns:
        A dictionary containing:
        - success: True if successful, False otherwise.
        - error: Error message (if applicable).
        - cards: List of found cards (id, title, type).
        - count: Number of cards found.
    """
    logger.info(f" [PydanticAI.search_cards] card_type={card_type}, keyword={title_keyword}")
    
    query = ctx.deps.session.query(Card).filter(Card.project_id == ctx.deps.project_id)
    
    if card_type:
        query = query.join(CardType).filter(CardType.name == card_type)
    
    if title_keyword:
        query = query.filter(Card.title.ilike(f'%{title_keyword}%'))
    
    cards = query.limit(limit).all()
    
    result = {
        "success": True,
        "cards": [
            {
                "id": c.id,
                "title": c.title,
                "type": c.card_type.name if c.card_type else "Unknown"
            }
            for c in cards
        ],
        "count": len(cards)
    }
    
    logger.info(f"✅ [PydanticAI.search_cards] Found {len(cards)} cards")
    return result


def create_card(
    ctx: RunContext[AssistantDeps],
    card_type: str,
    title: str,
    content: Dict[str, Any],
    parent_card_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a new card
    
    Examples:
        # Create a character card in project root
        create_card(card_type="Character Card", title="John Doe", content={...})
        
        # Create a chapter outline under a volume outline (card_id=42)
        create_card(card_type="Chapter Outline", title="Chapter 1", content={...}, parent_card_id=42)
    
    Args:
        ctx: Pydantic AI RunContext containing AssistantDeps.
        card_type: Card type name (e.g. Character Card, Chapter Outline, Worldview Setting etc.).
        title: Card title.
        content: Card content (Dictionary, must conform to the type's Schema).
        parent_card_id: Parent card ID (Optional).
            * If provided, create sub-card under specified card.
            * If not provided, create in project root.
    
    Returns:
        A dictionary containing:
        - success: True if successful, False otherwise.
        - error: Error message (if failed).
        - card_id: Card ID.
        - card_title: Card Title.
        - card_type: Card Type.
        - parent_id: Parent Card ID (None means created in root).
        - parent_title: Parent Card Title (If parent exists).
        - parent_type: Parent Card Type (If parent exists).
        - message: User friendly message.
    """
    
    logger.info(f" [PydanticAI.create_card] type={card_type}, title={title}, parent_id={parent_card_id}")
    
    state = {
        "scope": {
            "project_id": ctx.deps.project_id
        },
        "touched_card_ids": set()
    }
    
    # Build params, if parent_card_id provided, add to parent parameter
    params = {
        "cardType": card_type,
        "title": title,
        "contentMerge": content
    }
    
    if parent_card_id is not None:
        params["parent"] = parent_card_id
        logger.info(f"  Specified Parent Card ID: {parent_card_id}")
    else:
        params["parent"] = "$projectRoot"
        logger.info(f"  Creating in project root")
    
    result = nodes.node_card_upsert_child_by_title(
        session=ctx.deps.session,
        state=state,
        params=params
    )
    
    # Commit transaction (Important!)
    ctx.deps.session.commit()
    
    logger.info(f"✅ [PydanticAI.create_card] Creation success: {result}")
    
    # Get created card to return full info
    created_card = result.get("card")
    response = {
        "success": True,
        "card_id": created_card.id if created_card else result.get("card_id"),
        "card_title": created_card.title if created_card else result.get("card_title", title),
        "card_type": card_type,
        "parent_id": created_card.parent_id if created_card else parent_card_id,
        "message": f"✅ Created {card_type} '{title}'"
    }
    
    # If parent card exists, add parent info
    if created_card and created_card.parent_id and created_card.parent:
        response["parent_title"] = created_card.parent.title
        response["parent_type"] = created_card.parent.card_type.name if created_card.parent.card_type else "Unknown"
    
    return response


def modify_card_field(
    ctx: RunContext[AssistantDeps],
    card_id: int,
    field_path: str,
    new_value: Any
) -> Dict[str, Any]:
    """
    Modify field content of a specified card
    
    Use case: Must call this tool when user requests to write content into a card
    
    Examples:
        - modify_card_field(card_id=27, field_path="overview", new_value="This is new overview content...")
        - modify_card_field(card_id=15, field_path="content.name", new_value="Lin Feng")
        - modify_card_field(card_id=8, field_path="chapter_outline_list", new_value=[...])
    
    Args:
        ctx: Pydantic AI RunContext containing AssistantDeps.
        card_id: Target card ID (Find from project structure tree).
        field_path: Field path, supports two formats:
            * Simple field: "overview", "stage_name" etc.
            * Nested field: "content.overview", "content.chapter_outline_list" etc.
        new_value: New value to set (Can be string, number, list, dict etc.).
    
    Returns:
        A dictionary containing:
        - success: True if successful, False otherwise.
        - error: Error message.
        - card_id: Card ID.
        - card_title: Card Title.
        - field_path: Field Path.
        - new_value: New Value.
        - message: User friendly message.
    """
    logger.info(f" [PydanticAI.modify_card_field] card_id={card_id}, path={field_path}")
    logger.info(f"  New value type: {type(new_value)}")
    
    try:
        # Verify card existence
        card = ctx.deps.session.get(Card, card_id)
        if not card or card.project_id != ctx.deps.project_id:
            logger.warning(f"⚠️ Card {card_id} not found or not in current project")
            return {
                "success": False,
                "error": f"Card {card_id} not found or not in current project"
            }
        
        logger.info(f"  Card Title: {card.title}")
        logger.info(f"  Before Modify: {card.content}")
        
        # Construct state needed for workflow node
        state = {
            "card": card,
            "touched_card_ids": set()
        }
        
        # Call workflow node function
        nodes.node_card_modify_content(
            session=ctx.deps.session,
            state=state,
            params={
                "setPath": field_path,
                "setValue": new_value
            }
        )
        
        # Commit transaction (Important!)
        ctx.deps.session.commit()
        
        # Refresh card data
        ctx.deps.session.refresh(card)
        
        logger.info(f"  After Modify: {card.content}")
        logger.info(f"✅ [PydanticAI.modify_card_field] Modify success")
        
        return {
            "success": True,
            "card_id": card_id,
            "card_title": card.title,
            "field_path": field_path,
            "new_value": new_value,
            "message": f"✅ Updated '{field_path.replace('content.', '')}' of '{card.title}'"
        }
    
    except Exception as e:
        logger.error(f"❌ [PydanticAI.modify_card_field] Modify failed: {e}")
        return {
            "success": False,
            "error": f"Modify failed: {str(e)}"
        }


def batch_create_cards(
    ctx: RunContext[AssistantDeps],
    card_type: str,
    cards: List[Dict[str, Any]],
    parent_card_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Batch create cards of same type
    
    Args:
        ctx: Pydantic AI RunContext containing AssistantDeps.
        card_type: Card type name.
        cards: List of card data, each item contains title and content.
        parent_card_id: Parent card ID (Optional).
    
    Returns:
        A dictionary containing:
        - success: True if successful, False otherwise.
        - error: Error message.
        - total: Total cards.
        - success_count: Number of successfully created cards.
        - failed_count: Number of failed cards.
        - results: Creation result list.
    """
    logger.info(f" [PydanticAI.batch_create_cards] type={card_type}, count={len(cards)}")
    
    results = []
    
    for card_data in cards:
        try:
            title = card_data.get("title", "")
            content = card_data.get("content", {})
            
            result = create_card(ctx, card_type, title, content, parent_card_id)
            results.append({
                "title": title,
                "status": "success",
                "card_id": result["card_id"]
            })
        except Exception as e:
            logger.error(f"Batch create failed: {card_data.get('title', 'unknown')} - {e}")
            results.append({
                "title": card_data.get("title", "unknown"),
                "status": "failed",
                "error": str(e)
            })
    
    success_count = sum(1 for r in results if r["status"] == "success")
    
    logger.info(f"✅ [PydanticAI.batch_create_cards] Success {success_count}/{len(cards)}")
    
    return {
        "success": True,
        "total": len(cards),
        "success_count": success_count,
        "failed_count": len(cards) - success_count,
        "results": results
    }


def get_card_type_schema(
    ctx: RunContext[AssistantDeps],
    card_type_name: str
) -> Dict[str, Any]:
    """
    Get JSON Schema definition of specified card type
    
    Use case: Call when need to create card but unsure of its structure
    
    Args:
        ctx: Pydantic AI RunContext containing AssistantDeps.
        card_type_name: Card type name.
    
    Returns:
        A dictionary containing:
        - success: True if successful, False otherwise.
        - error: Error message.
        - card_type: Card type name.
        - schema: JSON Schema definition of card type.
        - description: Description of card type.
    """
    logger.info(f" [PydanticAI.get_card_type_schema] card_type={card_type_name}")
    
    card_type = ctx.deps.session.query(CardType).filter(
        CardType.name == card_type_name
    ).first()
    
    if not card_type:
        logger.warning(f"⚠️ [PydanticAI.get_card_type_schema] Card type '{card_type_name}' not found")
        return {
            "success": False,
            "error": f"Card type '{card_type_name}' not found"
        }
    
    result = {
        "success": True,
        "card_type": card_type_name,
        "schema": card_type.json_schema or {},
        "description": f"Complete structure definition of card type '{card_type_name}'"
    }
    
    logger.info(f"✅ [PydanticAI.get_card_type_schema] Returned Schema: {result}")
    return result


def get_card_content(
    ctx: RunContext[AssistantDeps],
    card_id: int
) -> Dict[str, Any]:
    """
    Get detailed content of specified card
    
    Use case: Call when need to view full data of a card
    
    Args:
        ctx: Pydantic AI RunContext containing AssistantDeps.
        card_id: Card ID.
    
    Returns:
        A dictionary containing:
        - success: True if successful, False otherwise.
        - error: Error message (if failed).
        - card_id: Card ID.
        - title: Card Title.
        - card_type: Card Type.
        - parent_id: Parent Card ID (None means root card).
        - parent_title: Parent Card Title (If parent exists).
        - parent_type: Parent Card Type (If parent exists).
        - content: Card Content.
        - created_at: Card Creation Time.
    """
    logger.info(f" [PydanticAI.get_card_content] card_id={card_id}")
    
    card = ctx.deps.session.query(Card).filter(Card.id == card_id).first()
    
    if not card:
        logger.warning(f"⚠️ [PydanticAI.get_card_content] Card #{card_id} not found")
        return {
            "success": False,
            "error": f"Card #{card_id} not found"
        }
    
    result = {
        "success": True,
        "card_id": card.id,
        "title": card.title,
        "card_type": card.card_type.name if card.card_type else "Unknown",
        "parent_id": card.parent_id,  # Parent Card ID, for hierarchy info
        "content": card.content or {},
        "created_at": str(card.created_at) if card.created_at else None
    }
    
    # If parent card exists, add parent info
    if card.parent_id and card.parent:
        result["parent_title"] = card.parent.title
        result["parent_type"] = card.parent.card_type.name if card.parent.card_type else "Unknown"
    
    logger.info(f"✅ [PydanticAI.get_card_content] Returned card content (parent_id={card.parent_id})")
    return result


def replace_field_text(
    ctx: RunContext[AssistantDeps],
    card_id: int,
    field_path: str,
    old_text: str,
    new_text: str
) -> Dict[str, Any]:
    """
    Replace specified text fragment in card field
    
    Use case: Call when user is unsatisfied with part of long text field content and wants to replace only that part
    Suitable for local modification of long text fields like chapter body, outline description etc.
    
    Examples:
        1. Exact match (Short text):
        replace_field_text(card_id=42, field_path="content", 
                            old_text="Lin Feng hesitated for a moment",
                            new_text="Lin Feng did not hesitate")
        
        2. Fuzzy match (Long text):
        replace_field_text(card_id=42, field_path="content",
                            old_text="The boy looked pale, veins popping on his forehead... now became a cripple.",
                            new_text="New complete paragraph content...")
    
    Args:
        ctx: Pydantic AI RunContext containing AssistantDeps.
        card_id: Target card ID.
        field_path: Field path (e.g. "content" for chapter body, "overview" for outline).
        old_text: Original text fragment to replace, supports two modes:
            1. Exact match: Provide complete original text (Suitable for short text, < 50 chars).
            2. Fuzzy match: Provide start 10 chars + "..." + end 10 chars (Suitable for long text, > 50 chars).
        new_text: New text content.
    
    Returns:
        A dictionary containing:
        - success: True if successful, False otherwise.
        - error: Error message.
        - card_title: Card Title.
        - replaced_count: Number of replacements.
        - message: User friendly message.
    """
    logger.info(f" [PydanticAI.replace_field_text] card_id={card_id}, path={field_path}")
    logger.info(f"  Text length to replace: {len(old_text)} chars")
    logger.info(f"  New text length: {len(new_text)} chars")
    
    try:
        # Verify card existence and ownership
        card = ctx.deps.session.get(Card, card_id)
        if not card or card.project_id != ctx.deps.project_id:
            logger.warning(f"⚠️ Card {card_id} not found or not in current project")
            return {
                "success": False,
                "error": f"Card {card_id} not found or not in current project"
            }
        
        logger.info(f"  Card Title: {card.title}")
        
        # Construct state needed for workflow node
        state = {
            "touched_card_ids": set()
        }
        
        # Call workflow node function
        result = nodes.node_card_replace_field_text(
            session=ctx.deps.session,
            state=state,
            params={
                "card_id": card_id,
                "field_path": field_path,
                "old_text": old_text,
                "new_text": new_text
            }
        )
        
        # If node execution failed, return error directly
        if not result.get("success"):
            logger.warning(f"⚠️ [PydanticAI.replace_field_text] Node execution failed: {result.get('error')}")
            return result
        
        # Commit transaction (Important!)
        ctx.deps.session.commit()
        
        logger.info(f"✅ [PydanticAI.replace_field_text] Replace success")
        
        # Add user friendly message
        result["message"] = f"✅ Replaced {result.get('replaced_count')} occurrences in '{field_path.replace('content.', '')}' of '{result.get('card_title')}'"
        
        return result
    
    except Exception as e:
        logger.error(f"❌ [PydanticAI.replace_field_text] Replace failed: {e}")
        return {
            "success": False,
            "error": f"Replace failed: {str(e)}"
        }




# Export all tool functions list (Pydantic AI standard way)
ASSISTANT_TOOLS = [
    search_cards,
    create_card,
    modify_card_field,
    replace_field_text,
    batch_create_cards,
    get_card_type_schema,
    get_card_content,
  
]


from pydantic_ai import Agent, ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

tools_schema=None

def _get_tools_json_schema(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """
    Internal helper to get tool schema.

    Args:
        messages: List of model messages.
        info: Agent info containing function tools.

    Returns:
        ModelResponse containing the JSON schema of tools.
    """
    tools=[]
    for tool in info.function_tools:
        tools.append({
            "name":tool.name,
            "description":tool.description,
            "parameters_json_schema":tool.parameters_json_schema
        })
    return ModelResponse(parts=[TextPart(json.dumps(tools,ensure_ascii=False))])

async def get_tools_schema():
    """
    Asynchronously get tool schema.

    Returns:
        List of tool schemas in JSON format.
    """
    global tools_schema
    if tools_schema is None:
        agent = Agent(tools=ASSISTANT_TOOLS)
        result = await agent.run('hello', model=FunctionModel(_get_tools_json_schema))
        # AgentRunResult uses .output attribute to get output
        tools_schema = json.loads(result.output)
    
    return tools_schema
