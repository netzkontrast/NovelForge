import os
from sqlmodel import Session, select
from app.db.models import Prompt, CardType, Card
from app.db.models import Workflow, WorkflowTrigger
from loguru import logger
from app.api.endpoints.ai import RESPONSE_MODEL_MAP

from app.db.models import Knowledge, LLMConfig
from app.db.models import Project
from sqlmodel import select as _select

def _parse_prompt_file(file_path: str):
    """Parse single prompt file, support frontmatter metadata"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    filename = os.path.basename(file_path)
    name = os.path.splitext(filename)[0]
    description = f"AI Task Prompt: {name}"
            
    return {
        "name": name,
        "description": description,
        "template": content.strip()
    }

def get_all_prompt_files():
    """Load all prompts from file system"""
    prompt_dir = os.path.join(os.path.dirname(__file__), 'prompts')
    if not os.path.exists(prompt_dir):
        logger.warning(f"Prompt directory not found at {prompt_dir}. Cannot load prompts.")
        return {}

    prompt_files = {}
    for filename in os.listdir(prompt_dir):
        if filename.endswith(('.prompt', '.txt')):
            file_path = os.path.join(prompt_dir, filename)
            name = os.path.splitext(filename)[0]
            prompt_files[name] = _parse_prompt_file(file_path)
    return prompt_files

def init_prompts(db: Session):
    """Initialize default prompts.
    Behavior controlled by environment variable BOOTSTRAP_OVERWRITE:
    """
    overwrite = str(os.getenv('BOOTSTRAP_OVERWRITE', '')).lower() in ('1', 'true', 'yes', 'on')
    existing_prompts = db.exec(select(Prompt)).all()
    existing_names = {p.name for p in existing_prompts}

    all_prompts_data = get_all_prompt_files()

    new_count = 0
    updated_count = 0
    skipped_count = 0
    prompts_to_add = []
    
    for name, prompt_data in all_prompts_data.items():
        if name in existing_names:
            if overwrite:
                existing_prompt = next(p for p in existing_prompts if p.name == name)
                existing_prompt.template = prompt_data['template']
                existing_prompt.description = prompt_data.get('description')
                existing_prompt.built_in = True
                updated_count += 1
            else:
                skipped_count += 1
        else:
            prompts_to_add.append(Prompt(**prompt_data, built_in=True))
            new_count += 1
    
    if prompts_to_add:
        db.add_all(prompts_to_add)

    if new_count > 0 or updated_count > 0:
        db.commit()
        logger.info(f"Prompts update completed: Added {new_count}, Updated {updated_count} (overwrite={overwrite}, Skipped {skipped_count}).")
    else:
        logger.info(f"All prompts are up to date (overwrite={overwrite}, Skipped {skipped_count}).")




def create_default_card_types(db: Session):
    """
    Creates or updates the default card types in the database.

    Args:
        db: Database session.
    """
    default_types = {
        "Tags": {"editor_component": "TagsEditor", "is_singleton": True, "is_ai_enabled": False, "default_ai_context_template": None},
        "SpecialAbility": {"is_singleton": True, "default_ai_context_template": "Tags: @Tags.content"},
        "OneSentenceSummary": {"is_singleton": True, "default_ai_context_template": "Tags: @Tags.content\nSpecial Ability: @SpecialAbility.content.special_abilities"},
        "StoryOutline": {"is_singleton": True, "default_ai_context_template": "Tags: @Tags.content\nSpecial Ability: @SpecialAbility.content.special_abilities\nStory Summary: @OneSentenceSummary.content.one_sentence"},
        "WorldSetting": {"is_singleton": True, "default_ai_context_template": "Tags: @Tags.content\nSpecial Ability: @SpecialAbility.content.special_abilities\nStory Outline: @StoryOutline.content.overview"},
        "CoreBlueprint": {"is_singleton": True, "default_ai_context_template": "Tags: @Tags.content\nSpecial Ability: @SpecialAbility.content.special_abilities\nStory Outline: @StoryOutline.content.overview\nWorld Setting: @WorldSetting.content\nOrganization Setting:@type:OrganizationCard[previous:global].{content.name,content.description,content.influence,content.relationship}"},
        # Volume Outline
        "VolumeOutline": {"default_ai_context_template": (
            "Total Volumes:@CoreBlueprint.content.volume_count\n"
            "Story Outline:@StoryOutline.content.overview\n"
            "Tags:@Tags.content\n"
            "World Setting: @WorldSetting.content.world_view\n"
            "Organization Setting:@type:OrganizationCard[previous:global].{content.name,content.description,content.influence,content.relationship}\n"
            "character_card:@type:CharacterCard[previous]\n"
            "scene_card:@type:SceneCard[previous]\n"
            "Previous Volume Info: @type:VolumeOutline[index=$current.volumeNumber-1].content\n"
            "Next, please create outline for Volume @self.content.volume_number\n"
        )},
        "WritingGuide": {
            "is_singleton": False,
            "default_ai_context_template": (
                "World Setting: @WorldSetting.content.world_view\n"
                "Organization Setting:@type:OrganizationCard[previous:global].{content.name,content.entity_type,content.life_span,content.description,content.influence,content.relationship}\n"
                "Current Volume Main Line:@parent.content.main_target\n"
                "Current Volume Branch Line:@parent.content.branch_line\n"
                "Stage Count and Entity Snapshot of this volume:@parent.{content.stage_count,content.entity_snapshot}\n"
                "Character Card Info:@type:CharacterCard[previous]\n"
                "Map/Scene Card Info:@type:SceneCard[previous]\n"
                "Please generate a Writing Guide for Volume @self.content.volume_number."
            )
        },
        "StageOutline": {"default_ai_context_template": (
            "World Setting: @WorldSetting.content.world_view\n"
            "Organization Setting:@type:OrganizationCard[previous:global].{content.name,content.entity_type,content.life_span,content.description,content.influence,content.relationship}\n"
            "Volume Main Line:@parent.content.main_target\n"
            "Volume Branch Line:@parent.content.branch_line\n"
            "Character Card Info:@type:CharacterCard[previous:global].{content.name,content.life_span,content.role_type,content.born_scene,content.description,content.personality,content.core_drive,content.character_arc}\n"
            "Map/Scene Card Info:@type:SceneCard[previous]\n"
            "Character Action Brief of this volume:@parent.content.character_action_list\n"
            "Previous Stage Story Outline, ensure chapter range and plot connection:@type:StageOutline[previous:global:1].{content.stage_name,content.reference_chapter,content.analysis,content.overview,content.entity_snapshot}\n"
            "Previous Chapter Outline Overview, ensure plot connection:@type:ChapterOutline[previous:global:1].{content.overview}\n"
            "Total StageCount of this volume: @parent.content.stage_count\n"
            "Note, must converge story according to volume main line within @parent.content.stage_count stages, and reach volume end entity snapshot status:@parent.content.entity_snapshot\n"
            "Writing precautions for this volume:@type:WritingGuide[sibling].content.content \n"
            "Next please create story outline for Stage @self.content.stage_number."
        )},
        # Chapter Outline
        "ChapterOutline": {"default_ai_context_template": (
            "word_view: @WorldSetting.content\n"
            "volume_number: @self.content.volume_number\n"
            "volume_main_target: @type:VolumeOutline[index=$current.volumeNumber].content.main_target\n"
            "volume_branch_line: @type:VolumeOutline[index=$current.volumeNumber].content.branch_line\n"
            "Entity action list of this volume: @parent.content.entity_action_list\n"
            "Current stage story overview: @stage:current.overview\n"
            "Current stage coverage chapter range: @stage:current.reference_chapter\n"
            "Previous chapter outline: @type:ChapterOutline[sibling].{content.chapter_number,content.overview}\n"
            "Please start creating outline for Chapter @self.content.chapter_number, ensuring coherence"
        )},
        "Chapter": {"editor_component": "CodeMirrorEditor", "is_ai_enabled": False, "default_ai_context_template": (
            "World Setting: @WorldSetting.content\n"
            "Organization Setting:@type:OrganizationCard[index=filter:content.name in $self.content.entity_list].{content.name,content.description,content.influence,content.relationship}\n"
            "Scene Card:@type:SceneCard[index=filter:content.name in $self.content.entity_list].{content.name,content.description}\n"
            "Current Story Stage Outline: @parent.content.overview\n"
            "Character Card:@type:CharacterCard[index=filter:content.name in $self.content.entity_list].{content.name,content.role_type,content.born_scene,content.description,content.personality,content.core_drive,content.character_arc,content.dynamic_info}\n"
            "Most recent chapter text, ensure plot connection:@type:Chapter[previous:1].{content.title,content.chapter_number,content.content}\n"
            "Participant Entity List, ensure generated content only involves these entities:@self.content.entity_list\n"
            "Please create chapter body content based on outline of Chapter @self.content.chapter_number @self.content.title @type:ChapterOutline[index=filter:content.title = $self.content.title].{content.overview}, can appropriately diverge and design plots not conflicting with outline to expand, making final content around 3000 words\n"
            "Note, when writing must ensure ending plot does not conflict with next chapter outline, and do not extract/design next chapter plot (if exists):@type:ChapterOutline[index=filter:content.volume_number = $self.content.volume_number && content.chapter_number = $self.content.chapter_number+1].{content.title,content.overview}\n"
            "Please combine writing guide requirements:@type:WritingGuide[index=filter:content.volume_number = $self.content.volume_number].{content.content}\n"
            )},
        "CharacterCard": {"default_ai_context_template": None},
        "SceneCard": {"default_ai_context_template": None},
        "OrganizationCard": {"default_ai_context_template": None},
    }

    # Type default AI param preset (Does not contain llm_config_id)
    DEFAULT_AI_PARAMS = {
        "SpecialAbility": {"prompt_name": "SpecialAbilityGeneration", "temperature": 0.6, "max_tokens": 4096, "timeout": 60},
        "OneSentenceSummary": {"prompt_name": "OneSentenceSummary", "temperature": 0.6, "max_tokens": 4096, "timeout": 60},
        "StoryOutline": {"prompt_name": "StoryOutline", "temperature": 0.7, "max_tokens": 8192, "timeout": 90},
        "WorldSetting": {"prompt_name": "WorldSetting", "temperature": 0.7, "max_tokens": 1500, "timeout": 90},
        "CoreBlueprint": {"prompt_name": "CoreBlueprint", "temperature": 0.7, "max_tokens": 8192  , "timeout": 120},
        "VolumeOutline": {"prompt_name": "VolumeOutline", "temperature": 0.7, "max_tokens": 8192, "timeout": 120},
        "WritingGuide": {"prompt_name": "WritingGuide", "temperature": 0.6, "max_tokens": 8192, "timeout": 90},
        "StageOutline": {"prompt_name": "StageOutline", "temperature": 0.7, "max_tokens": 8192, "timeout": 120},
        "ChapterOutline": {"prompt_name": "ChapterOutline", "temperature": 0.7, "max_tokens": 8192, "timeout": 90},
        "Chapter": {"prompt_name": "ContentGeneration", "temperature": 0.7, "max_tokens": 8192, "timeout": 90},
        "CharacterCard": {"prompt_name": "CharacterInfoExtraction", "temperature": 0.6, "max_tokens": 4096, "timeout": 60},
        "SceneCard": {"prompt_name": "ContentGeneration", "temperature": 0.6, "max_tokens": 4096, "timeout": 60},
        "OrganizationCard": {"prompt_name": "RelationExtraction", "temperature": 0.6, "max_tokens": 4096, "timeout": 60},
    }

    # Type name to built-in response model mapping (Used for generating json_schema)
    TYPE_TO_MODEL_KEY = {
        "Tags": "Tags",
        "SpecialAbility": "SpecialAbilityResponse",
        "OneSentenceSummary": "OneSentence",
        "StoryOutline": "ParagraphOverview",
        "WorldSetting": "WorldBuilding",
        "CoreBlueprint": "Blueprint",
        "VolumeOutline": "VolumeOutline",
        "WritingGuide": "WritingGuide",
        "StageOutline": "StageLine",
        "ChapterOutline": "ChapterOutline",
        "Chapter": "Chapter",
        "CharacterCard": "CharacterCard",
        "SceneCard": "SceneCard",
        "OrganizationCard": "OrganizationCard",
    }

    existing_types = db.exec(select(CardType)).all()
    existing_type_names = {ct.name for ct in existing_types}

    # Default llm_config_id: Take first available LLM config (if exists)
    default_llm = db.exec(select(LLMConfig)).first()

    for name, details in default_types.items():
        if name not in existing_type_names:
            # Directly store structure on card type (json_schema)
            schema = None
            try:
                model_class = RESPONSE_MODEL_MAP.get(TYPE_TO_MODEL_KEY.get(name))
                if model_class:
                    schema = model_class.model_json_schema(ref_template="#/$defs/{model}")
            except Exception:
                schema = None
            # AI param preset (llm_config_id chosen by frontend, not specified here)
            ai_params = DEFAULT_AI_PARAMS.get(name)
            if ai_params is not None:
                # If available default LLM exists, write its ID; avoid writing 0 causing frontend unrecognized
                ai_params = { **ai_params, "llm_config_id": (default_llm.id if default_llm else None) }
            card_type = CardType(
                name=name,
                model_name=TYPE_TO_MODEL_KEY.get(name, name),
                description=details.get("description", f"Default card type for {name}"),
                json_schema=schema,
                ai_params=ai_params,
                editor_component=details.get("editor_component"),
                is_ai_enabled=details.get("is_ai_enabled", True),
                is_singleton=details.get("is_singleton", False),
                default_ai_context_template=details.get("default_ai_context_template"),
                built_in=True,
            )
            db.add(card_type)
            logger.info(f"Created default card type: {name}")
        else:
            # Incremental update: Refresh type structure and meta info
            ct = next(ct for ct in existing_types if ct.name == name)
            try:
                model_class = RESPONSE_MODEL_MAP.get(TYPE_TO_MODEL_KEY.get(name))
                if model_class:
                    schema = model_class.model_json_schema(ref_template="#/$defs/{model}")
                    ct.json_schema = schema
            except Exception:
                pass
            # If ai_params missing, fill with preset (Do not overwrite user settings)
            if getattr(ct, 'ai_params', None) is None:
                preset = DEFAULT_AI_PARAMS.get(name)
                if preset is not None:
                    ct.ai_params = { **preset, "llm_config_id": (default_llm.id if default_llm else None) }
            # If model_name missing, fill with mapping
            if not getattr(ct, 'model_name', None):
                ct.model_name = TYPE_TO_MODEL_KEY.get(name, name)
            ct.editor_component = details.get("editor_component")
            ct.is_ai_enabled = details.get("is_ai_enabled", True)
            ct.is_singleton = details.get("is_singleton", False)
            ct.description = details.get("description", f"Default card type for {name}")
            ct.default_ai_context_template = details.get("default_ai_context_template")
            ct.built_in = True

    db.commit()
    logger.info("Default card types committed.")

# Initialize knowledge base (Import *.txt from bootstrap/knowledge directory)
def init_knowledge(db: Session):
    """
    Initialize knowledge base entries from files in the bootstrap/knowledge directory.

    Args:
        db: Database session.
    """
    knowledge_dir = os.path.join(os.path.dirname(__file__), 'knowledge')
    if not os.path.exists(knowledge_dir):
        logger.warning(f"Knowledge directory not found at {knowledge_dir}. Cannot load knowledge base.")
        return

    existing = {k.name: k for k in db.exec(select(Knowledge)).all()}
    created = 0
    updated = 0
    skipped = 0
    overwrite = str(os.getenv('BOOTSTRAP_OVERWRITE', '')).lower() in ('1', 'true', 'yes', 'on')

    for filename in os.listdir(knowledge_dir):
        if not filename.lower().endswith(('.txt', '.md')):
            continue
        file_path = os.path.join(knowledge_dir, filename)
        name = os.path.splitext(filename)[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read knowledge base file {file_path}: {e}")
            continue
        description = f"Built-in Knowledge Base: {name}"
        if name in existing:
            if overwrite:
                kb = existing[name]
                kb.content = content
                kb.description = description
                kb.built_in = True
                updated += 1
            else:
                skipped += 1
        else:
            db.add(Knowledge(name=name, description=description, content=content, built_in=True))
            created += 1

    if created or updated:
        db.commit()
        logger.info(f"Knowledge base initialization completed: Added {created}, Updated {updated} (overwrite={overwrite}, Skipped {skipped})")
    else:
        logger.info(f"Knowledge base is up to date (overwrite={overwrite}, Skipped {skipped}).")



# Initialize reserved project (__free__)
def init_reserved_project(db: Session):
    """Ensure a reserved project exists for archiving free cards across projects."""
    FREE_NAME = "__free__"
    exists = db.exec(_select(Project).where(Project.name == FREE_NAME)).first()
    if not exists:
        p = Project(name=FREE_NAME, description="System reserved project: Store free cards")
        db.add(p)
        db.commit()
        db.refresh(p)
        logger.info(f"Reserved project created: {FREE_NAME} (id={p.id})")
    else:
        # Incremental update can be done here (e.g. description field)
        pass


def _create_or_update_workflow(db: Session, name: str, description: str, dsl: dict, trigger_card_type: str, overwrite: bool):
    """Helper function to create or update single workflow and its triggers"""
    created_count = updated_count = skipped_count = 0
    
    # Process workflow
    wf = db.exec(select(Workflow).where(Workflow.name == name)).first()
    if not wf:
        wf = Workflow(name=name, description=description, is_built_in=True, is_active=True, version=1, dsl_version=1, definition_json=dsl)
        db.add(wf)
        db.commit()
        db.refresh(wf)
        created_count += 1
        logger.info(f"Built-in workflow created: {name} (id={wf.id})")
    else:
        if overwrite:
            wf.definition_json = dsl
            wf.is_built_in = True
            wf.is_active = True
            wf.version = 1
            db.add(wf)
            db.commit()
            updated_count += 1
            logger.info(f"Built-in workflow updated: {name} (id={wf.id})")
        else:
            skipped_count += 1
    
    # Process triggers
    tg = db.exec(select(WorkflowTrigger).where(WorkflowTrigger.workflow_id == wf.id, WorkflowTrigger.trigger_on == "onsave")).first()
    if not tg:
        tg = WorkflowTrigger(workflow_id=wf.id, trigger_on="onsave", card_type_name=trigger_card_type, is_active=True)
        db.add(tg)
        db.commit()
        created_count += 1
        logger.info(f"Trigger created: onsave -> {name}")
    else:
        if overwrite:
            tg.card_type_name = trigger_card_type
            tg.is_active = True
            db.add(tg)
            db.commit()
            updated_count += 1
            logger.info(f"Trigger updated: onsave -> {name}")
        else:
            skipped_count += 1
    
    return created_count, updated_count, skipped_count

def init_workflows(db: Session):
    """Initialize/Update built-in workflows (Standard format).
    Behavior controlled by environment variable BOOTSTRAP_OVERWRITE:
    - True: Force update DSL and triggers of existing workflows
    - False: Only create non-existent workflows, do not modify existing ones
    
    Current preset: WorldSetting -> Organization
    - Trigger: onsave, Card Type=WorldSetting
    - DSL:
      1) Card.Read (type_name=WorldSetting)
      2) List.ForEach ($.content.world_view.social_system.major_power_camps)
         Connect to:
            2.1) Card.UpsertChildByTitle (cardType=OrganizationCard, title={item.name}, useItemAsContent=true)
            2.2) Card.ModifyContent (setPath=world_view.social_system.major_power_camps, setValue=[])
    """
    overwrite = str(os.getenv('BOOTSTRAP_OVERWRITE', '')).lower() in ('1', 'true', 'yes', 'on')
    total_created = total_updated = total_skipped = 0
    name = "WorldSetting"
    dsl = {
        "dsl_version": 1,
        "name": name,
        "nodes": [
            {"id": "readself", "type": "Card.Read", "params": {"target": "$self", "type_name": "WorldSetting"}, "position": {"x": 40, "y": 80}},
            {"id": "foreachOrgs", "type": "List.ForEach", "params": {"listPath": "$.content.world_view.social_system.major_power_camps"}, "position": {"x": 460, "y": 80}},
            {"id": "upsertOrg", "type": "Card.UpsertChildByTitle", "params": {"cardType": "OrganizationCard", "title": "{item.name}", "useItemAsContent": True}, "position": {"x": 460, "y": 260}},
            {"id": "clearSource", "type": "Card.ModifyContent", "params": {"setPath": "world_view.social_system.major_power_camps", "setValue": []}, "position": {"x": 880, "y": 260}}
        ],
        "edges": [
            {"id": "e-readself-foreachOrgs", "source": "readself", "target": "foreachOrgs", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreachOrgs-upsertOrg", "source": "foreachOrgs", "target": "upsertOrg", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreachOrgs-clearSource", "source": "foreachOrgs", "target": "clearSource", "sourceHandle": "r", "targetHandle": "l"}
        ]
    }

    # First workflow: WorldSetting -> Organization
    c, u, s = _create_or_update_workflow(db, name, "Generate organization cards from worldview power list and clear source field", dsl, "WorldSetting", overwrite)
    total_created += c
    total_updated += u
    total_skipped += s

    # ---------------- CoreBlueprint · Drop Child Cards and Volumes ----------------
    name2 = "CoreBlueprint"
    dsl2 = {
        "dsl_version": 1,
        "name": name2,
        "nodes": [
            {"id": "read_bp", "type": "Card.Read", "params": {"target": "$self", "type_name": "CoreBlueprint"}, "position": {"x": 40, "y": 80}},
            {"id": "foreach_volumes", "type": "List.ForEachRange", "params": {"countPath": "$.content.volume_count", "start": 1}, "position": {"x": 460, "y": 80}},
            {"id": "upsert_volume", "type": "Card.UpsertChildByTitle", "params": {"parent": "$projectRoot", "cardType": "VolumeOutline", "title": "Volume {index}", "contentTemplate": {"volume_number": "{index}"}}, "position": {"x": 460, "y": 330}},
            {"id": "foreach_chars", "type": "List.ForEach", "params": {"listPath": "$.content.character_cards"}, "position": {"x": 880, "y": 80}},
            {"id": "upsert_char", "type": "Card.UpsertChildByTitle", "params": {"cardType": "CharacterCard", "title": "{item.name}", "contentPath": "item"}, "position": {"x": 880, "y": 260}},
            {"id": "foreach_scenes", "type": "List.ForEach", "params": {"listPath": "$.content.scene_cards"}, "position": {"x": 1300, "y": 80}},
            {"id": "upsert_scene", "type": "Card.UpsertChildByTitle", "params": {"cardType": "SceneCard", "title": "{item.name}", "contentPath": "item"}, "position": {"x": 1300, "y": 260}},
            {"id": "clear_lists", "type": "Card.ModifyContent", "params": {"contentMerge": {"character_cards": [], "scene_cards": []}}, "position": {"x": 1720, "y": 170}}
        ],
        "edges": [
            {"id": "e-read_bp-foreach_volumes", "source": "read_bp", "target": "foreach_volumes", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_volumes-upsert_volume", "source": "foreach_volumes", "target": "upsert_volume", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreach_volumes-foreach_chars", "source": "foreach_volumes", "target": "foreach_chars", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_chars-upsert_char", "source": "foreach_chars", "target": "upsert_char", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreach_chars-foreach_scenes", "source": "foreach_chars", "target": "foreach_scenes", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_scenes-upsert_scene", "source": "foreach_scenes", "target": "upsert_scene", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreach_scenes-clear_lists", "source": "foreach_scenes", "target": "clear_lists", "sourceHandle": "r", "targetHandle": "l"}
        ]
    }

    # Second workflow: CoreBlueprint
    c, u, s = _create_or_update_workflow(db, name2, "Blueprint generation: Create top-level volume and blueprint child character/scene cards, and clear blueprint lists", dsl2, "CoreBlueprint", overwrite)
    total_created += c
    total_updated += u
    total_skipped += s

    # ---------------- Volume Outline · Drop Child Cards ----------------
    name3 = "VolumeOutline"
    dsl3 = {
        "dsl_version": 1,
        "name": name3,
        "nodes": [
            {"id": "read_vol", "type": "Card.Read", "params": {"target": "$self", "type_name": "VolumeOutline"}, "position": {"x": 40, "y": 80}},
            {"id": "foreach_new_chars", "type": "List.ForEach", "params": {"listPath": "$.content.new_character_cards"}, "position": {"x": 460, "y": 80}},
            {"id": "upsert_char2", "type": "Card.UpsertChildByTitle", "params": {"cardType": "CharacterCard", "title": "{item.name}", "contentPath": "item"}, "position": {"x": 460, "y": 260}},
            {"id": "foreach_new_scenes", "type": "List.ForEach", "params": {"listPath": "$.content.new_scene_cards"}, "position": {"x": 880, "y": 80}},
            {"id": "upsert_scene2", "type": "Card.UpsertChildByTitle", "params": {"cardType": "SceneCard", "title": "{item.name}", "contentPath": "item"}, "position": {"x": 880, "y": 260}},
            {"id": "foreach_stage", "type": "List.ForEachRange", "params": {"countPath": "$.content.stage_count", "start": 1}, "position": {"x": 1300, "y": 80}},
            {"id": "upsert_stage", "type": "Card.UpsertChildByTitle", "params": {"cardType": "StageOutline", "title": "Stage {index}", "contentTemplate": {"stage_number": "{index}", "volume_number": "{$.content.volume_number}"}}, "position": {"x": 1300, "y": 260}},
            {"id": "upsert_guide", "type": "Card.UpsertChildByTitle", "params": {"cardType": "WritingGuide", "title": "WritingGuide", "contentTemplate": {"volume_number": "{$.content.volume_number}"}}, "position": {"x": 1720, "y": 170}}
        ],
        "edges": [
            {"id": "e-read_vol-foreach_new_chars", "source": "read_vol", "target": "foreach_new_chars", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_new_chars-upsert_char2", "source": "foreach_new_chars", "target": "upsert_char2", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreach_new_chars-foreach_new_scenes", "source": "foreach_new_chars", "target": "foreach_new_scenes", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_new_scenes-upsert_scene2", "source": "foreach_new_scenes", "target": "upsert_scene2", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreach_new_scenes-foreach_stage", "source": "foreach_new_scenes", "target": "foreach_stage", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_stage-upsert_stage", "source": "foreach_stage", "target": "upsert_stage", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreach_stage-upsert_guide", "source": "foreach_stage", "target": "upsert_guide", "sourceHandle": "r", "targetHandle": "l"}
        ]
    }

    # Third workflow: Volume Outline - Drop Child Cards
    c, u, s = _create_or_update_workflow(db, name3, "Volume Outline: Create stage outlines and writing guides, and land new character/scene child cards", dsl3, "VolumeOutline", overwrite)
    total_created += c
    total_updated += u
    total_skipped += s

    # ---------------- Stage Outline · Drop Chapter Cards ----------------
    name4 = "StageOutline"
    dsl4 = {
        "dsl_version": 1,
        "name": name4,
        "nodes": [
            {"id": "read_stage", "type": "Card.Read", "params": {"target": "$self", "type_name": "StageOutline"}, "position": {"x": 40, "y": 80}},
            {"id": "foreach_chapter_outline", "type": "List.ForEach", "params": {"listPath": "$.content.chapter_outline_list"}, "position": {"x": 460, "y": 80}},
            {"id": "upsert_outline", "type": "Card.UpsertChildByTitle", "params": {"cardType": "ChapterOutline", "title": "Chapter {item.chapter_number} {item.title}", "useItemAsContent": True}, "position": {"x": 460, "y": 260}},
            {"id": "upsert_chapter", "type": "Card.UpsertChildByTitle", "params": {"cardType": "Chapter", "title": "Chapter {item.chapter_number} {item.title}", "contentTemplate": {"volume_number": "{$.content.volume_number}", "stage_number": "{$.content.stage_number}", "chapter_number": "{item.chapter_number}", "title": "{item.title}", "entity_list": {"$toNameList": "item.entity_list"}, "content": ""}}, "position": {"x": 880, "y": 260}},
            {"id": "clear_outline", "type": "Card.ModifyContent", "params": {"setPath": "$.content.chapter_outline_list", "setValue": []}, "position": {"x": 1300, "y": 170}}
        ],
        "edges": [
            {"id": "e-read_stage-foreach_chapter_outline", "source": "read_stage", "target": "foreach_chapter_outline", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_chapter_outline-upsert_outline", "source": "foreach_chapter_outline", "target": "upsert_outline", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-foreach_chapter_outline-upsert_chapter", "source": "foreach_chapter_outline", "target": "upsert_chapter", "sourceHandle": "b", "targetHandle": "t"},
            {"id": "e-upsert_outline-upsert_chapter", "source": "upsert_outline", "target": "upsert_chapter", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-foreach_chapter_outline-clear_outline", "source": "foreach_chapter_outline", "target": "clear_outline", "sourceHandle": "r", "targetHandle": "l"}
        ]
    }

    # Fourth workflow: Stage Outline - Drop Chapter Cards
    c, u, s = _create_or_update_workflow(db, name4, "Stage Outline: Create/Update chapter outlines and chapter body child cards from chapter outline list, and clear list", dsl4, "StageOutline", overwrite)
    total_created += c
    total_updated += u
    total_skipped += s

    # ---------------- Project Create · Snowflake Method (onprojectcreate) ----------------
    name5 = "Project Create - Snowflake Method"
    dsl5 = {
        "dsl_version": 1,
        "name": name5,
        "nodes": [
            {"id": "upsert_tags", "type": "Card.UpsertChildByTitle", "params": {"parent": "$projectRoot", "cardType": "Tags", "title": "Tags"}, "position": {"x": 40, "y": 80}},
            {"id": "upsert_power", "type": "Card.UpsertChildByTitle", "params": {"parent": "$projectRoot", "cardType": "SpecialAbility", "title": "SpecialAbility"}, "position": {"x": 460, "y": 80}},
            {"id": "upsert_one_sentence", "type": "Card.UpsertChildByTitle", "params": {"parent": "$projectRoot", "cardType": "OneSentenceSummary", "title": "OneSentenceSummary"}, "position": {"x": 880, "y": 80}},
            {"id": "upsert_outline", "type": "Card.UpsertChildByTitle", "params": {"parent": "$projectRoot", "cardType": "StoryOutline", "title": "StoryOutline"}, "position": {"x": 1300, "y": 80}},
            {"id": "upsert_world", "type": "Card.UpsertChildByTitle", "params": {"parent": "$projectRoot", "cardType": "WorldSetting", "title": "WorldSetting"}, "position": {"x": 1720, "y": 80}},
            {"id": "upsert_blueprint", "type": "Card.UpsertChildByTitle", "params": {"parent": "$projectRoot", "cardType": "CoreBlueprint", "title": "CoreBlueprint"}, "position": {"x": 2140, "y": 80}}
        ],
        "edges": [
            {"id": "e-tags-power", "source": "upsert_tags", "target": "upsert_power", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-power-one", "source": "upsert_power", "target": "upsert_one_sentence", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-one-outline", "source": "upsert_one_sentence", "target": "upsert_outline", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-outline-world", "source": "upsert_outline", "target": "upsert_world", "sourceHandle": "r", "targetHandle": "l"},
            {"id": "e-world-blueprint", "source": "upsert_world", "target": "upsert_blueprint", "sourceHandle": "r", "targetHandle": "l"}
        ]
    }

    # Create/Update this workflow
    wf5 = db.exec(select(Workflow).where(Workflow.name == name5)).first()
    if not wf5:
        wf5 = Workflow(name=name5, description="Project Create: Initialize basic cards using Snowflake Method", is_built_in=True, is_active=True, version=1, dsl_version=1, definition_json=dsl5)
        db.add(wf5)
        db.commit()
        db.refresh(wf5)
        total_created += 1
        logger.info(f"Built-in workflow created: {name5} (id={wf5.id})")
    else:
        if overwrite:
            wf5.definition_json = dsl5
            wf5.is_built_in = True
            wf5.is_active = True
            wf5.version = 1
            db.add(wf5)
            db.commit()
            total_updated += 1
            logger.info(f"Built-in workflow updated: {name5} (id={wf5.id})")
        else:
            total_skipped += 1

    # Ensure onprojectcreate trigger exists
    if wf5 and wf5.id:
        tg5 = db.exec(select(WorkflowTrigger).where(WorkflowTrigger.workflow_id == wf5.id, WorkflowTrigger.trigger_on == "onprojectcreate")).first()
        if not tg5:
            tg5 = WorkflowTrigger(workflow_id=wf5.id, trigger_on="onprojectcreate", is_active=True)
            db.add(tg5)
            db.commit()
            total_created += 1
            logger.info(f"Trigger created: onprojectcreate -> {name5}")
        else:
            if overwrite:
                tg5.is_active = True
                db.add(tg5)
                db.commit()
                total_updated += 1
                logger.info(f"Trigger updated: onprojectcreate -> {name5}")
            else:
                total_skipped += 1


    if total_created > 0 or total_updated > 0:
        db.commit()
        logger.info(f"Workflow initialization completed: Added {total_created}, Updated {total_updated} (overwrite={overwrite}, Skipped {total_skipped}).")
    else:
        logger.info(f"All workflows are up to date (overwrite={overwrite}, Skipped {total_skipped}).")
