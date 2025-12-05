from __future__ import annotations

from typing import Any, Optional, List, Dict, Callable
import re
import copy
from sqlmodel import Session, select

from app.db.models import Card, CardType
from loguru import logger


# ==================== 节点注册机制 ====================
# 使用装饰器自动注册工作流节点，避免手动维护映射表

_NODE_REGISTRY: Dict[str, Callable] = {}


def register_node(node_type: str):
    """
    Decorator: Automatically register workflow nodes.
    
    Usage:
        @register_node("Card.Read")
        def node_card_read(session, state, params):
            ...

    Args:
        node_type: The string identifier for the node type.

    Returns:
        The decorated function.
    """
    def decorator(func: Callable):
        _NODE_REGISTRY[node_type] = func
        logger.debug(f"[节点注册] {node_type} -> {func.__name__}")
        return func
    return decorator


def get_registered_nodes() -> Dict[str, Callable]:
    """Get all registered nodes."""
    return _NODE_REGISTRY.copy()


def get_node_types() -> List[str]:
    """Get names of all registered node types."""
    return list(_NODE_REGISTRY.keys())


# ======================================================


def _parse_schema_fields(schema: dict, path: str = "$.content", max_depth: int = 5) -> List[dict]:
    """
    Parse JSON Schema field structure, supporting nested objects and references.
    Returns a list of fields, each containing: name, type, path, children(optional).
    """
    if max_depth <= 0:
        return []
    
    fields = []
    try:
        # 获取$defs用于解析引用
        defs = schema.get("$defs", {})
        
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            return fields
            
        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue
            
            # 解析引用
            resolved_schema = _resolve_schema_ref(field_schema, defs)
            
            field_type = resolved_schema.get("type", "unknown")
            field_title = resolved_schema.get("title", field_name)
            field_description = resolved_schema.get("description", "")
            field_path = f"{path}.{field_name}"
            
            field_info = {
                "name": field_name,
                "title": field_title,
                "type": field_type,
                "path": field_path,
                "description": field_description,
                "required": field_name in schema.get("required", []),
                "expanded": False
            }
            
            # 处理anyOf类型（可选类型）
            if "anyOf" in resolved_schema:
                non_null_schema = None
                for any_schema in resolved_schema["anyOf"]:
                    if isinstance(any_schema, dict) and any_schema.get("type") != "null":
                        non_null_schema = _resolve_schema_ref(any_schema, defs)
                        break
                if non_null_schema:
                    resolved_schema = non_null_schema
                    field_type = resolved_schema.get("type", "unknown")
                    field_info["type"] = field_type
            
            # 处理嵌套对象
            if field_type == "object" and "properties" in resolved_schema:
                children = _parse_schema_fields(resolved_schema, field_path, max_depth - 1)
                if children:
                    field_info["children"] = children
                    field_info["expandable"] = True
            
            # 处理数组类型
            elif field_type == "array" and "items" in resolved_schema:
                items_schema = resolved_schema["items"]
                items_resolved = _resolve_schema_ref(items_schema, defs)
                
                if items_resolved.get("type") == "object" and "properties" in items_resolved:
                    children = _parse_schema_fields(items_resolved, f"{field_path}[0]", max_depth - 1)
                    if children:
                        field_info["children"] = children
                        field_info["expandable"] = True
                        field_info["array_item_type"] = "object"
                else:
                    # 简单数组类型
                    field_info["array_item_type"] = items_resolved.get("type", "unknown")
            
            fields.append(field_info)
            
    except Exception as e:
        logger.warning(f"解析Schema字段失败: {e}")
    
    return fields


def _resolve_schema_ref(schema: dict, defs: dict) -> dict:
    """Resolve Schema references."""
    if not isinstance(schema, dict):
        return schema
    
    # 处理$ref引用
    if "$ref" in schema:
        ref_path = schema["$ref"]
        if ref_path.startswith("#/$defs/"):
            ref_name = ref_path.replace("#/$defs/", "")
            if ref_name in defs:
                resolved = defs[ref_name]
                # 保留原schema的title和description
                if "title" in schema:
                    resolved = {**resolved, "title": schema["title"]}
                if "description" in schema:
                    resolved = {**resolved, "description": schema["description"]}
                return resolved
    
    return schema


def _get_card_by_id(session: Session, card_id: int) -> Optional[Card]:
    """Helper to get card by ID."""
    try:
        return session.get(Card, int(card_id))
    except Exception:
        return None


def _get_by_path(obj: Any, path: str) -> Any:
    """Minimal JSONPath resolution."""
    if not path or not isinstance(path, str):
        return None
    if not path.startswith("$."):
        return None
    parts = path[2:].split(".")
    # 处理根 '$'：若 obj 为 {"$": base} 则先取出 base
    if isinstance(obj, dict) and "$" in obj:
        cur: Any = obj.get("$")
    else:
        cur = obj
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            try:
                cur = getattr(cur, p)
            except Exception:
                return None
    return cur


def _set_by_path(obj: Dict[str, Any], path: str, value: Any) -> bool:
    """
    Set value by JSONPath.
    
    Args:
        obj: Target object.
        path: JSONPath string (must start with $.).
        value: Value to set.
    
    Returns:
        bool: Success status.
    """
    if not isinstance(obj, dict) or not isinstance(path, str) or not path.startswith("$."):
        return False
    
    parts = path[2:].split(".")
    cur: Dict[str, Any] = obj
    
    # 遍历到倒数第二层，确保路径存在
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]  # type: ignore[assignment]
    
    # 设置最后一层的值
    cur[parts[-1]] = value
    return True


_TPL_PATTERN = re.compile(r"\{([^{}]+)\}")


def _resolve_expr(expr: str, state: dict) -> Any:
    """Resolve expression string against state."""
    expr = expr.strip()
    # index（循环序号，从 1 开始）
    if expr == "index":
        return (state.get("item") or {}).get("index")
    # item.xxx
    if expr.startswith("item."):
        item = state.get("item") or {}
        return _get_by_path({"item": item}, "$." + expr)
    # current.xxx / current.card.xxx
    if expr.startswith("current."):
        cur = state.get("current") or {}
        return _get_by_path({"current": cur}, "$." + expr)
    # scope.xxx
    if expr.startswith("scope."):
        scope = state.get("scope") or {}
        return _get_by_path({"scope": scope}, "$." + expr)
    # $.content.xxx 针对当前 card
    if expr.startswith("$."):
        card = (state.get("current") or {}).get("card") or state.get("card")
        base = {"content": getattr(card, "content", {})} if card else {}
        return _get_by_path({"$": base}, expr)
    return None


def _to_name(x: Any) -> str:
    """Convert object to name string."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        for key in ("name", "title", "label", "content"):
            v = x.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
            if isinstance(v, dict):
                nn = v.get("name") or v.get("title")
                if isinstance(nn, str) and nn.strip():
                    return nn.strip()
    return str(x).strip()


def _to_name_list(seq: Any) -> List[str]:
    """Convert sequence to list of names."""
    if not isinstance(seq, list):
        return []
    out: List[str] = []
    for it in seq:
        name = _to_name(it)
        if name:
            out.append(name)
    # 去重保持顺序
    seen = set()
    unique: List[str] = []
    for n in out:
        if n not in seen:
            unique.append(n)
            seen.add(n)
    return unique


def _render_value(val: Any, state: dict) -> Any:
    """
    Template rendering:
    - String: {item.xxx} / {current.card.content.xxx} / {scope.xxx} / {index} / {$.content.xxx}
    - Object: Supports {"$toNameList": "item.entity_list"} shortcut
    - List/Object: Recursive rendering
    """
    if isinstance(val, dict):
        if "$toNameList" in val and isinstance(val.get("$toNameList"), str):
            seq = _resolve_expr(val["$toNameList"], state)
            return _to_name_list(seq)
        return {k: _render_value(v, state) for k, v in val.items()}
    if isinstance(val, list):
        return [_render_value(v, state) for v in val]
    if isinstance(val, str):
        # 单一表达式直接返回原类型
        m = _TPL_PATTERN.fullmatch(val.strip())
        if m:
            resolved = _resolve_expr(m.group(1), state)
            return resolved
        # 内嵌模板，最终还是字符串
        def repl(match: re.Match) -> str:
            expr = match.group(1)
            res = _resolve_expr(expr, state)
            if isinstance(res, (dict, list)):
                return str(res)
            return "" if res is None else str(res)
        return _TPL_PATTERN.sub(repl, val)
    return val


def _get_from_state(path_expr: Any, state: dict) -> Any:
    """Helper to get value from state using path expression."""
    # 兼容 path 字符串（$. / $item(. ) / $current(. ) / $scope(. ) / item. / scope. / current.）或直接值
    if isinstance(path_expr, str):
        p = path_expr.strip()
        if p in ("item", "$item"):
            return state.get("item")
        if p in ("current", "$current"):
            return state.get("current")
        if p in ("scope", "$scope"):
            return state.get("scope")
        # 统一映射到 _resolve_expr 可识别形式
        if p.startswith("$item."):
            return _resolve_expr("item." + p[len("$item."):], state)
        if p.startswith("$current."):
            return _resolve_expr("current." + p[len("$current."):], state)
        if p.startswith("$scope."):
            return _resolve_expr("scope." + p[len("$scope."):], state)
        if p.startswith(("item.", "current.", "scope.", "$.")):
            return _resolve_expr(p, state)
    return path_expr


@register_node("Card.Read")
def node_card_read(session: Session, state: dict, params: dict) -> dict:
    """
    Card.Read: Read anchor card or specified card_id, write to state['card'] and return {'card': Card}
    params:
      - target: "$self" | int(card_id)
      - type_name: Card type name, used for type binding and field parsing
    """
    target = params.get("target", "$self")
    type_name = params.get("type_name", "")
    
    card: Optional[Card] = None
    if target == "$self":
        scope = state.get("scope") or {}
        card_id = scope.get("card_id")
        if card_id:
            card = _get_card_by_id(session, card_id)
    else:
        try:
            card = _get_card_by_id(session, int(target))
        except Exception:
            card = None
    
    if not card:
        raise ValueError("Card.Read: Target card not found")
    
    # If type name is specified, get type info and field structure
    card_type_info = None
    field_structure = None
    if type_name:
        from app.db.models import CardType
        card_type = session.exec(select(CardType).where(CardType.name == type_name)).first()
        if card_type and card_type.json_schema:
            card_type_info = {
                "id": card_type.id,
                "name": card_type.name,
                "schema": card_type.json_schema
            }
            # Parse field structure
            field_structure = _parse_schema_fields(card_type.json_schema)
    
    state["card"] = card
    state["current"] = {
        "card": card,
        "card_type_info": card_type_info,
        "field_structure": field_structure
    }
    
    logger.info(f"[Node] Card Read card_id={card.id} title={card.title} type={type_name}")
    return {
        "card": card,
        "card_type_info": card_type_info,
        "field_structure": field_structure
    }


@register_node("Card.ModifyContent")
def node_card_modify_content(session: Session, state: dict, params: dict) -> dict:
    """
    Card.ModifyContent: Shallow merge params['contentMerge'](dict) into current card.content
    Compatibility: setPath + setValue (Set path value directly)
    params:
      - contentMerge: dict
      - setPath: string (Optional, $.content.xxx path)
      - setValue: any (Optional, supports expression string)
    """
    card: Card = state.get("card")
    if not isinstance(card, Card):
        raise ValueError("Card.ModifyContent: Missing current card, please execute Card.Read first")

    # Handle setPath/setValue first
    set_path = params.get("setPath")
    if isinstance(set_path, str) and set_path:
        # Compatible $card. prefix (equivalent to $.)
        norm_path = set_path.strip()
        if norm_path.startswith("$card."):
            norm_path = "$." + norm_path[len("$card."):]
        
        # If path does not start with $., auto add $.content. prefix
        if not norm_path.startswith("$."):
            norm_path = "$.content." + norm_path
        
        value_expr = params.get("setValue")
        value = _get_from_state(value_expr, state)
        
        # Use deep copy to avoid modifying original object
        base = copy.deepcopy(dict(card.content or {}))
        
        # Normalize path: if starts with $.content., remove prefix
        if norm_path.startswith("$.content."):
            content_path = "$." + norm_path[len("$.content."):]
        else:
            content_path = norm_path
        
        # Set value
        _set_by_path(base, content_path, value)
        
        # Save
        card.content = base
        session.add(card)
        session.commit()
        session.refresh(card)
        logger.info(f"[Node] Set content by path card_id={card.id} path={set_path} value={value}")
        # Mark affected cards
        try:
            touched: set = state.setdefault("touched_card_ids", set())  # type: ignore[assignment]
            touched.add(int(card.id))
        except Exception:
            pass
        state["card"] = card
        state["current"] = {"card": card}
        return {"card": card}

    # Default merge
    content_merge = params.get("contentMerge") or {}
    content_merge = _render_value(content_merge, state)
    if not isinstance(content_merge, dict):
        raise ValueError("contentMerge must be an object")
    
    # Use deep copy to avoid modifying original object
    base = copy.deepcopy(dict(card.content or {}))
    base.update(content_merge)
    card.content = base
    session.add(card)
    session.commit()
    session.refresh(card)
    # Mark affected cards
    try:
        touched2: set = state.setdefault("touched_card_ids", set())  # type: ignore[assignment]
        touched2.add(int(card.id))
    except Exception:
        pass
    state["card"] = card
    state["current"] = {"card": card}
    logger.info(f"[Node] Modify card content complete card_id={card.id} merged_keys={list(content_merge.keys())}")
    return {"card": card}


@register_node("Card.UpsertChildByTitle")
def node_card_upsert_child_by_title(session: Session, state: dict, params: dict) -> dict:
    """
    Card.UpsertChildByTitle: Create/Update child card by title under target parent card.
    params:
      - cardType: str (Card type name)
      - title: str (Template allowed: {item.title} / {index} / { $.content.volume_number } etc.)
      - titlePath: string (Compatibility: Get title from path/expression)
      - parent: "$self" | "$projectRoot" | specific card_id (Optional, default $self)
      - useItemAsContent: bool (true then use state['item'] as content)
      - contentMerge: dict (Choice with useItemAsContent, merge into content)
      - contentTemplate: dict|list|str (Direct template render as content, priority over contentMerge)
      - contentPath: string (Compatibility: Get content from path/expression)
    Dependency: state['card'] as default parent; optional state['item'] for template value.
    """
    parent: Optional[Card] = state.get("card")
    # Allow parent not read first; if parent not provided, create at project root

    card_type_name = params.get("cardType")
    if not card_type_name:
        raise ValueError("Parameter cardType required")
    ct: Optional[CardType] = session.exec(select(CardType).where(CardType.name == card_type_name)).first()
    if not ct:
        raise ValueError(f"Card type not found: {card_type_name}")

    raw_title: Optional[str] = params.get("title")
    if not raw_title:
        title_path = params.get("titlePath")
        if isinstance(title_path, str) and title_path:
            resolved_title = _get_from_state(title_path, state)
            if isinstance(resolved_title, (str, int, float)):
                raw_title = str(resolved_title)
    title = _render_value(raw_title, state) if isinstance(raw_title, str) else raw_title
    if not isinstance(title, str) or not title.strip():
        title = ct.name or "Unnamed"

    # Parse parent target
    parent_spec = params.get("parent") or ("$self" if isinstance(parent, Card) else "$projectRoot")
    target_parent_id: Optional[int]
    project_id: int
    if parent_spec in ("$self", None):
        if not isinstance(parent, Card):
            raise ValueError("Need to read parent card first or provide parent target")
        target_parent_id = parent.id
        project_id = parent.project_id
    elif parent_spec in ("$root", "$projectRoot", "$project_root"):
        if isinstance(parent, Card):
            project_id = parent.project_id
        else:
            scope = state.get("scope") or {}
            project_id = int(scope.get("project_id"))
        target_parent_id = None
    else:
        p = _get_card_by_id(session, int(parent_spec))
        if not p:
            raise ValueError(f"Parent card not found: {parent_spec}")
        target_parent_id = p.id
        project_id = p.project_id

    # Check existing same parent, same type, same title (avoid misjudging different type same name cards)
    existing = session.exec(
        select(Card).where(
            Card.project_id == project_id,
            Card.parent_id == target_parent_id,
            Card.card_type_id == ct.id,
        )
    ).all()
    target = next((c for c in existing if str(c.title) == str(title)), None)

    use_item = bool(params.get("useItemAsContent"))
    content_merge = params.get("contentMerge") if isinstance(params.get("contentMerge"), dict) else None
    content_template = params.get("contentTemplate") if isinstance(params.get("contentTemplate"), (dict, list, str)) else None
    content_path = params.get("contentPath") if isinstance(params.get("contentPath"), str) else None
    item = state.get("item") or {}

    if use_item:
        content: Any = dict(item)
    else:
        if content_template is not None:
            content = _render_value(content_template, state)
            if not isinstance(content, dict):
                content = {"value": content}
        elif content_path:
            resolved = _get_from_state(content_path, state)
            content = resolved if isinstance(resolved, dict) else {"value": resolved}
        else:
            base = dict(target.content) if target else {}
            cm = _render_value(content_merge or {}, state)
            content = {**base, **(cm or {})}

    if target:
        target.content = content
        session.add(target)
        session.commit()
        session.refresh(target)
        result = target
        logger.info(f"[Node] Child card updated parent_id={target_parent_id} title={title} card_id={target.id}")
    else:
        new_card = Card(
            title=title,
            model_name=ct.model_name or ct.name,
            content=content,
            parent_id=target_parent_id,
            card_type_id=ct.id,
            json_schema=None,
            ai_params=None,
            project_id=project_id,
            display_order=len(existing),
            ai_context_template=ct.default_ai_context_template,
        )
        session.add(new_card)
        session.commit()
        session.refresh(new_card)
        result = new_card
        logger.info(f"[Node] Child card created parent_id={target_parent_id} title={title} card_id={new_card.id}")

    state["last_child"] = result
    state["current"] = {"card": result}
    # Mark affected cards
    try:
        touched3: set = state.setdefault("touched_card_ids", set())  # type: ignore[assignment]
        touched3.add(int(getattr(result, "id", 0)))
        if isinstance(parent, Card) and parent.id:
            touched3.add(int(parent.id))
    except Exception:
        pass
    return {"card": result}


@register_node("List.ForEach")
def node_list_foreach(session: Session, state: dict, params: dict, run_body):
    """
    List.ForEach: Iterate list and execute body node for each element.
    params:
      - listPath: string e.g., "$.content.character_cards"
      - list: Any (Compatibility: string path or direct array)
    """
    list_path = params.get("listPath")
    seq: Any = None
    if not isinstance(list_path, str) or not list_path:
        raw = params.get("list")
        logger.info(f"[Node] List.ForEach raw list param type={type(raw).__name__} value={raw!r}")
        if isinstance(raw, list):
            seq = raw
        elif isinstance(raw, dict):
            # Support { path: '$.content.xxx' }
            cand = raw.get("path") or raw.get("listPath")
            if isinstance(cand, str) and cand:
                seq = _get_from_state(cand, state)
        elif isinstance(raw, str) and raw:
            seq = _get_from_state(raw.strip(), state)
    if seq is None:
        if not isinstance(list_path, str) or not list_path:
            logger.warning("[Node] List.ForEach missing listPath")
            return
        card = state.get("card") or (state.get("current") or {}).get("card")
        base = {"content": getattr(card, "content", {})} if card else {}
        seq = _get_by_path({"$": base}, list_path) or []
    if not isinstance(seq, list):
        logger.warning(f"[Node] List.ForEach value not list path={list_path}")
        return
    logger.info(f"[Node] List.ForEach parsed, length={len(seq)}")
    for idx, it in enumerate(seq, start=1):
        state["item"] = {"index": idx, **(it if isinstance(it, dict) else {"value": it})}
        logger.info(f"[Node] List.ForEach index={idx}")
        run_body()


@register_node("List.ForEachRange")
def node_list_foreach_range(session: Session, state: dict, params: dict, run_body):
    """
    List.ForEachRange: Iterate 1..N based on count
    params:
      - countPath: string e.g., "$.content.stage_count"
      - start: int default 1
    """
    count_path = params.get("countPath")
    if not isinstance(count_path, str):
        logger.warning("[Node] List.ForEachRange missing countPath")
        return
    card = state.get("card") or (state.get("current") or {}).get("card")
    base = {"content": getattr(card, "content", {})} if card else {}
    count_val = _get_by_path({"$": base}, count_path) or 0
    try:
        n = int(count_val)
    except Exception:
        n = 0
    
    if n <= 0:
        logger.info(f"[Node] List.ForEachRange count is {n}, skip loop")
        return
    
    start = int(params.get("start", 1) or 1)
    for i in range(start, start + n):
        state["item"] = {"index": i}
        logger.info(f"[Node] List.ForEachRange index={i} (Total {n})")
        run_body()


@register_node("Card.ClearFields")
def node_card_clear_fields(session: Session, state: Dict[str, Any], params: Dict[str, Any]) -> None:
    """
    Card.ClearFields: Clear specified fields of a card
    params:
    - target: Target card ID or '$self'
    - fields: List of field paths to clear (e.g. ['$.content.field1', '$.content.field2'])
    """
    target = params.get("target", "$self")
    fields = params.get("fields", [])
    
    if target == "$self":
        target_id = state["scope"].get("card_id")
    else:
        target_id = int(target) if isinstance(target, (int, str)) and str(target).isdigit() else None
    
    if not target_id:
        logger.warning(f"[Card.ClearFields] Invalid target card: {target}")
        return
        
    card = _get_card_by_id(session, target_id)
    if not card:
        logger.warning(f"[Card.ClearFields] Card not found: {target_id}")
        return
    
    if not isinstance(fields, list) or not fields:
        logger.warning("[Card.ClearFields] Missing valid fields parameter")
        return
    
    # Use deep copy to avoid modifying original object
    content = copy.deepcopy(card.content or {})
    
    # Clear specified fields
    for field_path in fields:
        if isinstance(field_path, str) and field_path.startswith("$."):
            _set_by_path({"$": content}, field_path, None)
    
    card.content = content
    session.add(card)
    session.commit()
    
    # Record affected card
    if "touched_card_ids" in state:
        state["touched_card_ids"].add(target_id)


@register_node("Card.ReplaceFieldText")
def node_card_replace_field_text(session: Session, state: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Card.ReplaceFieldText: Replace specified text fragment in card field
    
    params:
    - card_id: Target card ID
    - field_path: Field path (e.g. "content", "overview" etc.)
    - old_text: Original text fragment to replace (must match exactly)
    - new_text: New text content
    
    returns:
    - success: bool
    - replaced_count: int
    - old_length: int
    - new_length: int
    - error: str (if failed)
    """
    card_id = params.get("card_id")
    field_path = params.get("field_path", "")
    old_text = params.get("old_text", "")
    new_text = params.get("new_text", "")
    
    if not card_id:
        return {"success": False, "error": "Missing card_id parameter"}
    
    if not field_path:
        return {"success": False, "error": "Missing field_path parameter"}
    
    if not old_text:
        return {"success": False, "error": "Missing old_text parameter"}
    
    # Get card
    card = _get_card_by_id(session, int(card_id))
    if not card:
        return {"success": False, "error": f"Card {card_id} not found"}
    
    # Handle field path, normalize to content. prefix
    normalized_path = field_path
    if not normalized_path.startswith("content."):
        normalized_path = f"content.{normalized_path}"
    
    logger.info(f"  Original field path: {field_path}")
    logger.info(f"  Normalized path: {normalized_path}")
    
    # Get current field value
    path_parts = normalized_path.split(".")
    logger.info(f"  Path parts: {path_parts}")
    
    current_value = card.content or {}
    logger.info(f"  card.content Type: {type(current_value)}")
    logger.info(f"  card.content Keys: {list(current_value.keys()) if isinstance(current_value, dict) else 'N/A'}")
    
    # Access target field level by level
    for i, part in enumerate(path_parts[1:]):  # Skip "content"
        logger.info(f"  Access level {i+1}: Field '{part}', Current value type {type(current_value)}")
        if isinstance(current_value, dict):
            current_value = current_value.get(part, "")
            logger.info(f"    Got value length: {len(str(current_value))}")
        else:
            return {
                "success": False,
                "error": f"Field path {normalized_path} invalid (Not a dict at {part})"
            }
    
    # Ensure current value is string
    if not isinstance(current_value, str):
        return {
            "success": False,
            "error": f"Field {field_path} is not text type, cannot replace text"
        }
    
    # Check if fuzzy match mode (start...end)
    fuzzy_match = False
    actual_old_text = old_text
    
    if "..." in old_text or "……" in old_text:
        # Fuzzy match mode: Extract start and end
        fuzzy_match = True
        separator = "..." if "..." in old_text else "……"
        parts = old_text.split(separator, 1)  # Split only once
        
        if len(parts) == 2:
            start_text = parts[0].strip()
            end_text = parts[1].strip()
            
            logger.info(f"  🔍 Using fuzzy match mode")
            logger.info(f"  Start text: {start_text[:20]}...")
            logger.info(f"  End text: ...{end_text[-20:]}")
            
            # Find matching fragment in content
            start_idx = current_value.find(start_text)
            if start_idx == -1:
                return {
                    "success": False,
                    "error": f"Start text not found in field '{field_path}': {start_text[:30]}...",
                    "hint": "Please confirm start text matches exactly"
                }
            
            # Find end after start position
            end_search_start = start_idx + len(start_text)
            end_idx = current_value.find(end_text, end_search_start)
            if end_idx == -1:
                return {
                    "success": False,
                    "error": f"End text not found in field '{field_path}': ...{end_text[-30:]}",
                    "hint": "Please confirm end text matches exactly"
                }
            
            # Extract complete matching fragment
            actual_old_text = current_value[start_idx:end_idx + len(end_text)]
            logger.info(f"  ✅ Fuzzy match success, found {len(actual_old_text)} char fragment")
        else:
            return {
                "success": False,
                "error": "Fuzzy match format error, should be: start text...end text",
                "hint": "Use three dots or six dots as separator"
            }
    
    # Check if original text exists (Exact match or full text after fuzzy match)
    if actual_old_text not in current_value:
        preview = current_value[:100] + "..." if len(current_value) > 100 else current_value
        error_message = f"Specified original text fragment not found in field '{field_path}'"
        logger.warning(f"⚠️ Text not found, field_path='{field_path}'")
        return {
            "success": False,
            "error": error_message,
            "field_preview": preview,
            "hint": "Please confirm original text matches exactly (including punctuation, spaces, newlines)"
        }
    
    # Execute replace
    replaced_count = current_value.count(actual_old_text)
    updated_value = current_value.replace(actual_old_text, new_text)
    
    if fuzzy_match:
        logger.info(f"  📝 Fuzzy match replace: Original {len(actual_old_text)} chars -> New {len(new_text)} chars")
    
    logger.info(f"[Card.ReplaceFieldText] card_id={card_id}, field={field_path}, Found {replaced_count} matches")
    logger.info(f"  Length before: {len(current_value)} chars")
    logger.info(f"  Length after: {len(updated_value)} chars")
    
    # Use deep copy to avoid modifying original object
    content = copy.deepcopy(card.content or {})
    
    # Set updated value
    # Remove "content." prefix to get actual field path
    field_parts = normalized_path.split(".")[1:]  # Remove "content", get ["field"] or ["nested", "field"]
    
    # Access and set value level by level
    current_dict = content
    for part in field_parts[:-1]:
        if part not in current_dict:
            current_dict[part] = {}
        current_dict = current_dict[part]
    
    # Set final field value
    current_dict[field_parts[-1]] = updated_value
    
    card.content = content
    session.add(card)
    session.commit()
    session.refresh(card)
    
    # Record affected card
    if "touched_card_ids" in state:
        state["touched_card_ids"].add(int(card_id))
    
    logger.info(f"[Card.ReplaceFieldText] Replace success")
    
    return {
        "success": True,
        "card_id": card_id,
        "card_title": card.title,
        "field_path": field_path,
        "replaced_count": replaced_count,
        "old_length": len(current_value),
        "new_length": len(updated_value)}
