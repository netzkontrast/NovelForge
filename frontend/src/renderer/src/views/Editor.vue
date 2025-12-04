<template>
  <div class="editor-layout">
    <!-- Left Card Navigation Tree -->
    <el-aside class="sidebar card-navigation-sidebar" :style="{ width: leftSidebarWidth + 'px' }" @contextmenu.prevent="onSidebarContextMenu">
      <div class="sidebar-header">
        <h3 class="sidebar-title">Creation Cards</h3>
        
      </div>

      <!-- Upper Pane (Type List + Free Card Lib) -->
      <div class="types-pane" :style="{ height: typesPaneHeight + 'px' }" @dragover.prevent @drop="onTypesPaneDrop">
        <div class="pane-title">Existing Card Types</div>
        <el-scrollbar class="types-scroll">
          <ul class="types-list">
            <li v-for="t in cardStore.cardTypes" :key="t.id" class="type-item" draggable="true"
                @dragstart="onTypeDragStart(t)">
              <span class="type-name">{{ t.name }}</span>
            </li>
          </ul>
        </el-scrollbar>
      </div>
      <!-- Inner Resizer (Vertical) -->
      <div class="inner-resizer" @mousedown="startResizingInner"></div>

      <!-- Lower Pane: Project Card Tree -->
      <div class="cards-pane" :style="{ height: `calc(100% - ${typesPaneHeight + innerResizerThickness}px)` }" @dragover.prevent @drop="onCardsPaneDrop">
        <div class="cards-title">
          <div class="cards-title-text">Current Project: {{ projectStore.currentProject?.name }}</div>
          <div class="cards-title-actions">
            <el-button size="small" type="primary" @click="openCreateRoot">New Card</el-button>
            <el-button v-if="!isFreeProject" size="small" @click="openImportFreeCards">Import Cards</el-button>
          </div>
        </div>
        <el-tree
          ref="treeRef"
          v-if="groupedTree.length > 0"
          :data="groupedTree"
          node-key="id"
          :default-expanded-keys="expandedKeys"
          :expand-on-click-node="false"
          @node-click="handleNodeClick"
          @node-expand="onNodeExpand"
          @node-collapse="onNodeCollapse"
          draggable
          :allow-drop="handleAllowDrop"
          :allow-drag="handleAllowDrag"
          @node-drop="handleNodeDrop"
          class="card-tree"
        >
          <template #default="{ node, data }">
            <el-dropdown class="full-row-dropdown" trigger="contextmenu" @command="(cmd:string) => handleContextCommand(cmd, data)">
              <div class="custom-tree-node full-row" @dragover.prevent @drop="(e:any) => onExternalDropToNode(e, data)" @dragenter.prevent>
                <el-icon class="card-icon"> 
                  <component :is="getIconByCardType(data.card_type?.name || data.__groupType)" />
                </el-icon>
                <span class="label">{{ node.label || data.title }}</span>
                <span v-if="data.children && data.children.length > 0" class="child-count">{{ data.children.length }}</span>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <template v-if="!data.__isGroup">
                    <el-dropdown-item command="create-child">New Child Card</el-dropdown-item>
                    <el-dropdown-item command="rename">Rename</el-dropdown-item>
                    <el-dropdown-item command="edit-structure">Edit Structure</el-dropdown-item>
                    <el-dropdown-item command="add-as-reference">Add as Reference</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>Delete Card</el-dropdown-item>
                  </template>
                  <template v-else>
                    <el-dropdown-item command="delete-group" divided>Delete all cards in this group</el-dropdown-item>
                  </template>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-tree>
        <el-empty v-else description="No Cards" :image-size="80"></el-empty>
      </div>

      <!-- Blank Area Context Menu -->
      <span ref="blankMenuRef" class="blank-menu-ref" :style="{ position: 'fixed', left: blankMenuX + 'px', top: blankMenuY + 'px', width: '1px', height: '1px' }"></span>
      <el-dropdown v-model:visible="blankMenuVisible" trigger="manual">
        <span></span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="openCreateRoot">New Card</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-aside>
    
    <!-- Resizer -->
    <div class="resizer left-resizer" @mousedown="startResizing('left')"></div>

    <!-- Main Content Area -->
    <el-main class="main-content">
      <el-tabs v-model="activeTab" type="border-card" class="main-tabs">
        <el-tab-pane label="Card Market" name="market">
          <CardMarket @edit-card="handleEditCard" />
        </el-tab-pane>
        <el-tab-pane label="Editor" name="editor">
          <template v-if="activeCard">
            <CardEditorHost :card="activeCard" :prefetched="prefetchedContext" />
          </template>
          <el-empty v-else description="Please select a card from left to edit" />
        </el-tab-pane>
      </el-tabs>
    </el-main>

    <!-- Right Assistant Sidebar -->
    <div class="resizer right-resizer" @mousedown="startResizing('right')"></div>
    <el-aside class="sidebar assistant-sidebar" :style="{ width: rightSidebarWidth + 'px' }">
      <!-- Chapter Body Card: Show 4 Tabs -->
      <template v-if="isChapterContent">
        <el-tabs v-model="activeRightTab" type="card" class="right-tabs">
          <el-tab-pane label="Assistant" name="assistant">
            <AssistantPanel
              :resolved-context="assistantResolvedContext"
              :llm-config-id="assistantParams.llm_config_id as any"
              :prompt-name="'Chat'"
              :temperature="assistantParams.temperature as any"
              :max_tokens="assistantParams.max_tokens as any"
              :timeout="assistantParams.timeout as any"
              :effective-schema="assistantEffectiveSchema"
              :generation-prompt-name="assistantParams.prompt_name as any"
              :current-card-title="assistantSelectionCleared ? '' : (activeCard?.title as any)"
              :current-card-content="assistantSelectionCleared ? null : (activeCard?.content as any)"
              @refresh-context="refreshAssistantContext"
              @reset-selection="resetAssistantSelection"
              @finalize="assistantFinalize"
              @jump-to-card="handleJumpToCard"
            />
          </el-tab-pane>
          
          <el-tab-pane label="Context" name="context">
            <ContextPanel 
              :project-id="projectStore.currentProject?.id"
              :prefetched="prefetchedContext"
              :volume-number="chapterVolumeNumber"
              :chapter-number="chapterChapterNumber"
              :participants="chapterParticipants"
            />
          </el-tab-pane>
          
          <el-tab-pane label="Extract" name="extract">
            <ChapterToolsPanel />
          </el-tab-pane>
          
          <el-tab-pane label="Outline" name="outline">
            <OutlinePanel 
              :active-card="activeCard"
              :volume-number="chapterVolumeNumber"
              :chapter-number="chapterChapterNumber"
            />
          </el-tab-pane>
        </el-tabs>
      </template>
      
      <!-- Other Cards: Only Assistant -->
      <AssistantPanel
        v-else
        :resolved-context="assistantResolvedContext"
        :llm-config-id="assistantParams.llm_config_id as any"
        :prompt-name="'Chat'"
        :temperature="assistantParams.temperature as any"
        :max_tokens="assistantParams.max_tokens as any"
        :timeout="assistantParams.timeout as any"
        :effective-schema="assistantEffectiveSchema"
        :generation-prompt-name="assistantParams.prompt_name as any"
        :current-card-title="assistantSelectionCleared ? '' : (activeCard?.title as any)"
        :current-card-content="assistantSelectionCleared ? null : (activeCard?.content as any)"
        @refresh-context="refreshAssistantContext"
        @reset-selection="resetAssistantSelection"
        @finalize="assistantFinalize"
        @jump-to-card="handleJumpToCard"
      />
    </el-aside>
  </div>

  <!-- New Card Dialog -->
  <el-dialog v-model="isCreateCardDialogVisible" title="New Creation Card" width="500px">
    <el-form :model="newCardForm" label-position="top">
      <el-form-item label="Card Title">
        <el-input v-model="newCardForm.title" placeholder="Please enter card title"></el-input>
      </el-form-item>
      <el-form-item label="Card Type">
        <el-select v-model="newCardForm.card_type_id" placeholder="Please select card type" style="width: 100%">
          <el-option
            v-for="type in cardStore.cardTypes"
            :key="type.id"
            :label="type.name"
            :value="type.id"
          ></el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="Parent Card (Optional)">
                <el-tree-select
           v-model="newCardForm.parent_id"
           :data="cardTree"
           :props="treeSelectProps"
           check-strictly
           :render-after-expand="false"
           placeholder="Select parent card"
           clearable
           style="width: 100%"
         />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="isCreateCardDialogVisible = false">Cancel</el-button>
      <el-button type="primary" @click="handleCreateCard">Create</el-button>
    </template>
  </el-dialog>

  <!-- Import Card Dialog -->
  <el-dialog v-model="importDialog.visible" title="Import Cards" width="900px" class="nf-import-dialog">
    <div style="display:flex; gap:12px; align-items:center; margin-bottom:8px; flex-wrap: wrap;">
      <el-select v-model="importDialog.sourcePid" placeholder="Source Project" style="width:220px" @change="onImportSourceChange($event as any)">
        <el-option v-for="p in importDialog.projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-input v-model="importDialog.search" placeholder="Search source card title..." clearable style="flex:1; min-width: 200px" />
      <el-select v-model="importFilter.types" multiple collapse-tags placeholder="Filter by Type" style="min-width:220px;" :max-collapse-tags="2">
        <el-option v-for="t in cardStore.cardTypes" :key="t.id" :label="t.name" :value="t.id!" />
      </el-select>
      <el-tree-select
        v-model="importDialog.parentId"
        :data="cardTree"
        :props="treeSelectProps"
        check-strictly
        :render-after-expand="false"
        placeholder="Target Parent (Optional)"
        clearable
        popper-class="nf-tree-select-popper"
        style="width: 300px"
      />
    </div>
    <el-table :data="filteredImportCards" height="360px" border @selection-change="onImportSelectionChange">
      <el-table-column type="selection" width="48" />
      <el-table-column label="Title" prop="title" min-width="220" />
      <el-table-column label="Type" min-width="160">
        <template #default="{ row }">{{ row.card_type?.name }}</template>
      </el-table-column>
      <el-table-column label="Created At" min-width="160">
        <template #default="{ row }">{{ (row as any).created_at }}</template>
      </el-table-column>
    </el-table>
    <template #footer>
      <el-button @click="importDialog.visible = false">Cancel</el-button>
      <el-button type="primary" :disabled="!selectedImportIds.length" @click="confirmImportCards">Import Selected</el-button>
    </template>
  </el-dialog>

  <SchemaStudio v-model:visible="schemaStudio.visible" :mode="'card'" :target-id="schemaStudio.cardId" :context-title="schemaStudio.cardTitle" @saved="onCardSchemaSaved" />

  
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, defineAsyncComponent, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { Plus } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { 
  CollectionTag,
  MagicStick,
  ChatLineRound,
  List,
  Connection,
  Tickets,
  Notebook,
  User,
  OfficeBuilding,
  Document,
} from '@element-plus/icons-vue'
import type { components } from '@renderer/types/generated'
import { useSidebarResizer } from '@renderer/composables/useSidebarResizer'
import AssistantPanel from '@renderer/components/assistants/AssistantPanel.vue'
import ContextPanel from '@renderer/components/panels/ContextPanel.vue'
import ChapterToolsPanel from '@renderer/components/panels/ChapterToolsPanel.vue'
import OutlinePanel from '@renderer/components/panels/OutlinePanel.vue'
import { useCardStore } from '@renderer/stores/useCardStore'
import { useEditorStore } from '@renderer/stores/useEditorStore'
import { useProjectStore } from '@renderer/stores/useProjectStore'
import { useAssistantStore } from '@renderer/stores/useAssistantStore'
import SchemaStudio from '@renderer/components/shared/SchemaStudio.vue'
import { getCardSchema, createCardType } from '@renderer/api/setting'
import { getProjects } from '@renderer/api/projects'
import { getCardsForProject, copyCard, getCardAIParams } from '@renderer/api/cards'
import { generateAIContent } from '@renderer/api/ai'
 
 // Mock components that will be created later
 const CardEditorHost = defineAsyncComponent(() => import('@renderer/components/cards/CardEditorHost.vue'));
 const CardMarket = defineAsyncComponent(() => import('@renderer/components/cards/CardMarket.vue'));


 type Project = components['schemas']['ProjectRead']
 type CardRead = components['schemas']['CardRead']
 type CardCreate = components['schemas']['CardCreate']

 // Import Dialog State
 const importDialog = ref<{ visible: boolean; search: string; parentId: number | null; sourcePid: number | null; projects: Array<{id:number; name:string}> }>({ visible: false, search: '', parentId: null, sourcePid: null, projects: [] })
 const importSourceCards = ref<CardRead[]>([])
 const selectedImportIds = ref<number[]>([])
 
 // Filter: Type + Title
 const importFilter = ref<{ types: number[] }>({ types: [] })
 
 const filteredImportCards = computed(() => {
   const q = (importDialog.value.search || '').trim().toLowerCase()
   let list = importSourceCards.value || []
   if (importFilter.value.types.length) {
     const typeSet = new Set(importFilter.value.types)
     list = list.filter(c => c.card_type?.id && typeSet.has(c.card_type.id))
   }
   if (q) {
     list = list.filter(c => (c.title || '').toLowerCase().includes(q))
   }
   return list
 })

 async function openImportFreeCards() {
   try {
     const list = await getProjects()
     const currentId = projectStore.currentProject?.id
     importDialog.value.projects = (list || []).filter(p => p.id !== currentId).map(p => ({ id: p.id!, name: p.name! }))
     importDialog.value.sourcePid = importDialog.value.projects[0]?.id ?? null
     selectedImportIds.value = []
     await onImportSourceChange(importDialog.value.sourcePid as any)
     importDialog.value.visible = true
   } catch { ElMessage.error('Failed to load source projects') }
 }

 async function onImportSourceChange(pid: number | null) {
   importSourceCards.value = []
   if (!pid) return
   try { importSourceCards.value = await getCardsForProject(pid) } catch { importSourceCards.value = [] }
 }

 function onImportSelectionChange(rows: any[]) {
   selectedImportIds.value = (rows || []).map(r => Number(r.id)).filter(n => Number.isFinite(n))
 }

 async function confirmImportCards() {
   try {
     const pid = projectStore.currentProject?.id
     if (!pid) return
     const targetParent = importDialog.value.parentId || null
     for (const id of selectedImportIds.value) {
       await copyCard(id, { target_project_id: pid, parent_id: targetParent as any })
     }
     await cardStore.fetchCards(pid)
     ElMessage.success('Selected cards imported')
     importDialog.value.visible = false
   } catch { ElMessage.error('Import failed') }
 }

 // Props
 const props = defineProps<{
   initialProject: Project
 }>()

 // Store
 const cardStore = useCardStore()
 const { cardTree, activeCard, cards } = storeToRefs(cardStore)
 const editorStore = useEditorStore()
 const { expandedKeys } = storeToRefs(editorStore)
 const projectStore = useProjectStore()
 const assistantStore = useAssistantStore()
 const isFreeProject = computed(() => (projectStore.currentProject?.name || '') === '__free__')

  // --- Frontend Auto Grouper ---
 // When any "number of types > 2" in direct child cards of a node, create a virtual group node for that type;
 // Types with quantity <= 2 remain as is (even if only one type in whole parent, group if > 2).
 // Structure strictly frontend, does not affect backend data
 interface TreeNode { id: number | string; title: string; children?: TreeNode[]; card_type?: { name: string }; __isGroup?: boolean; __groupType?: string }


 function buildGroupedNodes(nodes: any[]): any[] {
  return nodes.map(n => {
    const node: TreeNode = { ...n }
    // Group node itself does not participate in grouping logic, recurse its children
    if ((n as any).__isGroup) {
      if (Array.isArray(n.children) && n.children.length > 0) {
        node.children = buildGroupedNodes(n.children as any)
      }
      return node
    }
    if (Array.isArray(n.children) && n.children.length > 0) {
      // Count child node types
      const byType: Record<string, any[]> = {}
      n.children.forEach((c: any) => {
        const typeName = c.card_type?.name || 'Unknown Type'
        if (!byType[typeName]) byType[typeName] = []
        byType[typeName].push(c)
      })
      const types = Object.keys(byType)
        const grouped: any[] = []
        types.forEach(t => {
          const list = byType[t]
        if (list.length > 2) {
            // Create virtual group node (id uses string to avoid conflict)
            grouped.push({
              id: `group:${n.id}:${t}`,
              title: `${t}`,
              __isGroup: true,
              __groupType: t,
              children: list.map(x => ({ ...x }))
            })
          } else {
          // Quantity 1 or 2, flat
          grouped.push(...list)
          }
        })
      // Recurse children (Group node and normal node both recurse children)
      node.children = grouped.map((x: any) => {
        const copy = { ...x }
        if (Array.isArray(copy.children) && copy.children.length > 0) {
          copy.children = buildGroupedNodes(copy.children as any)
        }
        return copy
      })
    }
    return node
  })
}

// Compute grouped tree based on original cardTree
const groupedTree = computed(() => buildGroupedNodes(cardTree.value as unknown as any[]))

// Local State
const activeTab = ref('market')
const activeRightTab = ref('assistant')
const isCreateCardDialogVisible = ref(false)
const prefetchedContext = ref<any>(null)
const newCardForm = reactive<Partial<CardCreate>>({
  title: '',
  card_type_id: undefined,
  parent_id: '' as any
})

// Blank area menu state
const blankMenuVisible = ref(false)
const blankMenuX = ref(0)
const blankMenuY = ref(0)
const blankMenuRef = ref<HTMLElement | null>(null)

// Composables
  const { leftSidebarWidth, rightSidebarWidth, startResizing } = useSidebarResizer()
  
 // Unify TreeSelect Style/Props
 const treeSelectProps = {
   value: 'id',
   label: 'title',
   children: 'children'
 } as const
 
 // Inner vertical split: Type/Card height
 const typesPaneHeight = ref(180)
 const innerResizerThickness = 6
 // Left width resize uses useSidebarResizer.startResizing('left')

 function startResizingInner() {
   const startY = (event as MouseEvent).clientY
   const startH = typesPaneHeight.value
   const onMove = (e: MouseEvent) => {
     const dy = e.clientY - startY
     const next = Math.max(120, Math.min(startH + dy, 400))
     typesPaneHeight.value = next
   }
   const onUp = () => {
     window.removeEventListener('mousemove', onMove)
     window.removeEventListener('mouseup', onUp)
   }
   window.addEventListener('mousemove', onMove)
   window.addEventListener('mouseup', onUp)
 }

// Drag: Create new instance from Type to Card Area
function onTypeDragStart(t: any) {
  try { (event as DragEvent).dataTransfer?.setData('application/x-card-type-id', String(t.id)) } catch {}
}
async function onCardsPaneDrop(e: DragEvent) {
 try {
   const typeId = e.dataTransfer?.getData('application/x-card-type-id')
   if (typeId) {
     // Drag from type list to blank, create new card at root
     newCardForm.title = (cardStore.cardTypes.find(ct => ct.id === Number(typeId))?.name || 'New Card')
     newCardForm.card_type_id = Number(typeId)
     newCardForm.parent_id = '' as any
     handleCreateCard()
     return
   }
   // Drag copy from __free__ project
   const freeCardId = e.dataTransfer?.getData('application/x-free-card-id')
   if (freeCardId) {
     await copyCard(Number(freeCardId), { target_project_id: projectStore.currentProject!.id, parent_id: null as any })
     await cardStore.fetchCards(projectStore.currentProject!.id)
     ElMessage.success('Copied free card to root')
     return
   }
   // Note: Card drag within project handled by el-tree native drag (handleNodeDrop)
 } catch {}
}

// Promote Card Instance to Type: Drop in Upper Pane
async function onTypesPaneDrop(e: DragEvent) {
 try {
   const cardIdStr = e.dataTransfer?.getData('application/x-card-id')
   const cardId = cardIdStr ? Number(cardIdStr) : NaN
   if (!cardId || Number.isNaN(cardId)) return
   // Read effective schema of card
   const resp = await getCardSchema(cardId)
   const effective = resp?.effective_schema || resp?.json_schema
   if (!effective) { ElMessage.warning('This card has no available structure, cannot generate type'); return }
   // Default name: Card title or "New Type"
   const old = cards.value.find(c => (c as any).id === cardId)
   const defaultName = (old?.title || 'New Type') as string
   const { value } = await ElMessageBox.prompt('Create card type from this instance, please enter type name:', 'Create Card Type', {
     inputValue: defaultName,
     confirmButtonText: 'Create',
     cancelButtonText: 'Cancel',
     inputValidator: (v:string) => v.trim().length > 0 || 'Name cannot be empty'
   })
   const finalName = String(value).trim()
   await createCardType({ name: finalName, description: `Default card type for ${finalName}`, json_schema: effective } as any)
   ElMessage.success('Card type created from instance')
   await cardStore.fetchCardTypes()
 } catch (err) {
   // User cancel or error ignore
 }
}

// ===== el-tree Native Drag Function =====

// Control which nodes can be dragged
function handleAllowDrag(draggingNode: any): boolean {
  // Group nodes cannot be dragged
  if (draggingNode.data.__isGroup) {
    return false
  }
  return true
}

// Control drop position
// type: 'prev' | 'inner' | 'next'
function handleAllowDrop(draggingNode: any, dropNode: any, type: 'prev' | 'inner' | 'next'): boolean {
  // Group node only allow 'inner' (put card into group)
  if (dropNode.data.__isGroup) {
    return type === 'inner'
  }
  
  // Normal card nodes allow all
  return true
}

// Handle drop complete
async function handleNodeDrop(
  draggingNode: any,
  dropNode: any,
  dropType: 'before' | 'after' | 'inner',
  ev: DragEvent
) {
  try {
    const draggedCard = draggingNode.data
    const targetCard = dropNode.data
    
    console.log('🔄 [Drag] Drag card:', draggedCard.title, 'Target:', targetCard.title || targetCard.__groupType, 'Pos:', dropType)
    
    // If dragged into group, set parent_id to null (root)
    if (targetCard.__isGroup && dropType === 'inner') {
      // Calc root next display_order
      const rootCards = cards.value.filter(c => c.parent_id === null)
      const maxOrder = rootCards.length > 0 ? Math.max(...rootCards.map(c => c.display_order || 0)) : -1
      
      await cardStore.modifyCard(draggedCard.id, { 
        parent_id: null,
        display_order: maxOrder + 1
      }, { skipHooks: true })
      ElMessage.success(`Moved "${draggedCard.title}" to root`)
      await cardStore.fetchCards(projectStore.currentProject!.id)
      
      // Record move operation
      assistantStore.recordOperation(projectStore.currentProject!.id, {
        type: 'move',
        cardId: draggedCard.id,
        cardTitle: draggedCard.title,
        cardType: draggedCard.card_type?.name || 'Unknown',
        detail: 'Moved from child to root'
      })
      
      // Update project structure
      updateProjectStructureContext(activeCard.value?.id)
      return
    }
    
    // If dragged into card (become child)
    if (dropType === 'inner') {
      // Calc child next display_order
      const children = cards.value.filter(c => c.parent_id === targetCard.id)
      const maxOrder = children.length > 0 ? Math.max(...children.map(c => c.display_order || 0)) : -1
      
      await cardStore.modifyCard(draggedCard.id, { 
        parent_id: targetCard.id,
        display_order: maxOrder + 1
      }, { skipHooks: true })
      ElMessage.success(`Set "${draggedCard.title}" as child of "${targetCard.title}"`)
      await cardStore.fetchCards(projectStore.currentProject!.id)
      
      // Record move operation
      assistantStore.recordOperation(projectStore.currentProject!.id, {
        type: 'move',
        cardId: draggedCard.id,
        cardTitle: draggedCard.title,
        cardType: draggedCard.card_type?.name || 'Unknown',
        detail: `Set as child of "${targetCard.title}" (${targetCard.card_type?.name || 'Unknown'} #${targetCard.id})`
      })
      
      // Update project structure
      updateProjectStructureContext(activeCard.value?.id)
      return
    }
    
    // If dragged before/after card (sibling sort)
    const newParentId = targetCard.parent_id || null
    
    // Get all siblings, sort by display_order (exclude dragged card)
    const siblings = cards.value
      .filter(c => (c.parent_id || null) === newParentId && c.id !== draggedCard.id)
      .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    
    // Find target index
    const targetIndex = siblings.findIndex(c => c.id === targetCard.id)
    
    // Build new order array
    let newSiblings = [...siblings]
    if (dropType === 'before') {
      newSiblings.splice(targetIndex, 0, draggedCard)
    } else {
      newSiblings.splice(targetIndex + 1, 0, draggedCard)
    }
    
    // Batch update display_order
    const updates: Array<{ card_id: number; display_order: number; parent_id?: number | null }> = []
    
    newSiblings.forEach((card, index) => {
      if (card.id === draggedCard.id) {
        updates.push({
          card_id: card.id,
          display_order: index,
          parent_id: newParentId
        })
      } else if (card.display_order !== index) {
        updates.push({
          card_id: card.id,
          display_order: index,
          parent_id: card.parent_id || null  // Keep original parent_id
        })
      }
    })
    
    // Call batch update API
    if (updates.length > 0) {
      const { batchReorderCards } = await import('@renderer/api/cards')
      await batchReorderCards({ updates })
    }
    
    ElMessage.success(`Adjusted position of "${draggedCard.title}"`)
    await cardStore.fetchCards(projectStore.currentProject!.id)
    
    // Record move operation
    const targetCardTitle = targetCard?.title || 'Root'
    const positionText = dropType === 'before' ? 'before' : 'after'
    let moveDetail = `Moved to ${positionText} "${targetCardTitle}"`
    
    // Mark if parent changed
    if (draggedCard.parent_id !== newParentId) {
      const cardMap = new Map(cards.value.map(c => [(c as any).id, c.title]))
      const oldParentName = draggedCard.parent_id 
        ? cardMap.get(draggedCard.parent_id) || 'Unknown'
        : 'Root'
      const newParentName = newParentId 
        ? cardMap.get(newParentId) || 'Unknown'
        : 'Root'
      moveDetail += ` (from "${oldParentName}" to "${newParentName}")`
    }
    
    assistantStore.recordOperation(projectStore.currentProject!.id, {
      type: 'move',
      cardId: draggedCard.id,
      cardTitle: draggedCard.title,
      cardType: draggedCard.card_type?.name || 'Unknown',
      detail: moveDetail
    })
    
    // Update project structure
    updateProjectStructureContext(activeCard.value?.id)
    
  } catch (err: any) {
    console.error('Drag failed:', err)
    ElMessage.error(err?.message || 'Drag failed')
    // Refresh to restore
    await cardStore.fetchCards(projectStore.currentProject!.id)
    updateProjectStructureContext(activeCard.value?.id)
  }
}

// --- Drag: External (Type List, Free Card) to Card Tree ---

function getDraggedTypeId(e: DragEvent): number | null {
 try {
   const raw = e.dataTransfer?.getData('application/x-card-type-id') || ''
   const n = Number(raw)
   return Number.isFinite(n) && n > 0 ? n : null
 } catch { return null }
}

async function onExternalDropToNode(e: DragEvent, nodeData: any) {
 // Handle drag from type list or cross-project
 const typeId = getDraggedTypeId(e)
 if (typeId) {
   // Drag create new card from type list
   if (nodeData?.__isGroup) return
   const newCard = await cardStore.addCard({ title: 'New Card', card_type_id: typeId, parent_id: nodeData?.id } as any)
   
   // Record create
   if (newCard && projectStore.currentProject?.id) {
     const cardType = cardStore.cardTypes.find(ct => ct.id === typeId)
     assistantStore.recordOperation(projectStore.currentProject.id, {
       type: 'create',
       cardId: (newCard as any).id,
       cardTitle: newCard.title,
       cardType: cardType?.name || 'Unknown'
     })
   }
   
   return
 }
 
 try {
   // Handle free card copy
   const freeCardId = e.dataTransfer?.getData('application/x-free-card-id')
   if (freeCardId) {
     if (nodeData?.__isGroup) return
     await copyCard(Number(freeCardId), { target_project_id: projectStore.currentProject!.id, parent_id: Number(nodeData?.id) })
     await cardStore.fetchCards(projectStore.currentProject!.id)
     ElMessage.success('Copied free card to this node')
     return
   }
 } catch (err) {
   console.error('External drag failed:', err)
 }
}

 // --- Methods ---

function handleNodeClick(data: any) {
  if (data.__isGroup) return
  // Chapter content now also opens in center editor
  cardStore.setActiveCard(data.id)
  assistantSelectionCleared.value = false
  activeTab.value = 'editor'
  try {
    const pid = projectStore.currentProject?.id as number
    const pname = projectStore.currentProject?.name || ''
    const full = (cards.value || []).find((c:any) => c.id === data.id)
    const title = (full?.title || data.title || '') as string
    const content = (full?.content || (data as any).content || {})
    if (pid && data?.id) {
      // Append auto ref only
      assistantStore.addAutoRef({ projectId: pid, projectName: pname, cardId: data.id, cardTitle: title, content })
    }
  } catch {}
}

watch(activeCard, (c) => {
 try {
   if (!c) return
   const pid = projectStore.currentProject?.id as number
   const pname = projectStore.currentProject?.name || ''
   assistantStore.addAutoRef({ projectId: pid, projectName: pname, cardId: (c as any).id, cardTitle: (c as any).title || '', content: (c as any).content || {} })
   
   // Update card context
   console.log('🔄 [Editor] Update card context:', { card_id: (c as any).id, title: (c as any).title, pid })
   assistantStore.updateActiveCard(c as any, pid)
   
   // Update project structure
   updateProjectStructureContext((c as any)?.id)
 } catch (err) {
   console.error('🔄 [Editor] Update card context failed:', err)
 }
})

// Listen project switch, init context and history
watch(() => projectStore.currentProject, (newProject) => {
  if (!newProject?.id) return
  
  try {
    console.log('📦 [Editor] Project switch, init assistant context:', newProject.name)
    
    // Load history
    assistantStore.loadOperations(newProject.id)
    
    // Update card types
    assistantStore.updateProjectCardTypes(cardStore.cardTypes.map(ct => ct.name))
    
    // Build project structure
    updateProjectStructureContext(activeCard.value?.id)
  } catch (err) {
    console.error('📦 [Editor] Init assistant context failed:', err)
  }
}, { immediate: true })

// Listen card count change, auto update structure
watch(() => cards.value.length, () => {
  try {
    updateProjectStructureContext(activeCard.value?.id)
  } catch (err) {
    console.error('🔄 [Editor] Update project structure failed:', err)
  }
})

// Unified update project structure function
function updateProjectStructureContext(currentCardId?: number) {
  const project = projectStore.currentProject
  if (!project?.id) return
  
  assistantStore.updateProjectStructure(
    project.id,
    project.name,
    cards.value,
    cardStore.cardTypes,
    currentCardId
  )
}

function onNodeExpand(_: any, node: any) {
  editorStore.addExpandedKey(String(node.key))
}

function onNodeCollapse(_: any, node: any) {
  editorStore.removeExpandedKey(String(node.key))
}

function handleEditCard(cardId: number) {
  cardStore.setActiveCard(cardId);
  activeTab.value = 'editor';
}

async function handleCreateCard() {
  if (!newCardForm.title || !newCardForm.card_type_id) {
    ElMessage.warning('Please fill in card title and type');
    return;
  }
  const payload: any = {
    ...newCardForm,
    parent_id: (newCardForm as any).parent_id === '' ? undefined : (newCardForm as any).parent_id
  }
  const newCard = await cardStore.addCard(payload as CardCreate);
  
  // Record create
  if (newCard && projectStore.currentProject?.id) {
    const cardType = cardStore.cardTypes.find(ct => ct.id === newCardForm.card_type_id)
    assistantStore.recordOperation(projectStore.currentProject.id, {
      type: 'create',
      cardId: (newCard as any).id,
      cardTitle: newCard.title,
      cardType: cardType?.name || 'Unknown'
    })
  }
  
  isCreateCardDialogVisible.value = false;
  // Reset form
  Object.assign(newCardForm, { title: '', card_type_id: undefined, parent_id: '' as any });
}

// Return icon based on card type
function getIconByCardType(typeName?: string) {
  switch (typeName) {
    case 'Tags':
      return CollectionTag
    case 'SpecialAbility':
      return MagicStick
    case 'OneSentenceSummary':
      return ChatLineRound
    case 'StoryOutline':
      return List
    case 'WorldSetting':
      return Connection
    case 'CoreBlueprint':
      return Tickets
    case 'VolumeOutline':
      return Notebook
    case 'ChapterOutline':
      return Document
    case 'CharacterCard':
      return User
    case 'SceneCard':
      return OfficeBuilding
    default:
      return Document // Default icon
  }
}

// Context Menu Command
function handleContextCommand(command: string, data: any) {
  if (command === 'create-child') {
    openCreateChild(data.id)
  } else if (command === 'delete') {
    deleteNode(data.id, data.title)
  } else if (command === 'delete-group') {
    deleteGroupNodes(data)
  } else if (command === 'edit-structure') {
     if (!data?.id || data.__isGroup) return
     openCardSchemaStudio(data)
  } else if (command === 'rename') {
    if (!data?.id || data.__isGroup) return
    renameCard(data.id, data.title || '')
  } else if (command === 'add-as-reference') {
    try {
      if (!data?.id || data.__isGroup) return
      const pid = projectStore.currentProject?.id as number
      const pname = projectStore.currentProject?.name || ''
      const full = (cards.value || []).find((c:any) => c.id === data.id)
      const title = (full?.title || data.title || '') as string
      const content = (full?.content || (data as any).content || {})
      assistantStore.addInjectedRefDirect({ projectId: pid, projectName: pname, cardId: data.id, cardTitle: title, content }, 'manual')
      ElMessage.success('Added as reference')
    } catch {}
  }
}

function openCardSchemaStudio(card: any) {
  schemaStudio.value = { visible: true, cardId: card.id, cardTitle: card.title || '' }
}

const schemaStudio = ref<{ visible: boolean; cardId: number; cardTitle: string }>({ visible: false, cardId: 0, cardTitle: '' })

async function onCardSchemaSaved() {
  try {
    await cardStore.fetchCards(projectStore.currentProject?.id as number)
  } catch {}
}

// Open "New Card" dialog and prefill parent ID
function openCreateChild(parentId: number) {
  newCardForm.title = ''
  newCardForm.card_type_id = undefined
  newCardForm.parent_id = parentId as any
  isCreateCardDialogVisible.value = true
}

function openCreateRoot() {
  newCardForm.title = ''
  newCardForm.card_type_id = undefined
  newCardForm.parent_id = '' as any
  isCreateCardDialogVisible.value = true
  blankMenuVisible.value = false
}

// Blank area context menu
function onSidebarContextMenu(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.closest('.custom-tree-node')) return
  blankMenuX.value = e.clientX
  blankMenuY.value = e.clientY
  blankMenuVisible.value = true
}

// Delete Card (Confirm)
async function deleteNode(cardId: number, title: string) {
  try {
    await ElMessageBox.confirm(`Confirm delete card "${title}"? This action cannot be undone`, 'Delete Confirmation', { type: 'warning' })
    
    // Record card info before delete
    const card = cards.value.find(c => (c as any).id === cardId)
    const cardType = card ? ((card as any).card_type?.name || 'Unknown') : 'Unknown'
    
    await cardStore.removeCard(cardId)
    
    // Record delete operation
    if (projectStore.currentProject?.id) {
      assistantStore.recordOperation(projectStore.currentProject.id, {
        type: 'delete',
        cardId,
        cardTitle: title,
        cardType
      })
    }
  } catch (e) {
    // User cancel
  }
}

async function deleteGroupNodes(groupData: any) {
  try {
    const title = groupData?.title || groupData?.__groupType || 'this group'
    await ElMessageBox.confirm(`Confirm delete all cards under "${title}"? This action cannot be undone`, 'Delete Confirmation', { type: 'warning' })
    const directChildren: any[] = Array.isArray(groupData?.children) ? groupData.children : []
    const toDeleteOrdered: number[] = []

    // Recursively collect: Leaf first
    function collectDescendantIds(parentId: number) {
      const childIds = (cards.value || []).filter((c: any) => c.parent_id === parentId).map((c: any) => c.id)
      for (const cid of childIds) collectDescendantIds(cid)
      toDeleteOrdered.push(parentId)
    }

    for (const child of directChildren) {
      collectDescendantIds(child.id)
    }

    // Dedup
    const seen = new Set<number>()
    for (const id of toDeleteOrdered) {
      if (seen.has(id)) continue
      seen.add(id)
      await cardStore.removeCard(id)
    }
  } catch (e) {
    // User cancel
  }
}

// Rename function
async function renameCard(cardId: number, oldTitle: string) {
  try {
    const { value } = await ElMessageBox.prompt('Rename takes effect immediately, please enter new name:', 'Rename', {
      confirmButtonText: 'Confirm',
      cancelButtonText: 'Cancel',
      inputValue: oldTitle,
      inputPlaceholder: 'Please enter card title',
      inputValidator: (v:string) => v.trim().length > 0 || 'Title cannot be empty'
    })
    const newTitle = String(value).trim()
    if (newTitle === oldTitle) return
    await cardStore.modifyCard(cardId, { title: newTitle })
    ElMessage.success('Renamed')
  } catch {
    // User cancel or fail
  }
}

// Assistant Panel Context
const assistantResolvedContext = ref<string>('')
const assistantEffectiveSchema = ref<any>(null)
const assistantSelectionCleared = ref<boolean>(false)
const assistantParams = ref<{ llm_config_id: number | null; prompt_name: string | null; temperature: number | null; max_tokens: number | null; timeout: number | null }>({ llm_config_id: null, prompt_name: 'Chat', temperature: null, max_tokens: null, timeout: null })

// Check if current card is Chapter Body
const isChapterContent = computed(() => {
  return activeCard.value?.card_type?.name === 'Chapter'
})

// Chapter Info Extraction
const chapterVolumeNumber = computed(() => {
  if (!isChapterContent.value) return null
  const content: any = activeCard.value?.content || {}
  return content.volume_number ?? null
})

const chapterChapterNumber = computed(() => {
  if (!isChapterContent.value) return null
  const content: any = activeCard.value?.content || {}
  return content.chapter_number ?? null
})

const chapterParticipants = computed(() => {
  if (!isChapterContent.value) return []
  const content: any = activeCard.value?.content || {}
  const list = content.entity_list || []
  if (Array.isArray(list)) {
    return list.map((x: any) => typeof x === 'string' ? x : (x?.name || '')).filter(Boolean).slice(0, 6)
  }
  return []
})

// Auto assemble chapter context
watch(isChapterContent, async (val) => {
  if (val && activeCard.value) {
    await assembleChapterContext()
  }
}, { immediate: true })

async function assembleChapterContext() {
  if (!isChapterContent.value || !projectStore.currentProject?.id) return
  
  try {
    const { assembleContext } = await import('@renderer/api/ai')
    const res = await assembleContext({
      project_id: projectStore.currentProject.id,
      volume_number: chapterVolumeNumber.value ?? undefined,
      chapter_number: chapterChapterNumber.value ?? undefined,
      participants: chapterParticipants.value,
      current_draft_tail: ''
    })
    prefetchedContext.value = res
  } catch (e) {
    console.error('Failed to assemble chapter context:', e)
  }
}


async function refreshAssistantContext() {
  try {
    const card = assistantSelectionCleared.value ? null : (activeCard.value as any)
    if (!card) { assistantResolvedContext.value = ''; assistantEffectiveSchema.value = null; return }
    // Calc context
    const { resolveTemplate } = await import('@renderer/services/contextResolver')
    // Use card's ai_context_template and content
    const resolved = resolveTemplate({ template: card.ai_context_template || '', cards: cards.value, currentCard: card })
    assistantResolvedContext.value = resolved
    // Read effective Schema
    const resp = await getCardSchema(card.id)
    assistantEffectiveSchema.value = resp?.effective_schema || resp?.json_schema || null
    // Read effective AI params
    try {
      const ai = await getCardAIParams(card.id)
      const eff = (ai?.effective_params || {}) as any
      assistantParams.value = {
        llm_config_id: eff.llm_config_id ?? null,
        prompt_name: (eff.prompt_name ?? 'Chat') as any,
        temperature: eff.temperature ?? null,
        max_tokens: eff.max_tokens ?? null,
        timeout: eff.timeout ?? null,
      }
    } catch {
      // Fallback
      const p = (card?.ai_params || {}) as any
      assistantParams.value = {
        llm_config_id: p.llm_config_id ?? null,
        prompt_name: (p.prompt_name ?? 'Chat') as any,
        temperature: p.temperature ?? null,
        max_tokens: p.max_tokens ?? null,
        timeout: p.timeout ?? null,
      }
    }
  } catch { assistantResolvedContext.value = '' }
}

watch(activeCard, () => { if (!assistantSelectionCleared.value) refreshAssistantContext() })

function resetAssistantSelection() {
  assistantSelectionCleared.value = true
  assistantResolvedContext.value = ''
  assistantEffectiveSchema.value = null
}

const assistantFinalize = async (summary: string) => {
  try {
    const card = activeCard.value as any
    if (!card) return
    const evt = new CustomEvent('nf:assistant-finalize', { detail: { cardId: card.id, summary } })
    window.dispatchEvent(evt)
    ElMessage.success('Sent finalized points to editor page')
  } catch {}
}

async function onAssistantFinalize(e: CustomEvent) {
  try {
    const card = activeCard.value as any
    if (!card) return
    const summary: string = (e as any)?.detail?.summary || ''
    const llmId = assistantParams.value.llm_config_id
    const promptName = (assistantParams.value.prompt_name || 'ContentGeneration') as string
    const schema = assistantEffectiveSchema.value
    if (!llmId) { ElMessage.warning('Please select model for this card first'); return }
    if (!schema) { ElMessage.warning('No effective Schema found, cannot finalize'); return }
    // Assemble finalize input
    const ctx = (assistantResolvedContext.value || '').trim()
    const inputText = [ctx ? `[Context]\n${ctx}` : '', summary ? `[Finalization Points]\n${summary}` : ''].filter(Boolean).join('\n\n')
    const result = await generateAIContent({
      input: { input_text: inputText },
      llm_config_id: llmId as any,
      prompt_name: promptName,
      response_model_schema: schema as any,
      temperature: assistantParams.value.temperature ?? undefined,
      max_tokens: assistantParams.value.max_tokens ?? undefined,
      timeout: assistantParams.value.timeout ?? undefined,
    } as any)
    if (result) {
      await cardStore.modifyCard(card.id, { content: result as any })
      ElMessage.success('Generated and wrote back to card based on points')
    } else {
      ElMessage.error('Finalization generation failed: no return content')
    }
  } catch (err) {
    ElMessage.error('Finalization generation failed')
    console.error(err)
  }
}

// Assistant chips jump to card
async function handleJumpToCard(payload: { projectId: number; cardId: number }) {
  try {
    const curPid = projectStore.currentProject?.id
    if (curPid !== payload.projectId) {
      // Switch project
      const all = await getProjects()
      const target = (all || []).find(p => p.id === payload.projectId)
      if (target) {
        projectStore.setCurrentProject(target as any)
        await cardStore.fetchCards(target.id!)
      }
    }
    // Activate target card
    cardStore.setActiveCard(payload.cardId)
    activeTab.value = 'editor'
  } catch {}
}

// ... (Lifecycle and other functions same) ...
</script>

<style scoped>
/* Let right click trigger fill whole row */
.full-row-dropdown { display: block; width: 100%; }
.blank-menu-ref { pointer-events: none; }

.editor-layout {
  display: flex;
  height: 100%;
  width: 100%;
  position: relative;
  background-color: var(--el-fill-color-lighter); /* Dark mode adapt */
}

.sidebar {
  display: flex;
  flex-direction: column;
  background-color: var(--el-fill-color-lighter); /* Dark mode adapt */
  transition: width 0.2s;
  flex-shrink: 0;
  overflow: hidden;
  border-right: none; /* Remove border */
}

.card-navigation-sidebar {
  padding: 8px;
}

/* Top header removed, hide to remove gap */
.sidebar-header { display: none; }

.sidebar-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.card-tree {
  background-color: transparent;
  flex-grow: 1;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  font-size: 14px;
  padding-right: 8px;
}
.card-icon {
  color: var(--el-text-color-secondary);
}
.child-count {
  margin-left: auto;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.resizer {
  width: 5px;
  background: transparent;
  cursor: col-resize;
  z-index: 10;
  user-select: none;
  position: relative;
  transition: background-color 0.2s;
}
.resizer:hover {
  background: var(--el-color-primary-light-7);
}

.main-content {
  padding: 16px 8px; /* Margin */
  display: flex;
  flex-direction: column;
  background-color: transparent; /* Transparent bg */
}

.main-tabs {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color); /* Dark mode adapt */
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08); /* Slight shadow */
  border-radius: 8px; /* Radius */
  overflow: hidden; /* Ensure content not overflow */
  border: none; /* Remove default border */
}

:deep(.el-tabs__content) {
  flex-grow: 1;
  overflow-y: auto;
}
:deep(.el-tab-pane) {
  height: 100%;
}

.custom-tree-node.full-row { 
  display: flex;
  align-items: center;
  width: 100%;
  padding: 3px 6px;
}
.custom-tree-node.full-row .label {
  flex: 1;
}


.types-pane { display: flex; flex-direction: column; border-bottom: 1px solid var(--el-border-color-light); background: var(--el-fill-color-lighter); padding: 6px; box-shadow: 0 2px 6px -2px var(--el-box-shadow-lighter); border-radius: 6px; }
.pane-title { font-size: 12px; color: var(--el-text-color-regular); font-weight: 600; padding: 2px 4px 6px 4px; }
.types-scroll { flex: 1; background: var(--el-fill-color-lighter); }
.types-list { list-style: none; padding: 0; margin: 0; }
.type-item { padding: 6px 8px; cursor: grab; display: flex; align-items: center; color: var(--el-text-color-primary); font-size: 13px; border-radius: 4px; }
.type-item:hover { background: var(--el-fill-color-light); color: var(--el-color-primary); }
.type-name { flex: 1; }

.inner-resizer { height: 6px; cursor: row-resize; background: var(--el-fill-color-light); border-top: 1px solid var(--el-border-color-light); border-bottom: 1px solid var(--el-border-color-light); transition: height .12s ease, background-color .12s ease, border-color .12s ease; }
.inner-resizer:hover { height: 8px; background: var(--el-fill-color); border-top: 1px solid var(--el-border-color); border-bottom: 1px solid var(--el-border-color); }
/* Lower pane: Title sticky and scroll container */
.cards-pane { position: relative; padding-top: 8px; overflow: auto; }
.cards-title { position: sticky; top: 0; z-index: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 6px; font-size: 13px; font-weight: 600; color: var(--el-text-color-regular); padding: 6px 6px; background: var(--el-bg-color); border-bottom: 1px dashed var(--el-border-color-light); margin-bottom: 6px; }
.cards-title-text { width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cards-title-actions { display: flex; align-items: center; gap: 6px; }
.assistant-sidebar { 
  border-left: none; 
  background: transparent; 
  flex-shrink: 0; 
  padding: 16px 8px 16px 0; /* Right margin */
}
.right-resizer { cursor: col-resize; width: 5px; background: transparent; }
.right-resizer:hover { background: var(--el-color-primary-light-7); }
.nf-import-dialog :deep(.el-input__wrapper) { font-size: 14px; }
.nf-import-dialog :deep(.el-input__inner) { font-size: 14px; }
.nf-import-dialog :deep(.el-table .cell) { font-size: 14px; color: var(--el-text-color-primary); }
.nf-import-dialog :deep(.el-table__row) { height: 40px; }
.nf-tree-select-popper { min-width: 320px; }
.nf-tree-select-popper { background: var(--el-bg-color-overlay, #fff); color: var(--el-text-color-primary); }
.nf-tree-select-popper :deep(.el-select-dropdown__item) { color: var(--el-text-color-primary); }
.nf-tree-select-popper :deep(.el-tree) { background: transparent; }
.nf-tree-select-popper :deep(.el-tree-node__content) { background: transparent; }
.nf-tree-select-popper :deep(.el-tree-node__label) { font-size: 14px; color: var(--el-text-color-primary); }
.nf-tree-select-popper :deep(.is-current > .el-tree-node__content),
.nf-tree-select-popper :deep(.el-tree-node__content:hover) { background: var(--el-fill-color-light); }

/* Right Tab Style */
.right-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
.right-tabs :deep(.el-tabs__header) {
  margin: 0;
  border-bottom: 1px solid var(--el-border-color-light);
  padding: 12px 12px 0 12px;
  background: var(--el-fill-color-lighter);
}
.right-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0;
}
.right-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  font-weight: 500;
  padding: 0 16px;
  height: 36px;
  line-height: 36px;
}
.right-tabs :deep(.el-tabs__item.is-active) {
  color: var(--el-color-primary);
}
.right-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
}
.right-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow-y: auto;
}
</style>
