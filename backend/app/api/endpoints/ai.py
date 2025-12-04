from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from app.db.session import get_session
from app.schemas.ai import ContinuationRequest, ContinuationResponse, GeneralAIRequest
from app.schemas.response import ApiResponse
from app.services import prompt_service, agent_service, llm_config_service
from fastapi.responses import StreamingResponse
import json
from fastapi import Body
from pydantic import ValidationError, create_model
from pydantic import Field as PydanticField
from typing import Type, Dict, Any, List

from app.db.models import Card, CardType
from copy import deepcopy
from sqlmodel import select as orm_select

# 引入知识库
from app.services.knowledge_service import KnowledgeService
import re
from app.schemas.entity import DYNAMIC_INFO_TYPES
from app.schemas import entity as entity_schemas
from app.services.workflow_triggers import trigger_on_generate_finish
from app.services.context_service import assemble_context, ContextAssembleParams
from app.services import llm_config_service as _llm_svc

router = APIRouter()

# --- JSON Schema -> Python Type Simple Mapping (Conservative, fallback to Any) ---
from typing import Any as _Any, Dict as _Dict, List as _List

# Schema filtering based on metadata (remove fields marked with x-ai-exclude=true)
def _filter_schema_for_ai(schema: Dict[str, Any]) -> Dict[str, Any]:
    def prune(node: Any, parent_required: List[str] | None = None) -> Any:
        if isinstance(node, dict):
            # Object: Filter fields marked with x-ai-exclude in properties
            if node.get('type') == 'object' and isinstance(node.get('properties'), dict):
                props = node.get('properties') or {}
                required = list(node.get('required') or [])
                new_props: Dict[str, Any] = {}
                for name, sch in props.items():
                    if isinstance(sch, dict) and sch.get('x-ai-exclude') is True:
                        # Remove from required
                        if name in required:
                            required = [r for r in required if r != name]
                        continue
                    new_props[name] = prune(sch)
                node = dict(node)  # Copy
                node['properties'] = new_props
                if required:
                    node['required'] = required
                elif 'required' in node:
                    # If all removed, remove required field
                    node.pop('required', None)
            # Array: Recursively process items/prefixItems (tuple)
            if node.get('type') == 'array':
                if 'items' in node:
                    node = dict(node)
                    node['items'] = prune(node['items'])
                if 'prefixItems' in node and isinstance(node.get('prefixItems'), list):
                    node = dict(node)
                    node['prefixItems'] = [prune(it) for it in node.get('prefixItems', [])]
            # Combinators: Recursively process anyOf/oneOf/allOf
            for kw in ('anyOf', 'oneOf', 'allOf'):
                if isinstance(node.get(kw), list):
                    node = dict(node)
                    node[kw] = [prune(it) for it in node.get(kw, [])]
            # $defs: Only recursively process internal definitions (do not remove definition keys themselves)
            if isinstance(node.get('$defs'), dict):
                defs = node.get('$defs') or {}
                new_defs: Dict[str, Any] = {}
                for k, v in defs.items():
                    new_defs[k] = prune(v)
                node = dict(node)
                node['$defs'] = new_defs
            # Cleanup metadata traces (optional, not mandatory)
            if 'x-ai-exclude' in node:
                node = dict(node)
                node.pop('x-ai-exclude', None)
            return node
        elif isinstance(node, list):
            return [prune(it) for it in node]
        return node

    try:
        root = deepcopy(schema) if isinstance(schema, dict) else {}
        return prune(root)
    except Exception:
        # On error, do not block flow, fallback to original schema
        return schema


def _json_schema_to_py_type(sch: Dict[str, Any]) -> Any:
    if not isinstance(sch, dict):
        return _Any
    if '$ref' in sch:
        # Simplified handling: References handled as Dict
        return _Dict[str, _Any]
    t = sch.get('type')
    if t == 'string':
        return str
    if t == 'integer':
        return int
    if t == 'number':
        return float
    if t == 'boolean':
        return bool
    if t == 'array':
        item_sch = sch.get('items') or {}
        return _List[_json_schema_to_py_type(item_sch)]  # type: ignore[index]
    if t == 'object':
        # If dynamic structure with properties, handle as Dict
        return _Dict[str, _Any]
    # No type declared or unrecognized
    return _Any


def _build_model_from_json_schema(model_name: str, schema: Dict[str, Any]):
    props: Dict[str, Any] = (schema or {}).get('properties') or {}
    required: List[str] = list((schema or {}).get('required') or [])
    field_defs: Dict[str, tuple] = {}
    for fname, fsch in props.items():
        anno = _json_schema_to_py_type(fsch if isinstance(fsch, dict) else {})
        desc = fsch.get('description') if isinstance(fsch, dict) else None
        is_required = fname in required
        if desc is not None:
            default_val = PydanticField(... if is_required else None, description=desc)
        else:
            default_val = ... if is_required else None
        field_defs[fname] = (anno, default_val)
    return create_model(model_name, **field_defs)

# --- Schema $defs Recursion Completion (Inject $defs of built-in models into custom Schema) ---
_BUILTIN_DEFS_CACHE: Dict[str, Any] | None = None

def _get_builtin_defs() -> Dict[str, Any]:
    global _BUILTIN_DEFS_CACHE
    if _BUILTIN_DEFS_CACHE is not None:
        return _BUILTIN_DEFS_CACHE
    merged: Dict[str, Any] = {}
    for _, model_class in RESPONSE_MODEL_MAP.items():
        sch = model_class.model_json_schema(ref_template="#/$defs/{model}")
        defs = sch.get('$defs') or {}
        merged.update(defs)
    _BUILTIN_DEFS_CACHE = merged
    return merged

def _collect_ref_names(node: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        if '$ref' in node and isinstance(node['$ref'], str) and node['$ref'].startswith('#/$defs/'):
            names.add(node['$ref'].split('/')[-1])
        for v in node.values():
            names |= _collect_ref_names(v)
    elif isinstance(node, list):
        for it in node:
            names |= _collect_ref_names(it)
    return names

def _augment_schema_with_builtin_defs(schema: Dict[str, Any]) -> Dict[str, Any]:
    # Do not modify original object
    sch = deepcopy(schema) if schema is not None else {}
    if not isinstance(sch, dict):
        return sch
    sch.setdefault('$defs', {})
    defs = sch['$defs']
    builtin_defs = _get_builtin_defs()

    # Iterative completion until no new references
    seen: set[str] = set(defs.keys())
    pending = _collect_ref_names(sch) - seen
    while pending:
        name = pending.pop()
        if name in defs:
            continue
        if name in builtin_defs:
            defs[name] = deepcopy(builtin_defs[name])
            # New definitions might reference other defs
            newly = _collect_ref_names(defs[name]) - set(defs.keys())
            pending |= newly
        # If definition not found, skip (keep as is, let LLM tolerate)
    return sch

# --- Dynamic injection of CardType defs (same idea as cards.py) ---
def _compose_with_card_types(session: Session, schema: Dict[str, Any]) -> Dict[str, Any]:
    sch = deepcopy(schema) if isinstance(schema, dict) else {}
    if not isinstance(sch, dict):
        return sch
    sch.setdefault('$defs', {})
    defs = sch['$defs']
    ref_names: set[str] = _collect_ref_names(sch)
    types = session.exec(orm_select(CardType)).all()
    by_model: Dict[str, Any] = {}
    for t in types:
        if t and t.json_schema:
            if t.model_name:
                by_model[t.model_name] = t.json_schema
            by_model[t.name] = t.json_schema
    for n in ref_names:
        if n in by_model:
            defs[n] = by_model[n]
    return sch

# Response model map (built-in)
from app.schemas.response_registry import RESPONSE_MODEL_MAP

# Knowledge base placeholder parsing and replacement
_KB_ID_PATTERN = re.compile(r"@KB\{\s*id\s*=\s*(\d+)\s*\}")
_KB_NAME_PATTERN = re.compile(r"@KB\{\s*name\s*=\s*([^}]+)\}")


def _inject_knowledge(session: Session, template: str) -> str:
    """Inject knowledge base placeholders in template with actual content.

    Rules:
    1) For multiple placeholders within "- knowledge:" paragraph, inject sequentially separated by numbering:
       - knowledge:\n1.\n<KB1>\n\n2.\n<KB2> ...
    2) If placeholder appears outside knowledge paragraph, do in-place replacement with full text.
    3) If knowledge base not found, keep hint comment to avoid interruption.
    """
    svc = KnowledgeService(session)

    def fetch_kb_by_id(kid: int) -> str:
        kb = svc.get_by_id(kid)
        return kb.content if kb and kb.content else f"/* Knowledge Base not found: id={kid} */"

    def fetch_kb_by_name(name: str) -> str:
        kb = svc.get_by_name(name)
        return kb.content if kb and kb.content else f"/* Knowledge Base not found: name={name} */"

    # Process knowledge segment first (more structured injection)
    lines = template.splitlines()
    i = 0
    out_lines: list[str] = []
    while i < len(lines):
        line = lines[i]
        # Match top-level "- knowledge:" line (case insensitive)
        if re.match(r"^\s*-\s*knowledge\s*:\s*$", line, flags=re.IGNORECASE):
            # Collect placeholder lines within this paragraph until next top-level "- <Something>" line or EOF
            j = i + 1
            block_lines: list[str] = []
            while j < len(lines) and not re.match(r"^\s*-\s*\w", lines[j]):
                block_lines.append(lines[j])
                j += 1
            # Extract placeholder order
            placeholders: list[tuple[str, str]] = []  # (mode, value)
            for bl in block_lines:
                for m in _KB_ID_PATTERN.finditer(bl):
                    placeholders.append(("id", m.group(1)))
                for m in _KB_NAME_PATTERN.finditer(bl):
                    placeholders.append(("name", m.group(1).strip().strip('\"\'')))
            # Build numbered content
            out_lines.append(line)  # Keep title line "- knowledge:"
            if placeholders:
                for idx, (mode, val) in enumerate(placeholders, start=1):
                    out_lines.append(f"{idx}.")
                    if mode == "id":
                        try:
                            content = fetch_kb_by_id(int(val))
                        except Exception:
                            content = f"/* Knowledge Base not found: id={val} */"
                    else:
                        content = fetch_kb_by_name(val)
                    out_lines.append(content.strip())
                    # Empty line between paragraphs
                    if idx < len(placeholders):
                        out_lines.append("")
            # Skip original block
            i = j
            continue
        else:
            out_lines.append(line)
            i += 1

    enumerated_text = "\n".join(out_lines)

    # In-place replacement outside knowledge segment (if placeholders remain)
    def repl_id(m: re.Match) -> str:
        try:
            kid = int(m.group(1))
        except Exception:
            return f"/* Knowledge Base not found: id={m.group(1)} */"
        return fetch_kb_by_id(kid)

    def repl_name(m: re.Match) -> str:
        name = m.group(1).strip().strip('\"\'')
        return fetch_kb_by_name(name)

    result = _KB_ID_PATTERN.sub(repl_id, enumerated_text)
    result = _KB_NAME_PATTERN.sub(repl_name, result)
    return result

@router.get("/schemas", response_model=Dict[str, Any], summary="Get all output model JSON Schemas (Built-in only)")
def get_all_schemas(session: Session = Depends(get_session)):
    """Return schema aggregation of built-in pydantic models, keys are model names."""
    all_definitions: Dict[str, Any] = {}

    # 1) Built-in pydantic models
    for name, model_class in RESPONSE_MODEL_MAP.items():
        schema = model_class.model_json_schema(ref_template="#/$defs/{model}")
        if '$defs' in schema:
            all_definitions.update(schema['$defs'])
            del schema['$defs']
        all_definitions[name] = schema

    # Dynamically fix CharacterCard.dynamic_info attributes
    try:
        cc = all_definitions.get('CharacterCard')
        if isinstance(cc, dict):
            props = (cc.get('properties') or {})
            if 'dynamic_info' in props:
                item_schema = {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "info": {"type": "string"},
                        "weight": {"type": "number"}
                    },
                    "required": ["id", "info", "weight"]
                }
                enum_values = DYNAMIC_INFO_TYPES
                props['dynamic_info'] = {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        ev: {"type": "array", "items": item_schema} for ev in enum_values
                    },
                    "description": "Character dynamic info, array grouped by category (keys are Chinese enum values)"
                }
                cc['properties'] = props
                all_definitions['CharacterCard'] = cc
    except Exception:
        pass

    # 2) Inject entity dynamic info related models (for frontend parsing $ref: DynamicInfo etc.)
    try:
        entity_models = [
            entity_schemas.DynamicInfoItem,
            entity_schemas.DynamicInfo,
            entity_schemas.UpdateDynamicInfo,
        ]
        for mdl in entity_models:
            sch = mdl.model_json_schema(ref_template="#/$defs/{model}")
            if '$defs' in sch:
                all_definitions.update(sch['$defs'])
                del sch['$defs']
            all_definitions[mdl.__name__] = sch
    except Exception:
        pass

    return all_definitions

@router.get("/content-models", response_model=List[str], summary="Get all available output model names")
def get_content_models(session: Session = Depends(get_session)):
    # Only return built-in model names
    return list(RESPONSE_MODEL_MAP.keys())


async def stream_wrapper(generator):
    async for item in generator:
        yield f"data: {json.dumps({'content': item})}\n\n"

@router.get("/config-options", summary="Get AI generation configuration options")
async def get_ai_config_options(session: Session = Depends(get_session)):
    """Get available configuration options for AI generation"""
    try:
        # Get all LLM configs
        llm_configs = llm_config_service.get_llm_configs(session)
        # Get all prompts
        prompts = prompt_service.get_prompts(session)
        # Response models are built-in only
        response_models = get_content_models(session)
        return ApiResponse(data={
            "llm_configs": [{"id": config.id, "display_name": config.display_name or config.model_name} for config in llm_configs],
            "prompts": [{"id": prompt.id, "name": prompt.name, "description": prompt.description, "built_in": getattr(prompt, 'built_in', False)} for prompt in prompts],
            "available_tasks": [],
            "response_models": response_models
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config options: {str(e)}")

@router.get("/prompts/render", summary="Render and inject knowledge base into prompt template")
async def render_prompt_with_knowledge(name: str, session: Session = Depends(get_session)):
    p = prompt_service.get_prompt_by_name(session, name)
    if not p or not p.template:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {name}")
    try:
        text = _inject_knowledge(session, str(p.template))
        return ApiResponse(data={"text": text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")

@router.post("/generate", summary="General AI Generation Endpoint")
async def generate_ai_content(
    request: GeneralAIRequest = Body(...),
    session: Session = Depends(get_session),
):
    """
    General AI content generation endpoint: Frontend must provide response_model_schema.
    """
    # Basic parameter validation: input/llm_config_id/prompt_name/response_model_schema required
    if not request.input or not request.llm_config_id or not request.prompt_name:
        raise HTTPException(status_code=400, detail="Missing required generation parameters: input, llm_config_id or prompt_name")
    if request.response_model_schema is None:
        raise HTTPException(status_code=400, detail="Please provide response_model_schema")

    # Parse response model (Dynamic schema only)
    try:
        # Dynamically inject CardType defs first
        composed = _compose_with_card_types(session, request.response_model_schema)
        # Before completing built-in defs, filter fields based on x-ai-exclude
        composed = _filter_schema_for_ai(composed)
        # Complete built-in defs
        schema_for_prompt: Dict[str, Any] | None = _augment_schema_with_builtin_defs(composed)
        resp_model = _build_model_from_json_schema('DynamicResponseModel', schema_for_prompt or composed)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create dynamic model: {e}")

    # Get prompt
    prompt = prompt_service.get_prompt_by_name(session, request.prompt_name)
    if not prompt:
        raise HTTPException(status_code=400, detail=f"Prompt name not found: {request.prompt_name}")

    # Inject knowledge base
    prompt_template = _inject_knowledge(session, prompt.template or '')

    # System Prompt: Carry JSON Schema
    schema_json = json.dumps(schema_for_prompt if schema_for_prompt is not None else resp_model.model_json_schema(), indent=2, ensure_ascii=False)
    system_prompt = (
        f"{prompt_template}\n\n"
        f"```json\n{schema_json}\n```"
    )

    user_prompt = request.input['input_text']
    deps_str = request.deps or ""

    try:
        result = await agent_service.run_llm_agent(
            session=session,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            output_type=resp_model,
            llm_config_id=request.llm_config_id, 
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            timeout=request.timeout,
            deps=deps_str,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Trigger OnGenerateFinish (if card can be located)
    card: Card | None = None
    try:
        card_id = None
        if isinstance(request.input, dict):
            card_id = request.input.get('card_id')
        if card_id:
            card = session.get(Card, int(card_id))
        project_id = None
        if isinstance(request.input, dict):
            project_id = request.input.get('project_id') or (card.project_id if card else None)
        trigger_on_generate_finish(session, card, int(project_id) if project_id else (card.project_id if card else None))
    except Exception:
        pass
    return ApiResponse(data=result)

@router.post("/generate/continuation", 
             response_model=ApiResponse[ContinuationResponse], 
             summary="Continue writing text",
             responses={
                 200: {
                     "content": {
                         "application/json": {},
                         "text/event-stream": {}
                     },
                     "description": "Successfully returned continuation result or event stream"
                 }
             })
async def generate_continuation(
    request: ContinuationRequest,
    session: Session = Depends(get_session),
):
    try:
        # Force reading template from prompt_name as system prompt
        if not request.prompt_name:
            raise HTTPException(status_code=400, detail="Continuation must specify prompt_name")
        p = prompt_service.get_prompt_by_name(session, request.prompt_name)
        if not p or not p.template:
            raise HTTPException(status_code=400, detail=f"Prompt name not found: {request.prompt_name}")
        # Inject knowledge base
        system_prompt = _inject_knowledge(session, str(p.template))

        if request.stream:
            # Perform quota pre-check to avoid errors during streaming
            ok, reason = _llm_svc.can_consume(session, request.llm_config_id, 0, 0, 1)
            if not ok:
                raise HTTPException(status_code=400, detail=f"LLM quota insufficient: {reason}")
            async def _stream_and_trigger():
                content_acc = []
                async for chunk in agent_service.generate_continuation_streaming(session, request, system_prompt):
                    content_acc.append(chunk)
                    yield chunk
                try:
                    # Trigger after continuation finishes
                    trigger_on_generate_finish(session, None, request.project_id)
                except Exception:
                    pass
            return StreamingResponse(stream_wrapper(_stream_and_trigger()), media_type="text/event-stream")
        else:
            result = await agent_service.generate_continuation(session, request, system_prompt)
            try:
                trigger_on_generate_finish(session, None, request.project_id)
            except Exception:
                pass
            return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

from app.schemas.wizard import Tags as _Tags
@router.get("/models/tags", response_model=_Tags, summary="Export Tags model (for type generation)")
def export_tags_model():
    return _Tags() 