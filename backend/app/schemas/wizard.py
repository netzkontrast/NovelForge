from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional, List, Tuple, Any, Union

from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional, List, Tuple, Any, Union

from .entity import CharacterCard as CharacterCard  # Replace simplified model with complete character card
from .entity import SceneCard as SceneCard
from .entity import OrganizationCard as OrganizationCard
from .entity import EntityType as EntityType


# --- Schemas for Tags ---

class Tags(BaseModel):
    """
    Unified Tag Model.
    """
    theme: str = Field(default="", description="Theme category, format: Main-Sub")
    audience: Literal['通用','男生', '女生'] = Field(default='通用', description="Target audience (General/Male/Female)")
    narrative_person: Literal['第一人称', '第三人称'] = Field(default='第三人称', description="Narrative perspective (First/Third)")
    story_tags: List[Tuple[str, Literal['低权重', '中权重', '高权重']]] = Field(default=[], description="Category tags and weight levels (Low/Medium/High)")
    affection: str = Field(default="", description="Emotional relationship tag")


class SpecialAbility(BaseModel):
    name: str = Field(description="Name of the special ability/cheat")
    description: str = Field(description="Detailed description of the special ability")


class SpecialAbilityResponse(BaseModel):
    """0: Request model for designing special ability based on tags"""
    special_abilities_thinking: str = Field(description="Creative thinking process from tags to special ability.",examples=["Sample output, for learning thinking process only, do not be influenced by specific content: Based on tags 'Rebirth' and 'Invincible Flow', I need to design a cheat that allows the protagonist to constantly try and become stronger, eventually reaching an invincible state. Simply rebirth once is not enough to support the long-term development of 'Invincible Flow', so deepen the 'Rebirth' feature into 'Infinite Resurrection and Time Regression' ability, retaining experience and memory each resurrection. This fits 'Rebirth' and provides logical support for protagonist's 'Invincible' path. Also combining 'Otherworld Continent' and 'Civilization Deduction' background, this ability allows protagonist to accumulate knowledge and experience through repeated trial and error when facing unknown world, achieving dimensional strike and rising rapidly. This cheat setting can create strong expectation for readers on how protagonist uses this ability to solve dilemmas and overturn old order."])
    special_abilities: Optional[List[SpecialAbility]] = Field(None, description="Main special ability info. Can be specific systems, simulators etc., or some advantage/talent/physique etc. e.g. protagonist rebirth or time travel, their foreknowledge is also a cheat.")


class OneSentence(BaseModel):
    """1: Request model for designing one-sentence summary based on tags and special ability"""
    one_sentence_thinking: str = Field(description="Creative thinking process from tags/special ability to one-sentence summary.",examples=["Sample output, for learning thinking process only: Considering 'Fantasy-Otherworld Continent' theme and 'Time Travel', 'Otherworld Science Flow' tags, I first need to build a cross-world story framework. Modern kendo master meeting otherworld mage is a good entry point, 'Forbidden Magic Portal' cheat provides reasonable opportunity. Also 'Single CP' emotional tag requires this relationship to be an important clue. 'Civilization Collision' and 'Otherworld Science Flow' tags suggest protagonist brings modern knowledge advantage, forming unique conflict and spectacle. Combining these elements, I decided to build a story about modern person entering magic world, influencing entire otherworld fate through knowledge advantage and personal growth."])
    one_sentence: str = Field(description="One sentence summary of the entire novel")


class ParagraphOverview(BaseModel):
    """2: Request model for expanding one-sentence summary to paragraph overview"""
    overview_thinking: str = Field(description="Creative thinking process from one-sentence summary to paragraph outline.",examples=["Sample output, for learning thinking process only: Based on one-sentence summary, further think about specific story unfolding. Starting from 'Time Travel' tag, need to explain protagonist's identity change and initial dilemma. 'Villain Flow' and 'Behind-the-scenes Flow' determine protagonist must use non-traditional villain means. 'Farming Flow' suggests detailed description of demon society development process. 'Arrogance Talent' cheat provides unique way for protagonist to solve problems. The whole story needs to show how protagonist uses modern thinking and resourcefulness to complete demon transformation and peaceful infiltration of human world within limited time."])
    overview: str = Field(description="Expanded novel outline")
    

# --- Simplified AI Request Model ---

class SimpleAIRequest(BaseModel):
    """Simplified AI request model, directly passing string input"""
    input_text: str = Field(description="String input constructed according to training data format")
    llm_config_id: Optional[int] = Field(default=1, description="LLM Config ID")
    prompt_name: Optional[str] = Field(description="Prompt name, use task name if not specified")
    response_model_name: Optional[str] = Field(description="Response model name")



class SocialSystem(BaseModel):
    power_structure: str = Field(description="Power structure (e.g., Feudal Dynasty/Capital Federation)")
    currency_system: List[str] = Field(default=["Gold Coin"], description="Currency system")
    background:List[str]=Field(description="Power structure background, history legends etc. of this social system")
    major_power_camps: List[OrganizationCard] = Field(description="Major organizations/sects/factions, generate core organizations with cross-volume long-term influence only here.")
    civilization_level: Optional[str] = Field(description="Technology/Civilization development level")

class CoreSystem(BaseModel):
    system_type: str = Field(description="System type (Power/Social/Tech/Ability etc.)")
    name: str = Field(description="System name (e.g. Douqi/Capital Rules/Court Politics)")
    levels: Optional[List[str]] = Field(None, description="Level/Class division (Optional)")
    source: str = Field(description="Source of Energy/Power (e.g. Reiki/Capital/Imperial Power)")

class SettingItem(BaseModel):
    title: str = Field(description="Setting title, e.g.: Geography Cosmology, History Legends, Race Settings etc.")
    description: str = Field(description="Specific description of this setting item")

class WorldviewTemplate(BaseModel):
    """
    Worldview Template
    """
    world_name: str = Field(min_length=2, description="World Name")
    core_conflict: str = Field(description="World core conflict (e.g. Resource Scramble/Racial Hatred)")
    social_system: SocialSystem = Field(description="Social System")
    power_systems: List[CoreSystem] = Field(default=[],description="Core system list, can include power/tech/ability etc., avoid overly complex settings, max 2 systems. If realistic/historical genre, can be empty",max_length=2)
    # key_settings: Optional[List[SettingItem]] = Field(description="Other key worldview settings (Optional)")

class WorldBuilding(BaseModel):
    world_view_thinking: str = Field(description="Worldview design thinking process",examples=["Sample output, for learning thinking process only: When designing worldview, I hope to build a framework that is both close to reality and full of sci-fi imagination. First, for reader immersion, I choose to set story background in modern city, so conflict between protagonist's special ability and daily life will have more tension. But modern city alone is not enough to support 'Space-Time Travel' theme, so I introduce 'Dream World' as bridge between reality and future. This dream world is initially a reflection of reality, but with protagonist's intervention, it changes drastically, even appearing 'Old Sea' and 'New Mirage City' differences, adding layers and exploration space to worldview. To explain this change, I need rigorous space-time laws, like 'Space-Time Butterfly Effect', 'Timeline Correction' etc. These laws not only explain interaction between dream and reality, but also provide logical basis for plot advancement and conflict generation. Also to carry 'Civilization Deduction' and 'Otherworld Science Flow' tags, I conceive a hidden organization behind scenes, mastering technology beyond era and deep understanding of space-time laws. Their existence is embodiment of world core conflict - control over historical direction. In social system, real world is modern society, while future dream might present highly developed tech but deformed society (like points supremacy) or apocalyptic wasteland (like radiation disaster), this contrast enhances story depth and warning significance. Core drive system, besides protagonist's dream ability, needs 'Super-Space-Time Particles' scientific concepts as power source and theoretical support, making entire worldview self-consistent and full of exploration potential under sci-fi framework."])
    world_view: WorldviewTemplate


# === Step 3: Blueprint Schemas ===


class Blueprint(BaseModel):
    volume_count: int = Field(description="Expected number of volumes, usually 3~6 volumes")
    character_thinking: str = Field(description="Character design thinking process",examples=["Sample output, for learning thinking process only: In designing characters, I uphold 'Diversity and Complementarity' principle, ensuring each core character plays unique role and forms close connection with protagonist group.\n\nFirst is protagonist Wang Xiaoming. As 'Time Traveler', must have modern thinking and adaptability. I set him as Kendo master, allowing fast integration into otherworld and echoing otherworld 'Swordsmanship' system. His core drive is 'High Reward' and 'Protecting Haiwen', transforming him from bystander to participant and guardian. His growth arc will be 'From ordinary person in reality to savior in otherworld', closely linked to 'Evolution Flow' tag.\n\nHeroine Haiwen is story guide. Must be core figure in otherworld, with strong magic talent and unique background. I set her as 'Genius Mage' and 'Royal Marriage Fugitive', providing initial dilemma and motivation. Her 'Flash Marriage' with protagonist quickly establishes CP relationship and lays foundation for emotional development. Her core drive is 'Escape Marriage' and 'Save World', finding balance between personal and world fate. Her character arc is 'From fugitive to Royal Court Mage saving world', showing her growth and responsibility.\n\nHeath as main villain, must be powerful and mysterious. I set her as 'Haiwen's Aunt' and 'Evil Mage', kinship adds complexity and emotional tension. Her core motivation is 'Destroy World', related to curse of lost civilization. Her character arc is 'From genius mage to destroyer, finally choosing to leave', adding tragic color to ending.\n\nLin Xiaoxue acts as bridge to real world, her 'Scholar' setting allows providing modern knowledge to otherworld, reflecting 'Otherworld Science Flow' and 'Civilization Collision' tags.\n\nThrough these character designs, I hope to build a character ensemble full of tension, rich emotion, and jointly driving grand narrative."])
    character_cards: List[CharacterCard] = Field(description="Core character card list, generate core characters with cross-volume long-term influence only here")
    
    # organization_thinking:str=Field(description="Organization/Faction/Camp design thinking process, distinguish from scene")
    # organization_cards: List[OrganizationCard] = Field(description="Core Organization/Faction/Camp card list, generate core organizations with cross-volume long-term influence only here. Distinguish from scene_cards")
    
    scene_thinking: str = Field(description="Scene design thinking process",examples=["Sample output, for learning thinking process only: When designing map and scenes, I follow principle of local to global, known to unknown, progressive layering, ensuring story rhythm and gradual unfolding of worldview. Core idea: Each scene is not just location, but key to driving plot, showing character growth, revealing worldview secrets.\n\n**Volume 1: First Entry & Initial Exploration**\nI first set Blue Star (Real World) as starting point and protagonist's 'Known World' for reader immersion. Then introduce otherworld core region via 'Molanta' and 'Lante Kingdom (Moon City)', typical scenes of magic and sword, also initial conflict point. Molanta as mage sanctuary is Haiwen's background and place for protagonist magic learning. Moon City represents political center and war frontline. These scenes let protagonist adapt to otherworld, show adaptability and initial strength improvement, and introduce main factions.\n\n**Volume 2: Faction Development & Alliance Building**\nWith plot development, need broader stage to show protagonist group expansion and grand plan. So introduce 'Lante Kingdom (Jinghong City)' as new ally base, becoming strategic center for princess restoration and alliance building. Also to show war comprehensiveness, I design 'Gaolan Federation (Linya City/Central Watchtower/Sunrise Mountain)' as important battlefield and political gaming ground, driving alliance formation through conflicts here. Liberating 'Moon City' is climax of this volume, marking key step in restoration plan. These scenes shift protagonist group from passive defense to active attack, showing strategic vision and leadership, facilitating alliance.\n\n**Volume 3: Unification War & Ancient Secrets Revealed**\nEntering Volume 3, story focus shifts to unifying continent and revealing deeper secrets. So expand scenes to 'Sun Moon Kingdom' and 'Saint Valen Empire (Tesistineburg)'. Sun Moon Kingdom is must-pass for coalition, showing protagonist group power through battles here. Empire capital 'Tesistineburg' is final battle location, its fall marks end of old order. These scenes complete unification cause, revealing deep worldview secrets, foreshadowing final crisis.\n\n**Volume 4: Doomsday Crisis & Final Choice**\nLast volume, world faces destruction, scene design revolves around 'Save' and 'End'. 'Linya City' and 'Jinghong City' reappear, but carrying hope of collecting royal blood and tech survival. Final 'Origin Place/Burning Peak' is decisive battle stage, source of curse and key to breaking it. These scenes concentrate all clues, complete final redemption, and let protagonist group make final choice on belonging, concluding the story."])
    scene_cards: List[SceneCard] = Field(description="Main Map/Scene/Dungeon card list, generate core map/scene with cross-volume long-term influence only here. Note connection with organization_cards, e.g. if a map is activity range of an organization, specify it.")


# === Step 4: Volume Outline Schemas===

class CharacterAction(BaseModel):
    """Character Card, covering various info"""
    name: Optional[str] = Field(default="", description="Character name")
    description: Optional[str] = Field(default="", description="Narrate main deeds of this character in this volume from first person perspective")

class StoryLine(BaseModel):
    """Story line info, from primitive_models/Step2Model.py"""
    story_type: Optional[Literal['主线', '辅线']] = Field(default='主线', description="Story line type (Main/Branch)")
    name: Optional[str] = Field(default="", description="Use a simple name to represent this line")
    overview: Optional[str] = Field(default="", description="Story line content overview, be concise, all involved scenes, characters etc. should be reflected in this overview.")


class VolumeOutline(BaseModel):
    """
    Core data model for Volume Outline
    """
    volume_number: Optional[int] = Field(default=1, description="Volume Number")
    thinking: Optional[str] = Field(default="", description="Based on provided worldview, characters, maps/dungeons, think how to unfold this volume, what main/branch lines to design? How to drive plot development?",examples=["Sample output, for learning thinking process only: As opening volume, my core thinking is how to quickly establish protagonist's 'Infinite Resurrection' cheat feature, combine it with cruel otherworld background, create strong survival pressure, driving protagonist to rise from desperation. I need to design a progressive growth path, let protagonist start from dying person, accumulate experience and knowledge through each resurrection, gradually adapt to environment, finally stand firm in City A, accumulate primitive capital, establish initial power. Meanwhile for subsequent grand narrative, must bury worldview foreshadowing in this volume, e.g. social solidification, higher civilization manipulation, revealed gradually through protagonist view. In character building, introduce group of partners with different personalities, they are protagonist's help and contrast protagonist's strength and uniqueness. In terms of satisfaction points, protagonist using cheat 'foreknowledge' advantage to achieve dimensional strike in stock market and adventure, and final revenge on early villains, will be important design points."])
    main_target: StoryLine = Field(description="Design main line target based on thinking, to what extent should protagonist develop? Need accurate data description")
    branch_line: Optional[List[StoryLine]] = Field(default=[], description="Branch or side lines of this volume, include 1~3 core branch lines")
    character_thinking: Optional[str] = Field(default="", description="Combine overview, provided character info (personality, core drive, arc etc.), think what to drive character entities to do in this volume? Which characters to appear? Need auxiliary characters?",examples=["Sample output, for learning thinking process only: In this volume, I will focus on driving protagonist to fully use 'Infinite Resurrection' ability, growing from survivor in desperation to leader of City A. He will learn combat skills, social rules through repeated trial and error, and use information gap to accumulate wealth in stock market. I also need to introduce Sun Qingyu, Wang Huo, Han Tian as core supporting roles, playing important auxiliary roles in protagonist growth: Sun Qingyu as first partner and loyal follower, witnessing and participating in early rise; Wang Huo providing tech support and knowing 'Resurrection' secret; Han Tian providing key help in equipment modification and R&D. Their appearance and interaction drive plot and enrich protagonist persona, showing his intelligence and resourcefulness. Lin Sen as main villain of this volume, will be concrete target of protagonist's initial resistance against old order, constantly stimulating protagonist to become stronger and revenge."])
    new_character_cards: Optional[List[CharacterCard]] = Field(default=None, description="If new key characters added, supplement info here, life_span is short-term. Avoid introducing new characters if unnecessary")
    new_scene_cards: Optional[List[SceneCard]]= Field(default=None, description="If new key scenes/maps/dungeons added, supplement info here, life_span is short-term. Avoid introducing new scenes if unnecessary")
    # stage_lines: Optional[List[StageLine]] = Field(default=[], description="Design detailed story context of this volume, divided by stages, pay attention to appropriate detail when cutting story stages, each stage chapter span not too large, best not exceed 30 chapters")
    stage_count:int=Field(description="Expected stage plot of this volume, divide volume plot into n stages to narrate, usually 4~6")
    character_action_list: Optional[List[CharacterAction]] = Field(default=[], description="Outline key character entity actions and changes based on volume design")
    entity_snapshot: Optional[List[str]] = Field(default=[], description="At end of volume, key entity (mainly character) snapshot status info, including level/cultivation realm, wealth, techniques etc. accurate info, to conclude plot")

class WritingGuide(BaseModel):
    """
    Writing Guide, used to guide AI on details to pay attention to when writing in specific volume.
    """
    volume_number: int = Field(description="Volume number corresponding to this writing guide")
    content: str = Field(description="Specific content generated by AI based on methodology to guide writing of this volume. Word count controlled within 1000 words.",min_length=100)

class ChapterOutline(BaseModel):
    """Chapter Outline"""
    volume_number: Optional[int] = Field(default=0, description="Volume number, if not found, set to 0")
    stage_number:Optional[int]=Field(default=1,description="Which stage this chapter belongs to, starting from 1")
    title: Optional[str] = Field(default="", description="Chapter Title")
    chapter_number: Optional[int] = Field(default=1, description="Chapter Number")
   
    overview: Optional[str] = Field(default="", description="Chapter main content overview, appropriate detail, avoid being too thin. If protagonist has significant improvement, relevant info cannot be omitted, need accurate data description (e.g. strength greatly improved, economy or resources increased by how much).",min_length=100)
    entity_list: Optional[List[str]] = Field(
        default=[],
        description="List of important entities appearing in chapter, must be selected from context provided organization/character/scene card entities, no adding/creating new; entity name must be pure name (no brackets/remarks). Note, to streamline context, avoid redundant entities not appearing in this chapter in entity list",
    )

    

class StageLine(BaseModel):
    """Story info divided by stage"""
    volume_number:int=Field(default=1,description="Which volume this story stage belongs to")
    stage_number:int=Field(default=1,description="Which stage this story stage is, starting from 1")
    stage_name: Optional[str] = Field(default="", description="Use a name or sentence to briefly summarize this stage")
    reference_chapter: Tuple[int, int] = Field(description="Start and end chapter numbers of this part of plot, span usually around 10~20 chapters")
    analysis: Optional[str] = Field(default="", description="From perspective of experienced web novel writer substituting author's first person view, how 'I' think about setting this part of plot, what role does this part play for volume main/branch line? What is the satisfaction point of this stage? Any hook/suspense at end?")
    overview: Optional[str] = Field(default="", description="Concrete overview of this stage plot content, appropriate detail, involved main entities like character, scene/map, organization etc. should be reflected. Also, if protagonist has significant improvement (e.g. improved strength or status, increased wealth or resources), relevant info needs accurate data description, cannot be omitted")
    chapter_outline_list:Optional[List[ChapterOutline]]=Field(description="Generate required chapter outlines based on reference_chapter, overview")
    entity_snapshot: Optional[List[str]] = Field(default=[], description="At end of stage, key entity (mainly character) snapshot status info, including level/cultivation realm, wealth, techniques etc. accurate info, to conclude plot, ensuring plot development leads entity status to converge to entity status at end of this volume.")


# === Step 6: Batch Chapter Outline Schemas===

class Chapter(BaseModel):
    volume_number: Optional[int] = Field(default=0, description="Volume number, if not found, set to 0")
    stage_number:Optional[int]=Field(default=1,description="Which stage this chapter belongs to, starting from 1")
    title: Optional[str] = Field(default="", description="Chapter Title")
    chapter_number: Optional[int] = Field(default=1, description="Chapter Number")

    entity_list: List[str] = Field(
        default=[],
        description="List of important entities participating in chapter, must be selected from provided entities; name must be pure name (no brackets/remarks)",
    )
    content:Optional[str]=Field(default="",description="Chapter text content")
    

