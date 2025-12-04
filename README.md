<div align="center">

# NovelForge

<p><strong>The Next Generation AI Novel Creation Engine</strong></p>

<p>
  <a href="#core-features">Core Features</a> •
  <a href="#changelog">Changelog</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#outlook">Outlook</a>
</p>


</div>

**NovelForge** is an AI-assisted writing tool capable of handling millions of words for long-form novel creation. It is not just an editor, but a solution that integrates world-building and structured content generation.

In long-form writing, maintaining consistency, ensuring controllability, and stimulating continuous inspiration are the biggest challenges. To this end, NovelForge is built around four core concepts: modular **"Cards"**, customizable **"Dynamic Output Models"**, flexible **"Context Injection"**, and the **"Knowledge Graph"** that guarantees consistency.

---

<a id="core-features"></a>
## ✨ Core Features

*   **📚 Dynamic Output Models**
    *   **Say goodbye to traditional handwritten JSON constraints!** Built on Pydantic, you can freely define the structure of any creative element (characters, scenes, outlines) through a visual interface. Every generation by the AI is forcibly validated to ensure the output is in the precise format you want, which is the cornerstone of highly structured and configurable content.

*   **✨ Free Context Injection (@DSL)**
    *   With simple `@` syntax, you can inject any card, any field, or any collection in the project into the prompt as needed. Whether it's "all enemies of the current character", "all scenes from the previous volume", or "all treasures with a level greater than 5", complex context retrieval is just a one-line expression, providing infinite possibilities for complex creative logic.

*   **🧠 Knowledge Graph Driven**
    *   To solve the most tricky consistency problems in long-form writing (such as character relationships, titles, stance changes), NovelForge integrates Neo4j. During the creation process, the system can automatically or manually extract relationship and dynamic information from the text. When generating subsequent content, these structured "facts" are dynamically injected, significantly reducing AI hallucinations and ensuring character behavior aligns with their persona and past experiences.

*   **🔮 Inspiration Assistant**
    *   The Inspiration Assistant makes the creative process more natural and efficient. You can talk to the assistant anytime, just like communicating with a partner, to discuss and modify any detail of a card without generating the whole content every time. It supports cross-project referencing, bringing card content from other projects directly into the conversation for comparison, reference, and brainstorming new ideas. When the conversation results are suitable, you can apply them to the card with one click, making the whole process intuitive and smooth.

*   **💡 Ideas Workbench**
    *   The Ideas Workbench is an independent space designed for brainstorming and idea organization. Here, you can jot down various ideas and create "free cards" not limited by projects. It supports cross-project referencing, allowing you to recall card content from multiple projects simultaneously, helping you break boundaries and combine brand new ideas. When an inspiration takes shape, you can move or copy it to a formal project with one click, letting creativity land smoothly.

*   **❄️ Snowflake Method Inspired**
    *   The project draws on the classic "Snowflake Method", guiding you from a "one-sentence summary", gradually expanding to an outline, worldview, blueprint, volumes, chapters, and finally the text. All these steps exist in the form of independent "Cards" and are organized in a tree structure, making your entire creative world clear at a glance.

*   **🛠️ Highly Configurable and Extensible**
    *   From AI model parameters and prompt templates to card types and content structures, almost every link in the project allows deep user customization. You can build a creative workflow that belongs entirely to you.

---

<a id="changelog"></a>

## 📅 Changelog

<details>

<summary>v0.8.3</summary>

- Inspiration Assistant Enhancement
  - Added ReAct mode: Compatible with more LLM models (text format tool calling), switchable between Standard/ReAct mode in settings.
    (Note: Due to time constraints, the ReAct mode implementation is relatively rough and may have bugs. It is recommended to prioritize models with good native tool calling support.)
  - Intelligent context enhancement: Tool return values now add parent card information, allowing AI to better understand card hierarchy.

- UI & Experience Optimization
  - Refactored reference card area: Fixed layout, always visible `...(N)` button, used Popover instead of Modal.
  - Optimized tool calling result display: Shows success/failure status, supports jumping to cards, collapsible to view full JSON.
  - Fixed reference card and model selection overlap issue, adjusted input box height.

- Code optimization and bug fixes

</details>

<details>

<summary>v0.8.2</summary>

- Optimized Inspiration Assistant tool calling, added automatic retry function. Configurable max retries via .env file.
- Enhanced card dragging function, allowing free sorting.
- Optimized Inspiration Assistant UI, supports markdown display.
- Bug fixes and code cleanup.

</details>

<details>

<summary>v0.8.0</summary>

- Chapter Editor Refactoring
  - Migrated from independent window to the middle column of the main editor for a unified editing experience.
  - Added right-click quick edit: Select text and right-click to input requirements for polishing/expansion.
  - Optimized context assembly: Automatically includes context during polishing/expansion for more natural transitions.
  - Dynamic highlighting of AI-generated content.

- Inspiration Assistant Enhancement
  - Added tool calling capability (Experimental): Directly create/modify cards in conversation, support searching, viewing type structures, etc.
  - History conversation management: Stores conversation history by project, supports adding/loading/deleting sessions.
  - Real-time tool calling feedback: Displays "Calling tool...", automatically refreshes card tree upon completion.
  - Optimized context construction: Automatically injects project structure tree, statistical information, operation history.

- Workflow System Optimization
  - Node automatic registration mechanism: Adding a new node requires only a one-line decorator, automatically synchronized by the frontend.
  - Dynamic node library: Dynamically loads node list from backend, zero-configuration extension.

- UI & Experience Optimization
  - Fixed multiple display issues in dark mode.
  - Optimized card editor layout and interaction details.
  - Improved visual feedback for streaming output.

Note: If you chose local development before, the current version update requires re-installing backend requirements.

</details>

<details>

<summary>v0.7.8</summary>

- Workflow System (Experimental) continued
  - Added "Trigger on Project Creation (onprojectcreate)", replacing old project templates with workflows.
  - Canvas interaction optimization: Drag to create nodes, delete connection lines, more accurate coordinate positioning.
  - Several usability optimizations for Workflow Studio and Node Parameter Panel.
  - Note: Workflow is still in the experimental stage, currently mainly used to gradually replace original hardcoded logic, there is still large room for improvement in extending new capabilities.

- Code Optimization
  - Cleaned up old project template related code and interface, unified into the workflow system.

</details>

<details>

<summary>v0.7.7</summary>

- Optimized Work Tag Card
  - Added tag items and option data.
  - Extracted tag item category data to be stored as knowledge base files. You can edit work tags in Settings-Knowledge Base and freely modify tag item categories.
- Added interruption function during Card AI generation.
- Code optimization and bug fixes. Configurable via .env whether to reset knowledge base, prompts, etc. on startup.

</details>

<details>

<summary>v0.7.6</summary>

- Enhanced LLM Management
  - LLM configuration supports "Test Connection".
  - Support usage settings: Set Token limit, call count limit (-1 means unlimited).
  - List displays "Used (Input/Output/Calls)" and provides "One-click Reset Statistics". (Currently, token usage is a rough estimate, different models may calculate differently, for reference only)

- Code optimization and experience improvement.

</details>

<details>
<summary>v0.7.5</summary>

- Optimization: Inspiration Assistant
  - Supports free citation of multiple card data (cross-project, deduplication, and source marking).
  - Select LLM model in conversation (can override card configuration).
  - Conversation history saved and restored by project, not lost on reload.
  - Several UI and interaction detail optimizations.

- Preliminary: Workflow (Experimental)
  - Added "Workflow Studio": Canvas (Vue Flow), parameter sidebar, node library, and trigger basic CRUD.
  - Running & Events: Supports SSE, `run_completed` carries `affected_card_ids`, frontend refreshes accurately by card granularity.
  - Important Note: Currently an experimental feature, UI interaction/DSL/Validation/Runner/Triggers etc. are still being perfected.

</details>

<details>
<summary>v0.7.0</summary>

- New: Inspiration Assistant
  - Conversational collaboration tool in the right panel, supports real-time discussion and iterative optimization of card content.
  - Cross-project card reference function, can inject card data from any project into the conversation to spark creative collisions.
  - Automatically reference the currently selected card for seamless context switching.
  - One-click "Finalize Generation", applying conversation results directly to card content.
  - Reset conversation function to easily start new creative discussions.

- New: Ideas Workbench
  - Independent window mode providing a focused environment for creative exploration.
  - Free card system, unconstrained by project structure.
  - Cross-project reference and creative fusion capabilities.
  - One-click move/copy free cards to formal projects.

- Optimization: Import Card Function
  - Upgraded "Import Free Card" to "Import Card", supporting import from any project.
  - Improved card selector, grouped by type and supports collapse/expand.
  - Optimized reference data caching to improve performance and response speed.

</details>

<details>
<summary>v0.6.5</summary>

- New: Project Templates - Migrated to Workflow System in v0.7.8
  - "Project Template" management added to settings page, supporting configuration of card types and order automatically created when creating a new project, forming a reusable creation pipeline; supports maintaining multiple templates.
  - Create new project supports selecting templates.
  - Backend added template data model and CRUD interface, automatically writes default project templates on application startup.

</details>

---

<a id="tech-stack"></a>
## 🛠️ Tech Stack

*   **Frontend:** Electron, Vue 3, TypeScript, Pinia, Element Plus
*   **Backend:** FastAPI, SQLModel (Pydantic + SQLAlchemy), Uvicorn
*   **Database:** SQLite (Core Data), Neo4j (Knowledge Graph)

---

<a id="getting-started"></a>
## 🚀 Getting Started

Whether you want to experience it directly or participate in development, it's easy to get started.

### 0. Core Dependency: Neo4j Desktop

**This is a necessary prerequisite for running the knowledge graph function.**

*   Please download and install **Neo4j Desktop**, recommended version **5.16** or higher.
*   Download link: [Neo4j Desktop](https://neo4j.com/download/)
*   After installation, create a local database instance and ensure it is in **Running** state. Default connection information can be configured in the `.env` file.
![alt text](docImgs/README/image-6.png)

### Method 1: Run from Source (Developer/Latest Features)

**1. Backend (Python / FastAPI)**
```bash
# Clone repository
git clone https://github.com/RhythmicWave/NovelForge.git
cd NovelForge/backend

# Install dependencies
pip install -r requirements.txt

# Modify backend/.env.example file to .env

# Run backend service
python main.py
```

**2. Frontend (Node.js / Electron)**
```bash
# Enter frontend directory
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Important: BOOTSTRAP_OVERWRITE in .env

> When the backend starts, the system will initialize/update built-in resources (knowledge base, prompts, workflows) as needed. Whether to overwrite updates is controlled by `BOOTSTRAP_OVERWRITE` in `.env`.

- Recommended settings:
  - If you have not directly modified built-in resources, it is recommended to set to:
    ```ini
    BOOTSTRAP_OVERWRITE=true
    ```
    This allows automatic synchronization of the latest built-in knowledge base/prompts/workflows when upgrading versions or restarting.
  - If you have directly modified "built-in" resources, it is recommended to set to `false` to avoid being overwritten.

- Suggestion (to avoid being overwritten):
  - Do not directly edit "built-in" resources.
  - If customization is needed, please create a new copy (duplicate knowledge base/prompts/workflows and rename), and modify on the copy. This way, even if `BOOTSTRAP_OVERWRITE=true` is set in the future, your custom copy will not be overwritten by the update logic.


### Method 2: Use Release Version (Quick Start)

Packaged release versions are published irregularly, ready to use without configuring a development environment.

1.  Go to the project's **Releases** page to download the latest portable compressed package (`.zip` or `.7z`).
2.  Unzip to any location.
3.  **(Important)** Before running, please ensure the database instance in Neo4j Desktop is started.
4.  Enter the unzipped folder, find the `backend` directory, and edit the `.env` file as needed to configure the database connection.
5.  Run `backend/NovelForgeBackend.exe` to start the backend service.
6.  Return to the previous level and run `NovelForge.exe` to start the main program.

> Most data is stored in the `backend/aiauthor.db` database. When updating versions/migrating, just copy this database file to the corresponding location.
---

## ✍️ Creative Process

1.  **Configure Large Language Model (LLM)**
    *   After the first startup, add your AI model configuration in settings, such as API Key, Base URL, etc.
    ![alt text](docImgs/README/image.png)
    It is recommended to use Gemini 2.5Pro level LLMs for creation.

2.  **Create Project and Initialize Workflow**
    *   When creating a new project, you can choose an initialization workflow (usually `onprojectcreate` type) to automatically create preset cards. The system has a built-in "Project Creation · Snowflake Method" workflow, which will automatically create a complete card tree according to the Snowflake Method.
    ![alt text](docImgs/README/image-1.png)

3.  **Top-Down, Fill Core Settings**
    *   Start from the highest level card and use AI to fill in the content one by one. For example, generate a "Story Outline" based on a "One-sentence Summary", then generate "Worldview" and "Core Blueprint".
    Basically, every step provides an AI generation option.
    After completing the core blueprint card creation, click Save, and the corresponding volume cards will be automatically created according to the number of volumes.
    Continue to complete the volume outline creation, starting from Volume 1.
    After completion, stage outline sub-cards and writing guide cards will be automatically created according to the number of stages. It is recommended to generate the writing guide card first to generate writing guidance information, and then proceed with stage outline card creation.
    ![alt text](docImgs/README/image-2.png)

4.  **Use Inspiration Assistant to Refine Content**
    *   During the writing process, if you want to further polish or optimize card content, you can use the Inspiration Assistant on the right at any time.
    *   Select any card, and the Inspiration Assistant will automatically read the content of that card for your reference and thinking.
    *   You can ask the assistant specific questions directly, such as "Is this character's motivation reasonable?" or "How to make this scene more tense?".
    *   The Inspiration Assistant will give targeted suggestions based on the current card content, and you can communicate with the assistant repeatedly to gradually perfect your ideas.
    *   Through the "Add Reference" button, you can also add relevant card content from the current project or other projects into the conversation to spark more creative sparks.
    *   The Inspiration Assistant has the ability to perceive context and call tools to modify/create card content (Experimental).
    ![Alt text](docImgs/README/image-20.png)

5.  **After completing the stage outline creation, automatically generate chapter outlines and chapter text cards, and automatically inject entities that need to participate in each chapter.**
    ![alt text](docImgs/README/image-3.png)

6.  **Enter Chapter Creation**
    *   After completing the above steps, click the corresponding chapter text card to open the chapter editor and enter the core writing interface. The context panel on the right will automatically prepare all the background information required for the current chapter for you.
    ![Alt text](docImgs/README/image-27.png)
    
    *    Click Continue Writing for AI generation (if there is no content, it will automatically start writing from scratch).
    *    If you are not satisfied with the generated content, you can select the content, right-click for quick editing, enter requirements, and click Polish/Expand to rewrite this part of the content.
    ![Alt text](docImgs/README/image-8.png)

    *   After the content creation is completed, click Graph Relation to parse the relationships between characters and store them in the knowledge graph for reference during subsequent writing.
    ![Alt text](docImgs/README/image-7.png)
    After extraction is complete, click Confirm to save to the neo4j database.
    ![alt text](docImgs/README/image-5.png)

    *    It is recommended to extract character dynamic information again, using a lower-cost model for extraction.
  

    *    After the above steps are completed, when proceeding to the next chapter creation, information on relevant participating entities is automatically injected.
    ![alt text](docImgs/README/image-9.png)

7.  **Ideas Workbench: Capture Creative Sparks**
    *   Have a new idea but don't know which project it belongs to? Click the "Ideas" button at the top of the page to open the independent Ideas Workbench window.
    *   Here, you can jot down various ideas and freely create different types of cards without considering the project structure, focusing on putting inspiration into practice.
    *   The Inspiration Assistant on the right supports referencing card content from any project, making it convenient for you to cross-project consult, compare, and combine, sparking more creativity.
    *   When an idea gradually takes shape, simply use the "Move/Copy to Project" function at the top to classify the free card into a formal project with one click, naturally connecting creativity to subsequent creation.
    ![Alt text](docImgs/README/image-21.png)
    ![Alt text](docImgs/README/image-22.png)
---

## ⚙️ Advanced Features and Configuration

Although NovelForge provides a recommended creative process, its true power lies in its high flexibility. You can completely discard presets and use the following tools to assemble a creative system exclusive to you.

### Schema-first: Type/Instance Structure and Parameters

*   In `Settings -> Card Types`, use the structure builder to define `json_schema` for the type (supports basic types, relation(embed), tuple, etc.). The type Schema will serve as the default structure for cards of that type.
    ![alt text](docImgs/README/image-10.png)
    ![alt text](docImgs/README/image-11.png)

*   In a specific card, you can open `Structure` (Schema Studio) to overwrite the structure of that card instance, or "Apply to Type" with one click.
    ![alt text](docImgs/README/image-12.png)

    ![alt text](docImgs/README/image-13.png)

    After applying to type, subsequent creation of cards of that type will use the new structure.

*   Card AI Parameters: Open the parameter layer through the "Model" button in the editor toolbar, set `llm_config_id`, `prompt_name`, `temperature`, `max_tokens`, `timeout`..
    ![alt text](docImgs/README/image-14.png)

*  After completing the above settings, you can create cards of that type in the project and perform AI generation. The frontend will send the "Effective Schema" of the card to the backend for structured validation and output.
    ![alt text](docImgs/README/image-15.png)
    When creating a new card, you can also drag directly from an existing card to the bottom to automatically create it.
    ![alt text](docImgs/README/image-16.png)

    ![alt text](docImgs/README/image-17.png)

*  Schema supports embedding (`$ref` to type `$defs`), allowing combination and reuse of existing structures, facilitating complex capability building.

    ![alt text](docImgs/README/image-18.png)
    
Note: Try to add new models instead of modifying existing model structures to avoid conflicts with existing data.


### Prompt Workshop

*   Behind all AI functions are editable prompt templates. You can modify preset templates here or create brand new ones.
*   **Knowledge Base Injection**: Supports dynamically referencing "Knowledge Base" content in prompts via `@KB{name=Knowledge Base Name}` syntax, providing richer background information for AI.

### Context Injection (@DSL) Details

This is a feature of NovelForge. It allows you to precisely reference any data in the project in the prompt template using the `@` symbol to inject as context.

*   **Reference by Title**: `@Card Title` or `@Card Title.content.Some Field`
*   **Reference by Type**: `@type:Character Card` (All character cards)
*   **Special References**: `@self` (Current card), `@parent` (Parent card)
*   **Powerful Filters**:
    *   `[previous]`: Get the previous card at the same level.
    *   `[previous:global:n]`: Get the nearest n cards of the same type in the global order (tree pre-order).
    *   `[sibling]`: Get all sibling cards at the same level.
    *   `[index=...]`: Get by index, supports expressions, e.g., `$self.content.volume_number - 1`.
    *   `[filter:...]`: Filter by condition, e.g., `[filter:content.level > 5]` or `[filter:content.name in $self.content.entity_list]`.
*   **Field Level Selection**: You can select the entire card data, or select individual fields of the card.

For example, referencing the chapter titles and original text of the last 3 chapters:
![Alt text](docImgs/README/image-23.png)

### Workflow System (Experimental)

> Note: The workflow system is currently an experimental feature. The current goal is to "gradually replace the original hardcoded process" (such as automatically creating sub-cards when saving, project initialization, etc.) to obtain better visualization and orchestratability; there is still significant room for improvement in "extending new capabilities, generalizing node ecosystem, complex conditions/parallelism", etc., and it will be continuously improved in subsequent versions.

The Workflow System allows you to orchestrate the creative process into visual, reusable flows and execute them automatically at the right time.

#### Workflow Studio

- Visit the "Workflow" page to enter the visual workflow editor.
- Create nodes from the bottom node library by dragging and dropping, and define the execution order by connecting lines.
- Supported node types:
  - `Card.Read`: Read card content into workflow context.
  - `Card.UpsertChildByTitle`: Create or update sub-cards.
  - `Card.ModifyContent`: Modify card content.
  - `List.ForEach`: Iterate through array to execute sub-flows.
  - `List.ForEachRange`: Loop execution by number range.
- The smart parameter panel automatically displays configurable parameters based on the node type, supporting field path selection and real-time validation.

![Alt text](docImgs/README/image-24.png)

#### Trigger Configuration

Each workflow can configure one or more triggers to define when to execute automatically:

- **Trigger on Save (onsave)**: Automatically execute when a card of a specified type is saved.
- **Trigger on Generation Finish (ongenfinish)**: Automatically execute after AI generation is completed.
- **Manual Trigger (manual)**: Manually execute via right-click menu.
- **Trigger on Project Creation (onprojectcreate)**: Automatically execute when creating a new project, used for project initialization.

![Alt text](docImgs/README/image-25.png)

#### Built-in Workflow Templates

The system presets multiple common workflows, which can be used directly or as references:

- **Project Creation · Snowflake Method**: Automatically create initial card structure according to the Snowflake Method when creating a new project.
- **Worldview · Convert Organization**: Automatically generate organization cards from the power list in the worldview setting.
- **Core Blueprint · Drop Sub-cards**: Automatically create character cards, scene cards, and volume cards based on blueprint content.
- **Volume Outline · Drop Sub-cards**: Automatically create stage outlines and writing guides based on volume outlines.
- **Stage Outline · Drop Chapter Cards**: Automatically create chapter outlines and text cards based on the chapter list in the stage outline.

#### Project Initialization Workflow

When creating a new project, you can choose a workflow with an `onprojectcreate` trigger as the project template:

- Default selection "Project Creation · Snowflake Method", automatically creating work tags, cheats, one-sentence summary, story outline, worldview settings, core blueprint, etc. cards.
- You can also create your own project initialization workflow in Workflow Studio to fully customize the project starting structure.
- Supports complex initialization logic, such as creating different card structures based on conditions.

![Alt text](docImgs/README/image-26.png)

---

## License
This project uses a dual license authorization model:

- By default, this project is licensed under the GNU Affero General Public License v3.0 (AGPLv3).
- Providing service-based commercial use: Providing this project (or its modified version) as a backend to third parties in the form of SaaS, hosting, or other forms requires obtaining a commercial authorization license from the author.

Please comply with the open source license terms and obtain corresponding authorization in applicable scenarios.

---

## 📂 Project Structure

```
NovelForge/
  ├── backend/        # FastAPI Backend
  │   ├── app/
  │   │   ├── api/        # API Routes
  │   │   ├── db/         # Database Models & Sessions
  │   │   ├── schemas/    # Pydantic Data Models
  │   │   └── services/   # Core Business Logic
  │   └── main.py       # Entry Point
  │
  └── frontend/       # Electron + Vue3 Frontend
      └── src/
          ├── main/       # Electron Main Process
          ├── preload/    # Preload Scripts
          └── renderer/   # Vue Renderer Process
              └── src/
                  ├── components/ # Vue Components
                  ├── services/   # Frontend Services
                  ├── stores/     # Pinia State Management
                  └── views/      # Page Views
```

---

<a id="outlook"></a>
## Outlook

NovelForge is still in the early stages of iteration. The author is well aware that the project still has huge room for improvement in creative process, consistency maintenance, UI design, interaction experience, etc.

The best tools come from the wisdom of the community. Whether you are a creator or a developer, we sincerely welcome you:

*   Submit valuable feature suggestions or feedback in **Issues**.
*   Share your unique insights on the creative process.



## TODO

- [ ] **Enhance Knowledge Graph Injection**: Implement smarter, more automated relationship and fact injection mechanisms to further reduce AI hallucinations.
- [ ] **Optimize Creative Process**: Provide more flexible and powerful process orchestration and guidance functions to adapt to different creative styles.
- [ ] **Improve Interaction Experience**: Continuously polish UI/UX to make it more intuitive and efficient, reducing unnecessary operations.
