<script setup lang="ts">
import { onMounted, ref, watch, nextTick, computed } from 'vue'
import WorkflowCanvas from '@renderer/components/workflow/WorkflowCanvas.vue'
import WorkflowParamPanel from '@renderer/components/workflow/WorkflowParamPanel.vue'
import { useVueFlow } from '@vue-flow/core'
import { listWorkflows, getWorkflow, updateWorkflow, validateWorkflow, listWorkflowTriggers, createWorkflowTrigger, updateWorkflowTrigger, deleteWorkflowTrigger, type WorkflowTriggerRead, createWorkflow, deleteWorkflow } from '@renderer/api/workflows'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Edit, Delete as DeleteIcon, ArrowDown, ArrowUp, Document, Setting } from '@element-plus/icons-vue'
import { getCardTypes, type CardTypeRead } from '@renderer/api/cards'

onMounted(() => { document.title = 'Workflow Studio - Novel Forge' })
// Node toolbar: Unified delete response
if (typeof window !== 'undefined') {
  window.addEventListener('wf-node-delete', (e: any) => {
    const id = e?.detail?.id
    if (!id) return
    try {
      const list: any[] = Array.isArray(dsl.value.nodes) ? dsl.value.nodes : []
      const idx = list.findIndex((n: any, i: number) => (n.id || `n${i}`) === id)
      if (idx < 0) return
      const next = list.slice(); next.splice(idx,1)
      dsl.value = { ...(dsl.value || {}), nodes: next }
    } catch {}
  })
}

const workflows = ref<any[]>([])
const selectedId = ref<number | null>(null)
const dsl = ref<any>({ nodes: [] })
const errors = ref<string[]>([])
const selectedNode = ref<any | null>(null)
const cardTypes = ref<CardTypeRead[]>([])
const previewTypeName = ref<string>('')
const triggers = ref<WorkflowTriggerRead[]>([])
const triggerDialogVisible = ref(false)
const editingTrigger = ref<Partial<WorkflowTriggerRead & { is_new?: boolean }>>({})
const paramWidth = ref<number>(320)
let resizing = false
let startX = 0
let startW = 320
const ctxMenu = ref<{ visible: boolean; x: number; y: number }>({ visible: false, x: 0, y: 0 })
const jsonPanelCollapsed = ref(true) // JSON panel collapse state
const jsonPanelHeight = ref(200) // JSON panel height

function onNodeContext(e: any) {
  try {
    selectedNode.value = e?.node || selectedNode.value
    const ev: MouseEvent | undefined = e?.event
    ctxMenu.value = { visible: true, x: Number(ev?.clientX || 0), y: Number(ev?.clientY || 0) }
    ;(e?.event || e)?.preventDefault?.()
  } catch {}
}

function toggleJsonPanel() {
  jsonPanelCollapsed.value = !jsonPanelCollapsed.value
}

// Beautify JSON display
const formattedDsl = computed(() => {
  try {
    return JSON.stringify(dsl.value, null, 2)
  } catch {
    return JSON.stringify(dsl.value)
  }
})

async function loadList() {
  workflows.value = await listWorkflows()
  if (!selectedId.value && workflows.value.length) select(workflows.value[0].id)
}

async function select(id: number) {
  selectedId.value = id
  const wf = await getWorkflow(id)
  dsl.value = wf.definition_json || { name: wf.name, dsl_version: 1, nodes: [] }
  errors.value = []
  try {
    triggers.value = (await listWorkflowTriggers()).filter(t => t.workflow_id === id)
  } catch {}

  // If first node is Card.Read and type_name not set, fill with preview type (or default "WorldSetting") for field parsing
  try {
    const nodes: any[] = Array.isArray(dsl.value.nodes) ? dsl.value.nodes : []
    const firstRead = nodes.find(n => n?.type === 'Card.Read')
    const typeFromDsl = firstRead?.params?.type_name
    const typeFromTrigger = (triggers.value.find(t => !!t.card_type_name)?.card_type_name) as string | undefined
    const smart = (wf.name || '').includes('WorldSetting') ? 'WorldSetting' : undefined
    const decided = typeFromDsl || typeFromTrigger || smart || ''
    if (firstRead) {
      firstRead.params = { ...(firstRead.params || {}), type_name: (firstRead.params?.type_name || decided) }
    }
    if (decided) previewTypeName.value = decided
  } catch {}
}

function setFirstReadTypeName(typeName: string) {
  try {
    const nodes: any[] = Array.isArray(dsl.value.nodes) ? dsl.value.nodes : []
    const firstRead = nodes.find(n => n?.type === 'Card.Read')
    if (firstRead) firstRead.params = { ...(firstRead.params || {}), type_name: typeName }
  } catch {}
}

watch(previewTypeName, (v) => {
  if (v) setFirstReadTypeName(v)
})

async function save() {
  const wid = Number(selectedId.value)
  if (!Number.isFinite(wid)) return
  try {
    await updateWorkflow(wid, { definition_json: dsl.value })
    // Reload to confirm backend persistence
    const wf = await getWorkflow(wid)
    dsl.value = wf.definition_json || dsl.value
    ElMessage.success('Saved')
  } catch (e:any) {
    ElMessage.error('Save failed')
    console.error(e)
  }
}

const createDialogVisible = ref(false)
const newWorkflowName = ref('')
async function createNew() {
  newWorkflowName.value = ''
  createDialogVisible.value = true
}
async function confirmCreate() {
  const name = (newWorkflowName.value || '').trim()
  if (!name) { createDialogVisible.value = false; return }
  const wf = await createWorkflow({ name, definition_json: { dsl_version: 1, name, nodes: [] }, is_active: true })
  await loadList()
  if (wf?.id) await select(wf.id)
  createDialogVisible.value = false
}

async function removeSelected() {
  const wid = Number(selectedId.value)
  if (!Number.isFinite(wid)) return
  try {
    await ElMessageBox.confirm('Confirm delete this workflow? This action cannot be undone', 'Delete Confirmation', { confirmButtonText: 'Delete', cancelButtonText: 'Cancel', type: 'warning' })
  } catch { return }
  await deleteWorkflow(wid)
  selectedId.value = null
  dsl.value = { nodes: [] }
  await loadList()
  ElMessage.success('Deleted')
}

async function validateNow() {
  const wid = Number(selectedId.value)
  if (!Number.isFinite(wid)) return
  const v = await validateWorkflow(wid)
  errors.value = v.errors || []
}

loadList()
getCardTypes().then(v => { cardTypes.value = v }).catch(() => {})

function onNodeSelected(node: any) {
  selectedNode.value = node || null
}

function updateParams(next: any) {
  // Write back params from right panel to DSL (support top-level and body recursion)
  if (!selectedNode.value) return
  const id = String(selectedNode.value.id || '')
  // no-op debug log removed

  function applyPatch(list: any[]): boolean {
    for (let i = 0; i < list.length; i++) {
      const n = list[i]
      const nid = String(n?.id || `n${i}`)
      if (nid === id) {
        const before = JSON.parse(JSON.stringify(n.params || {}))
        n.params = { ...(n.params || {}), ...next }
        // no-op debug log removed
        if (selectedNode.value?.data) selectedNode.value.data.params = n.params
        return true
      }
      if (Array.isArray(n?.body)) {
        // Child nodes match by own id, not id constructed during render
        for (let k = 0; k < n.body.length; k++) {
          const bn = n.body[k]
          const bid = String(bn?.id || `${n.id || `n${i}`}-b${k}`)
          if (bid === id) {
            const beforeB = JSON.parse(JSON.stringify(bn.params || {}))
            bn.params = { ...(bn.params || {}), ...next }
            // no-op debug log removed
            if (selectedNode.value?.data) selectedNode.value.data.params = bn.params
            return true
          }
          if (Array.isArray(bn?.body) && applyPatch([bn])) return true
        }
      }
    }
    return false
  }

  const root = Array.isArray(dsl.value?.nodes) ? dsl.value.nodes : []
  if (!applyPatch(root)) return
  dsl.value = { ...(dsl.value || {}), nodes: JSON.parse(JSON.stringify(root)) }
}

function startResize(e: MouseEvent) {
  resizing = true
  startX = e.clientX
  startW = paramWidth.value
  const onMove = (ev: MouseEvent) => {
    if (!resizing) return
    const dx = ev.clientX - startX
    // Panel on right, drag left edge: drag left increases width, drag right decreases
    let w = startW - dx
    if (w < 260) w = 260
    if (w > 560) w = 560
    paramWidth.value = w
  }
  const onUp = () => {
    resizing = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function insertNode(spec: any) {
  try {
    // Ensure DSL is standard format
    if (!Array.isArray(dsl.value.edges)) {
      convertDslToStandardFormat()
    }
    
    const nodes: any[] = Array.isArray(dsl.value.nodes) ? dsl.value.nodes : []
    const edges: any[] = Array.isArray(dsl.value.edges) ? dsl.value.edges : []
    
    const nodeId = `n${Date.now()}`
    
    // Use passed exact position or default
    const position = spec.position || {
      x: 40 + nodes.length * 240,
      y: 80
    }
    
    const newNode: any = { 
      id: nodeId, 
      type: spec.type || spec.newNodeType, 
      params: spec.params || {},
      position
    }
    
    // Simply add node, no auto connection or child node
    nodes.push(newNode)
    
    dsl.value = { ...(dsl.value || {}), nodes, edges }
    pendingInsertIndex.value = null
    pendingBelowOf = null
    
    // Select newly created node
    nextTick(() => {
      selectedNode.value = { id: nodeId, type: newNode.type, params: newNode.params }
    })
  } catch (err) {
    console.warn('Insert node failed:', err)
  }
}

// Convert DSL to standard format
function convertDslToStandardFormat() {
  if (Array.isArray(dsl.value.edges)) return // Already standard format
  
  const nodes: any[] = Array.isArray(dsl.value.nodes) ? dsl.value.nodes : []
  const edges: any[] = []
  
  // Add position info and generate edges for existing nodes
  nodes.forEach((node: any, index: number) => {
    if (!node.position) {
      node.position = { x: 40 + index * 240, y: 80 }
    }
    
    // Generate edges for adjacent nodes (simplified)
    if (index > 0) {
      edges.push({
        id: `e-${nodes[index-1].id}-${node.id}`,
        source: nodes[index-1].id,
        target: node.id,
        sourceHandle: 'r',
        targetHandle: 'l'
      })
    }
  })
  
  dsl.value = { ...dsl.value, edges }
}

const pendingInsertIndex = ref<number | null>(null)
let pendingBelowOf: string | null = null

function handleRequestInsert(payload: any) {
  openNodeLibAt(payload)
}

function getTriggerLabel(triggerOn: string) {
  const labels: Record<string, string> = {
    'onsave': 'Trigger on Save',
    'ongenfinish': 'Trigger on Gen Finish',
    'manual': 'Manual Trigger',
    'onprojectcreate': 'Trigger on Project Create'
  }
  return labels[triggerOn] || triggerOn
}

function openNodeLibAt(payload: any) {
  if (payload?.newNodeType) {
    // Drag create: Use passed position
    insertNode({ 
      type: payload.newNodeType,
      position: payload.position
    })
  } else {
    // Right click create: Use index to calc position
    const index = Math.max(0, Math.min(Number(payload?.index ?? (dsl.value?.nodes || []).length), (dsl.value?.nodes || []).length))
    pendingInsertIndex.value = index
    pendingBelowOf = payload?.placement === 'below' ? String(payload?.anchorId || '') : null
  }
}

function openCreateTrigger() {
  if (!selectedId.value) return
  editingTrigger.value = { workflow_id: Number(selectedId.value), trigger_on: 'onsave', card_type_name: '', is_active: true, is_new: true }
  triggerDialogVisible.value = true
}

async function saveTrigger() {
  const t = editingTrigger.value
  if (!t) return
  if ((t as any).is_new) {
    const created = await createWorkflowTrigger({ workflow_id: Number(selectedId.value), trigger_on: String(t.trigger_on || 'onsave'), card_type_name: (t.card_type_name || undefined), is_active: t.is_active !== false })
    triggers.value = [...triggers.value, created]
  } else if (t.id) {
    const updated = await updateWorkflowTrigger(Number(t.id), { trigger_on: t.trigger_on, card_type_name: t.card_type_name, is_active: t.is_active })
    const i = triggers.value.findIndex(x => x.id === updated.id)
    if (i >= 0) triggers.value[i] = updated
  }
  triggerDialogVisible.value = false
}

async function removeTrigger(id: number) {
  await deleteWorkflowTrigger(id)
  triggers.value = triggers.value.filter(t => t.id !== id)
}

function deleteSelectedNode() {
  try {
    if (!selectedNode.value) return
    const id = selectedNode.value.id as string
    const list: any[] = Array.isArray(dsl.value.nodes) ? dsl.value.nodes : []
    const idx = list.findIndex((n: any, i: number) => (n.id || `n${i}`) === id)
    if (idx < 0) return
    const next = list.slice()
    next.splice(idx, 1)
    dsl.value = { ...(dsl.value || {}), nodes: next }
    selectedNode.value = null
    ctxMenu.value.visible = false
  } catch {}
}
</script>

<template>
  <div class="workflow-studio">
    <!-- Header -->
    <div class="studio-header">
      <div class="header-left">
        <div class="title">
          <el-icon><Setting /></el-icon>
          <h2>Workflow Studio</h2>
        </div>
        <div class="subtitle">Visually edit and manage workflows</div>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Document" @click="save" :disabled="!selectedId">Save Workflow</el-button>
        <el-button @click="createNew">New Workflow</el-button>
      </div>
    </div>

    <div class="studio-layout">
      <!-- Left Sidebar -->
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>Workflow List</h3>
          <el-tag size="small" type="info">{{ workflows.length }}</el-tag>
        </div>
        <el-scrollbar class="workflow-list">
          <div 
            v-for="w in workflows" 
            :key="w.id"
            class="workflow-item" 
            :class="{ active: selectedId === w.id }"
            @click="select(w.id)"
          >
            <div class="workflow-main">
              <div class="workflow-name">{{ w.name }}</div>
              <div class="workflow-badges">
                <el-tag v-if="w.is_built_in" size="small" type="primary">Built-in</el-tag>
                <el-tag size="small" effect="plain">v{{ w.version }}</el-tag>
              </div>
            </div>
            <div class="workflow-meta">
              <span class="dsl-version">DSL {{ w.dsl_version }}</span>
              <el-icon v-if="selectedId === w.id" class="selected-icon" color="#409EFF"><ArrowDown /></el-icon>
            </div>
          </div>
        </el-scrollbar>
      </div>

      <!-- Main Content -->
      <div class="main-content">
        <!-- Toolbar -->
        <div class="content-toolbar">
          <div class="toolbar-section">
            <el-button-group>
              <el-button @click="validateNow" :disabled="!selectedId">Validate</el-button>
              <el-button type="danger" @click="removeSelected" :disabled="!selectedId">Delete</el-button>
            </el-button-group>
            <el-alert 
              v-if="errors.length" 
              :title="`Found ${errors.length} errors`"
              type="error" 
              size="small"
              show-icon
              :closable="false"
            />
          </div>
          
          <div class="toolbar-section">
            <div class="config-group">
              <span class="config-label">Preview Card Type</span>
              <el-select v-model="previewTypeName" size="small" placeholder="Select Type" style="width: 180px">
                <el-option v-for="t in cardTypes" :key="t.id" :label="t.name" :value="t.name" />
              </el-select>
            </div>
            
            <div class="config-group">
              <span class="config-label">Triggers</span>
              <div class="triggers-list">
                <el-tag 
                  v-for="tg in triggers" 
                  :key="tg.id" 
                  closable
                  @close="removeTrigger(tg.id)"
                  @click="editingTrigger={...tg};triggerDialogVisible=true"
                  class="trigger-tag"
                >
                  {{ getTriggerLabel(tg.trigger_on) }}{{ tg.card_type_name ? `:${tg.card_type_name}` : '' }}
                </el-tag>
                <el-button size="small" type="primary" plain @click="openCreateTrigger">
                  <el-icon><Edit /></el-icon>
                  Add Trigger
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- Canvas and Panel -->
        <div class="workspace">
          <div class="canvas-container">
            <WorkflowCanvas 
              v-model="dsl" 
              @select-node="onNodeSelected" 
              @node-context="onNodeContext"
              @request-insert="handleRequestInsert"
            />
          </div>
          
          <div class="param-container" :style="{ width: paramWidth + 'px' }">
            <div class="param-header">
              <h4>Node Params</h4>
              <span v-if="selectedNode" class="selected-node-type">{{ selectedNode.type || 'Unknown' }}</span>
              <span v-else class="no-selection">No Node Selected</span>
            </div>
            <WorkflowParamPanel 
              class="param-panel" 
              :key="selectedNode?.id || 'none'" 
              :node="selectedNode" 
              :context-type-name="previewTypeName" 
              @update-params="updateParams" 
            />
            <div class="resizer" @mousedown="startResize"></div>
          </div>
        </div>

        <!-- JSON Inspector Panel -->
        <div class="json-inspector" :class="{ collapsed: jsonPanelCollapsed }">
          <div class="json-header" @click="toggleJsonPanel">
            <div class="json-title">
              <el-icon><Document /></el-icon>
              <span>DSL Inspector</span>
            </div>
            <div class="json-actions">
              <el-tag size="small" type="info">{{ Object.keys(dsl.nodes || []).length }} nodes</el-tag>
              <el-icon class="collapse-icon" :class="{ expanded: !jsonPanelCollapsed }">
                <ArrowUp />
              </el-icon>
            </div>
          </div>
          <div v-show="!jsonPanelCollapsed" class="json-content" :style="{ height: jsonPanelHeight + 'px' }">
            <el-scrollbar>
              <pre class="json-code">{{ formattedDsl }}</pre>
            </el-scrollbar>
          </div>
        </div>
      </div>
    </div>

    <!-- Context Menu -->
    <div v-if="ctxMenu.visible" class="ctx" :style="{ left: ctxMenu.x + 'px', top: ctxMenu.y + 'px' }" @click.stop @contextmenu.stop.prevent>
      <el-card shadow="hover" class="ctx-card">
        <div class="ctx-item" @click="deleteSelectedNode">
          <el-icon><DeleteIcon/></el-icon>
          <span>Delete Node</span>
        </div>
      </el-card>
    </div>

    <!-- Trigger Dialog -->
    <el-dialog v-model="triggerDialogVisible" title="Trigger Config" width="450px">
      <el-form label-width="100px" size="default">
        <el-form-item label="Trigger Timing">
          <el-select v-model="(editingTrigger as any).trigger_on" placeholder="Select Trigger Timing">
            <el-option label="Trigger on Save" value="onsave" />
            <el-option label="Trigger on Gen Finish" value="ongenfinish" />
            <el-option label="Manual Trigger" value="manual" />
            <el-option label="Trigger on Project Create" value="onprojectcreate" />
          </el-select>
        </el-form-item>
        <el-form-item 
          label="Card Type"
          v-show="(editingTrigger as any)?.trigger_on !== 'onprojectcreate'"
        >
          <el-input v-model="(editingTrigger as any).card_type_name" placeholder="Empty means all types" />
          <template #append>
            <span style="color: var(--el-text-color-secondary); font-size: 12px;">Optional</span>
          </template>
        </el-form-item>
        <el-form-item label="Enabled">
          <el-switch v-model="(editingTrigger as any).is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="triggerDialogVisible=false">Cancel</el-button>
          <el-button type="primary" @click="saveTrigger">Save Trigger</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Create Workflow Dialog -->
    <el-dialog v-model="createDialogVisible" title="New Workflow" width="450px">
      <el-form label-width="80px" size="default">
        <el-form-item label="Name" required>
          <el-input 
            v-model="newWorkflowName" 
            placeholder="Please enter workflow name"
            @keyup.enter="confirmCreate"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="createDialogVisible=false">Cancel</el-button>
          <el-button type="primary" @click="confirmCreate" :disabled="!newWorkflowName.trim()">
            Create Workflow
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
  
</template>

<style scoped>
/* Main Container */
.workflow-studio {
  height: 100vh;
  background: var(--el-bg-color-page);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header Styles */
.studio-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 32px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.header-left .title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.header-left .title h2 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 24px;
  font-weight: 600;
}

.header-left .title .el-icon {
  font-size: 24px;
  color: var(--el-color-primary);
}

.header-left .subtitle {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin-left: 36px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* Main Layout */
.studio-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 320px 1fr;
  overflow: hidden;
}

/* Sidebar Styles */
.sidebar {
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.workflow-list {
  flex: 1;
  padding: 8px;
}

.workflow-item {
  padding: 16px 20px;
  margin: 4px 0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.workflow-item:hover {
  background: var(--el-fill-color-extra-light);
  border-color: var(--el-border-color-light);
}

.workflow-item.active {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-7);
  box-shadow: 0 2px 8px var(--el-color-primary-light-8);
}

.workflow-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.workflow-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.workflow-badges {
  display: flex;
  gap: 4px;
}

.workflow-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.selected-icon {
  font-size: 12px;
  animation: bounce 1s infinite;
}

/* Main Content */
.main-content {
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color-page);
  overflow: hidden;
}

/* Toolbar */
.content-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-extra-light);
  gap: 24px;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.config-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
  font-weight: 500;
  white-space: nowrap;
}

.triggers-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.trigger-tag {
  cursor: pointer;
  transition: all 0.2s ease;
}

.trigger-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Workspace */
.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1px;
  background: var(--el-border-color-extra-light);
  overflow: hidden;
}

.canvas-container {
  background: var(--el-bg-color);
  position: relative;
  overflow: hidden;
}

.param-container {
  background: var(--el-bg-color);
  display: flex;
  flex-direction: column;
  position: relative;
  min-width: 260px;
  max-width: 560px;
}

.param-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  background: var(--el-fill-color-extra-light);
}

.param-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.selected-node-type {
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  padding: 2px 8px;
  border-radius: 12px;
  font-family: 'Monaco', 'Consolas', monospace;
}

.no-selection {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-style: italic;
}

.param-panel {
  flex: 1;
  overflow: auto;
}

.resizer {
  position: absolute;
  left: -3px;
  top: 0;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  background: transparent;
  transition: background 0.2s ease;
}

.resizer:hover {
  background: var(--el-color-primary-light-7);
}

/* JSON Inspector */
.json-inspector {
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-extra-light);
  transition: all 0.3s ease;
  max-height: 400px;
}

.json-inspector.collapsed {
  max-height: 48px;
}

.json-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  cursor: pointer;
  background: var(--el-fill-color-extra-light);
  transition: background 0.2s ease;
}

.json-header:hover {
  background: var(--el-fill-color-light);
}

.json-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.json-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-icon {
  transition: transform 0.3s ease;
}

.collapse-icon.expanded {
  transform: rotate(180deg);
}

.json-content {
  overflow: hidden;
  border-top: 1px solid var(--el-border-color-extra-light);
}

.json-code {
  margin: 0;
  padding: 20px;
  background: var(--el-fill-color-darker);
  color: var(--el-text-color-primary);
  font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre;
  overflow-wrap: break-word;
}

/* Context Menu */
.ctx {
  position: fixed;
  z-index: 3000;
}

.ctx-card {
  padding: 8px 0;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.2s ease;
  font-size: 13px;
}

.ctx-item:hover {
  background: var(--el-fill-color-light);
}

/* Animations */
@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-3px);
  }
  60% {
    transform: translateY(-1px);
  }
}

/* Dialog Styles */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* Responsive Design */
@media (max-width: 1400px) {
  .studio-layout {
    grid-template-columns: 280px 1fr;
  }
  
  .param-container {
    min-width: 240px;
  }
}

@media (max-width: 1200px) {
  .content-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .toolbar-section {
    justify-content: space-between;
  }
  
  .studio-layout {
    grid-template-columns: 260px 1fr;
  }
}
</style>


