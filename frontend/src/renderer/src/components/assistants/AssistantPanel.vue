<template>
  <div class="assistant-panel">
    <div class="panel-header">
      <div class="header-title-row">
        <div class="title-area">
          <span class="main-title">Inspiration Assistant</span>
          <span class="session-subtitle">{{ currentSession.title }}</span>
        </div>
        <div class="spacer"></div>
        <el-tooltip content="New Chat" placement="bottom">
          <el-button :icon="Plus" size="small" circle @click="createNewSession" />
        </el-tooltip>
        <el-tooltip content="Chat History" placement="bottom">
          <el-button :icon="Clock" size="small" circle @click="historyDrawerVisible = true" />
        </el-tooltip>
      </div>
      <div class="header-controls-row">
        <el-tag v-if="currentCardTitle" size="small" type="info" class="card-tag" effect="plain">{{ currentCardTitle }}</el-tag>
        <div class="spacer"></div>
        <el-button size="small" @click="$emit('refresh-context')">Refresh Context</el-button>
        <el-popover placement="bottom" width="480" trigger="hover">
          <template #reference>
            <el-tag type="info" class="ctx-tag" size="small">Preview</el-tag>
          </template>
          <pre class="ctx-preview">{{ (resolvedContext || '') }}</pre>
        </el-popover>
      </div>
    </div>

    <div class="chat-area">
      <div class="messages" ref="messagesEl">
        <div v-for="(m, idx) in messages" :key="idx" :class="['msg', m.role]">
          <div class="bubble">
            <XMarkdown 
              :markdown="filterMessageContent(m.content)" 
              :default-theme-mode="isDarkMode ? 'dark' : 'light'"
              class="bubble-markdown"
            />
          </div>
          
          <!-- ⏳ Temp "Calling Tools" Display -->
          <div v-if="m.toolsInProgress" class="tools-in-progress">
            <el-icon class="tools-icon spinning"><Loading /></el-icon>
            <pre class="tools-progress-text">{{ m.toolsInProgress }}</pre>
          </div>
          
          <!-- Tool Execution Display -->
          <div v-if="m.tools && m.tools.length" class="tools-summary">
            <div class="tools-header">
              <el-icon class="tools-icon"><Tools /></el-icon>
              <span class="tools-count">Executed {{ m.tools.length }} actions</span>
            </div>
            <el-collapse class="tools-collapse">
              <el-collapse-item>
                <template #title>
                  <span class="tools-expand-label">View Details</span>
                </template>
                <div v-for="(tool, tidx) in m.tools" :key="tidx" class="tool-item">
                  <div class="tool-header">
                    <el-tag size="small" type="success">{{ formatToolName(tool.tool_name) }}</el-tag>
                    <span class="tool-status">{{ tool.result?.success ? '✅ Success' : '❌ Failed' }}</span>
                    <el-link 
                      v-if="tool.result?.card_id" 
                      type="primary" 
                      size="small"
                      @click="emit('jump-to-card', { 
                        projectId: projectStore.currentProject?.id || 0, 
                        cardId: tool.result.card_id 
                      })"
                    >
                      Jump to Card →
                    </el-link>
                  </div>
                  
                  <!-- Tool Detail Info -->
                  <div class="tool-details">
                    <!-- Brief Message -->
                    <div v-if="tool.result?.message" class="tool-message">
                      {{ tool.result.message }}
                    </div>
                    
                    <!-- Key Return Data -->
                    <div v-if="tool.result" class="tool-result-summary">
                      <div v-if="tool.result.card_id" class="result-field">
                        <span class="field-label">Card ID:</span>
                        <span class="field-value">{{ tool.result.card_id }}</span>
                      </div>
                      <div v-if="tool.result.cards_created" class="result-field">
                        <span class="field-label">Created Count:</span>
                        <span class="field-value">{{ tool.result.cards_created.length }} Cards</span>
                      </div>
                      <div v-if="tool.result.data" class="result-field">
                        <span class="field-label">Return Data:</span>
                        <span class="field-value">{{ typeof tool.result.data === 'object' ? JSON.stringify(tool.result.data).substring(0, 100) + '...' : tool.result.data }}</span>
                      </div>
                    </div>
                    
                    <!-- Full JSON (Collapsed) -->
                    <el-collapse class="tool-json-collapse">
                      <el-collapse-item title="View Full Return Data">
                        <pre class="tool-json">{{ JSON.stringify(tool.result, null, 2) }}</pre>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
          
          <div v-if="m.role==='assistant'" class="msg-toolbar">
            <el-button :icon="Refresh" circle size="small" :disabled="isStreaming" @click="handleRegenerateAt(idx)" title="Regenerate" />
            <el-button :icon="DocumentCopy" circle size="small" :disabled="isStreaming || !m.content" @click="handleCopy(idx)" title="Copy Content" />
          </div>
        </div>
      </div>
      <div v-if="isStreaming" class="streaming-tip">Generating…</div>
    </div>

    <div class="composer">
      <div class="inject-toolbar">
        <!-- Citation Cards Display Area -->
        <div class="chips">
          <!-- Tag Display -->
          <div class="chips-tags">
            <el-tag 
              v-for="(r, idx) in visibleRefs" 
              :key="r.projectId + '-' + r.cardId" 
              closable 
              @close="removeInjectedRef(idx)" 
              size="small" 
              effect="plain" 
              class="chip-tag" 
              @click="onChipClick(r)"
            >
              {{ r.projectName }} / {{ r.cardTitle }}
            </el-tag>
          </div>
          
          <!-- More Button -->
          <div v-if="assistantStore.injectedRefs.length > 0" class="chips-more">
            <el-popover
              placement="bottom-start"
              :width="380"
              trigger="click"
            >
              <template #reference>
                <el-button 
                  size="small" 
                  text
                  class="more-refs-btn"
                  :title="`Total ${assistantStore.injectedRefs.length} cited cards`"
                >
                  <span class="more-refs-dots">...</span>
                  <span class="more-refs-count">({{ assistantStore.injectedRefs.length }})</span>
                </el-button>
              </template>
              
              <!-- Popover Content -->
              <div class="more-refs-popover">
                <div class="popover-header">
                  <span>Cited Cards</span>
                  <span class="popover-count">{{ assistantStore.injectedRefs.length }}</span>
                </div>
                <div class="more-refs-list">
                  <div 
                    v-for="(r, idx) in assistantStore.injectedRefs" 
                    :key="r.projectId + '-' + r.cardId"
                    class="more-ref-item"
                  >
                    <span class="ref-info" @click="onChipClick(r)">
                      <el-icon><Document /></el-icon>
                      {{ r.projectName }} / {{ r.cardTitle }}
                    </span>
                    <el-button 
                      :icon="Close" 
                      size="small" 
                      text 
                      @click="removeInjectedRef(idx)"
                      title="Remove Citation"
                    />
                  </div>
                </div>
              </div>
            </el-popover>
          </div>
        </div>
        
        <el-button size="small" :icon="Plus" @click="openInjectSelector" class="add-ref-btn">Add Citation</el-button>
      </div>
      
      <div class="composer-subbar">
        <el-select v-model="overrideLlmId" placeholder="Select Model" size="small" style="width: 200px">
          <el-option v-for="m in llmOptions" :key="m.id" :label="(m.display_name || m.model_name)" :value="m.id" />
        </el-select>
      </div>
      
      <el-input v-model="draft" type="textarea" :rows="4" placeholder="Enter your thoughts, constraints or follow-up questions" :disabled="isStreaming" @keydown="onComposerKeydown" class="composer-input" />
      
      <div class="composer-actions">
        <el-tooltip content="React Mode: Call tools via text format, compatible with more models" placement="top">
          <el-switch 
            v-model="useReactMode" 
            size="small"
            active-text="React"
            style="margin-right: auto"
          />
        </el-tooltip>
        <el-button :disabled="!isStreaming" @click="handleCancel">Stop</el-button>
        <el-button type="primary" :icon="Promotion" circle :disabled="isStreaming || !canSend" @click="handleSend" title="Send" />
      </div>
    </div>

    <!-- Selector Dialog -->
    <el-dialog v-model="selectorVisible" title="Add Citation Card" width="760px">
      <div style="display:flex; gap:12px; align-items:center; margin-bottom:10px;">
        <el-select v-model="selectorSourcePid" placeholder="Source Project" style="width: 260px" @change="onSelectorProjectChange($event as any)">
          <el-option v-for="p in assistantStore.projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-input v-model="selectorSearch" placeholder="Search Title..." clearable style="flex:1" />
      </div>
      <el-tree :data="selectorTreeData" :props="{ label: 'label', children: 'children' }" node-key="key" show-checkbox highlight-current :default-expand-all="false" :check-strictly="false" @check="onTreeCheck" style="max-height:360px; overflow:auto; border:1px solid var(--el-border-color-light); padding:8px; border-radius:6px;" />
      <template #footer>
        <el-button @click="selectorVisible = false">Cancel</el-button>
        <el-button type="primary" :disabled="!selectorSelectedIds.length || !selectorSourcePid" @click="confirmAddInjectedRefs">Add</el-button>
      </template>
    </el-dialog>

    <!-- History Drawer -->
    <el-drawer
      v-model="historyDrawerVisible"
      title="Chat History"
      direction="rtl"
      size="320px"
    >
      <div class="history-drawer-content">
        <div class="history-actions">
          <el-button type="primary" :icon="Plus" @click="createNewSession" style="width: 100%;">
            New Chat
          </el-button>
        </div>

        <el-divider />

        <div v-if="!historySessions.length" class="empty-history">
          <el-empty description="No Chat History" :image-size="80" />
        </div>

        <div v-else class="history-list">
          <div 
            v-for="session in historySessions" 
            :key="session.id"
            :class="['history-item', { 'is-current': session.id === currentSession.id }]"
            @click="loadSession(session.id)"
          >
            <div class="history-item-header">
              <el-icon class="history-icon"><ChatDotRound /></el-icon>
              <span class="history-title">{{ session.title }}</span>
            </div>
            <div class="history-item-footer">
              <span class="history-time">{{ formatSessionTime(session.updatedAt) }}</span>
              <el-button 
                :icon="Delete" 
                size="small" 
                text 
                type="danger"
                @click.stop="handleDeleteSession(session.id)"
              />
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { generateContinuationStreaming, renderPromptWithKnowledge } from '@renderer/api/ai'
import { getProjects } from '@renderer/api/projects'
import { getCardsForProject, type CardRead } from '@renderer/api/cards'
import { listLLMConfigs, type LLMConfigRead } from '@renderer/api/setting'
import { Plus, Promotion, Refresh, DocumentCopy, Tools, Loading, ChatDotRound, ArrowDown, Delete, Clock, Document, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {XMarkdown} from 'vue-element-plus-x'
import { useAssistantStore } from '@renderer/stores/useAssistantStore'
import { useProjectStore } from '@renderer/stores/useProjectStore'
import { useCardStore } from '@renderer/stores/useCardStore'
import { useAppStore } from '@renderer/stores/useAppStore'

const props = defineProps<{ resolvedContext: string; llmConfigId?: number | null; promptName?: string | null; temperature?: number | null; max_tokens?: number | null; timeout?: number | null; effectiveSchema?: any; generationPromptName?: string | null; currentCardTitle?: string | null; currentCardContent?: any }>()
const emit = defineEmits<{ 'finalize': [string]; 'refresh-context': []; 'reset-selection': []; 'jump-to-card': [{ projectId: number; cardId: number }] }>()

const messages = ref<Array<{ 
  role: 'user' | 'assistant'
  content: string
  tools?: Array<{tool_name: string, result: any}>
  toolsInProgress?: string
}>>([])
const draft = ref('')
const isStreaming = ref(false)
let streamCtl: { cancel: () => void } | null = null
const messagesEl = ref<HTMLDivElement | null>(null)

// ===== Session Management =====
interface ChatSession {
  id: string
  projectId: number
  title: string
  createdAt: number
  updatedAt: number
  messages: typeof messages.value
}

const currentSession = ref<ChatSession>({
  id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  projectId: 0,
  title: 'New Chat',
  createdAt: Date.now(),
  updatedAt: Date.now(),
  messages: []
})

const historySessions = ref<ChatSession[]>([])
const historyDrawerVisible = ref(false)

const lastRun = ref<{ prev: string; tail: string; targetIdx: number } | null>(null)
const canRegenerate = computed(() => !isStreaming.value && !!lastRun.value && messages.value[lastRun.value.targetIdx]?.role === 'assistant')
const canRegenerateNow = computed(() => {
  if (isStreaming.value) return false
  const last = messages.value[messages.value.length - 1]
  return !!last && last.role === 'assistant'
})

// Model Selection (Per project)
const llmOptions = ref<LLMConfigRead[]>([])
const overrideLlmId = ref<number | null>(null)
const effectiveLlmId = computed(() => overrideLlmId.value || (props.llmConfigId as any) || null)
const MODEL_KEY_PREFIX = 'nf:assistant:model:'
function modelKeyForProject(pid: number) { return `${MODEL_KEY_PREFIX}${pid}` }

// ReAct Mode Switch (Per project)
const useReactMode = ref(false)
const REACT_MODE_KEY_PREFIX = 'nf:assistant:react:'
function reactModeKeyForProject(pid: number) { return `${REACT_MODE_KEY_PREFIX}${pid}` }

// Cited Cards Display Control
const MAX_VISIBLE_REFS = 5  // Max 5 visible

const visibleRefs = computed(() => {
  return assistantStore.injectedRefs.slice(0, MAX_VISIBLE_REFS)
})

const hiddenRefsCount = computed(() => {
  const total = assistantStore.injectedRefs.length
  return total > MAX_VISIBLE_REFS ? total - MAX_VISIBLE_REFS : 0
})

watch(overrideLlmId, (val) => {
  try { const pid = projectStore.currentProject?.id; if (pid && val) localStorage.setItem(modelKeyForProject(pid), String(val)) } catch {}
})

watch(useReactMode, (val) => {
  try { const pid = projectStore.currentProject?.id; if (pid) localStorage.setItem(reactModeKeyForProject(pid), String(val)) } catch {}
})

const injectedCardPrompt = ref<string>('')
async function loadInjectedCardPrompt() {
  try {
    const name = props.generationPromptName || ''
    if (!name) { injectedCardPrompt.value = ''; return }
    const resp = await renderPromptWithKnowledge(name)
    injectedCardPrompt.value = resp?.text || ''
  } catch { injectedCardPrompt.value = '' }
}

watch(() => props.generationPromptName, async () => { await loadInjectedCardPrompt() }, { immediate: true })

const canSend = computed(() => {
  const hasDraft = !!draft.value.trim()
  const hasRefs = assistantStore.injectedRefs.length > 0
  return !!effectiveLlmId.value && (hasDraft || hasRefs)
})

// ---- Multi-card Reference (Cross-project, using Pinia) ----
const assistantStore = useAssistantStore()
const projectStore = useProjectStore()
const appStore = useAppStore()
const { isDarkMode } = storeToRefs(appStore)
const selectorVisible = ref(false)
const selectorSourcePid = ref<number | null>(null)
const selectorCards = ref<CardRead[]>([])
const selectorSearch = ref('')
const selectorSelectedIds = ref<number[]>([])
const filteredSelectorCards = computed(() => {
  const q = (selectorSearch.value || '').trim().toLowerCase()
  if (!q) return selectorCards.value
  return (selectorCards.value || []).filter(c => (c.title || '').toLowerCase().includes(q))
})
const selectorTreeData = computed(() => {
  const byType: Record<string, any[]> = {}
  for (const c of filteredSelectorCards.value || []) {
    const tn = c.card_type?.name || 'Uncategorized'
    if (!byType[tn]) byType[tn] = []
    byType[tn].push({ id: c.id, title: c.title, label: c.title, key: `card:${c.id}`, isLeaf: true })
  }
  return Object.keys(byType).sort().map((t, idx) => ({ key: `type:${idx}`, label: t, children: byType[t] }))
})
const selectorCheckedKeys = ref<string[]>([])

async function openInjectSelector() {
  try {
    await assistantStore.loadProjects()
    const currentPid = projectStore.currentProject?.id || null
    selectorSourcePid.value = currentPid ?? (assistantStore.projects[0]?.id ?? null)
    if (selectorSourcePid.value) selectorCards.value = await assistantStore.loadCardsForProject(selectorSourcePid.value)
    selectorSelectedIds.value = []
    selectorSearch.value = ''
    selectorVisible.value = true
  } catch {}
}

async function onSelectorProjectChange(pid: number | null) {
  selectorCards.value = []
  if (!pid) return
  selectorCards.value = await assistantStore.loadCardsForProject(pid)
}

function onTreeCheck(_: any, meta: any) {
  // meta.checkedKeys: string[]
  const keys: string[] = (meta?.checkedKeys || []) as string[]
  selectorCheckedKeys.value = keys
  const ids = keys.filter(k => k.startsWith('card:')).map(k => Number(k.split(':')[1])).filter(n => Number.isFinite(n))
  selectorSelectedIds.value = ids
}

function removeInjectedRef(idx: number) { assistantStore.removeInjectedRefAt(idx) }

async function confirmAddInjectedRefs() {
  try {
    const pid = selectorSourcePid.value as number
    const pname = assistantStore.projects.find(p => p.id === pid)?.name || ''
    assistantStore.addInjectedRefs(pid, pname, selectorSelectedIds.value)
  } finally { selectorVisible.value = false }
}

function pruneEmpty(val: any): any {
  if (val == null) return val
  if (typeof val === 'string') return val.trim() === '' ? undefined : val
  if (typeof val !== 'object') return val
  if (Array.isArray(val)) {
    const arr = val.map(pruneEmpty).filter(v => v !== undefined)
    return arr
  }
  const out: Record<string, any> = {}
  for (const [k, v] of Object.entries(val)) {
    const pv = pruneEmpty(v)
    if (pv === undefined) continue
    if (typeof pv === 'object' && !Array.isArray(pv) && Object.keys(pv).length === 0) continue
    if (Array.isArray(pv) && pv.length === 0) continue
    out[k] = pv
  }
  return out
}

function buildConversationText() { 
  return messages.value.map(m => {
    const prefix = m.role === 'user' ? 'User:' : 'Assistant:'
    let text = `${prefix} ${m.content}`
    
    // Add tool history
    if (m.tools && m.tools.length > 0) {
      text += '\n\n[Tool Call Record]'
      for (const tool of m.tools) {
        text += `\n- Tool: ${tool.tool_name}`
        if (tool.result) {
          text += `\n  Result: ${JSON.stringify(tool.result, null, 2)}`
        }
      }
    }
    
    return text
  }).join('\n\n')
}

//  Build Assistant Request Params
function buildAssistantChatRequest() {
  const parts: string[] = []
  
  // 1. Project Structure Context
  if (assistantStore.projectStructure) {
    const struct = assistantStore.projectStructure
    parts.push(`# Project: ${struct.project_name}`)
    parts.push(`Project ID: ${struct.project_id} | Total Cards: ${struct.total_cards}`)
    parts.push('')
    
    // Stats
    const stats = Object.entries(struct.stats)
      .map(([type, count]) => `- ${type}: ${count} Cards`)
      .join('\n')
    parts.push(`## 📊 Project Stats\n${stats}`)
    parts.push('')
    
    // Tree
    parts.push(`## 🌲 Card Structure Tree\nROOT\n${struct.tree_text}`)
    parts.push('')
    
    // Available Types
    parts.push(`## 🏷️ Available Card Types`)
    parts.push(struct.available_card_types.join(' | '))
    parts.push('')
  }
  
  // 2. Recent Operations
  const opsText = assistantStore.formatRecentOperations()
  if (opsText) {
    parts.push(`## 📝 Recent Operations\n${opsText}`)
    parts.push('')
  }
  
  // 3. Current Card (Including Schema)
  const context = assistantStore.getContextForAssistant()
  if (context.active_card) {
    parts.push(`## ⭐ Current Card`)
    parts.push(`"${context.active_card.title}" (ID: ${context.active_card.card_id}, Type: ${context.active_card.card_type})`)
    
    // Add JSON Schema
    if (props.effectiveSchema) {
      try {
        const schemaText = JSON.stringify(props.effectiveSchema, null, 2)
        parts.push(`\n### Card Structure (JSON Schema)`)
        parts.push('```json')
        parts.push(schemaText)
        parts.push('```')
      } catch {}
    }
    
    parts.push('')
  }
  
  // 4. Cited Card Data
  if (assistantStore.injectedRefs.length) {
    const blocks: string[] = []
    for (const ref of assistantStore.injectedRefs) {
      try {
        const cleaned = pruneEmpty(ref.content)
        const text = JSON.stringify(cleaned ?? {}, null, 2)
        const clipped = text.length > 4000 ? text.slice(0, 4000) + '\n/* ... */' : text
        blocks.push(`### [Ref] ${ref.projectName} / ${ref.cardTitle}\n\`\`\`json\n${clipped}\n\`\`\``)
      } catch {}
    }
    parts.push(`## 📎 Cited Cards\n${blocks.join('\n\n')}`)
    parts.push('')
  }
  
  // 5. DSL Context
  if (props.resolvedContext) {
    parts.push(`## 🔗 Context Reference\n${props.resolvedContext}`)
    parts.push('')
  }
  
  // 6. Chat History
  parts.push(`## 💬 Chat History`)
  parts.push(buildConversationText())
  
  // Get last user message
  const lastUserMessage = messages.value.filter(m => m.role === 'user').pop()
  const userPrompt = lastUserMessage?.content?.trim() || ''
  
  return {
    user_prompt: userPrompt,
    context_info: parts.join('\n')
  }
}

function scrollToBottom() { nextTick(() => { try { const el = messagesEl.value; if (el) el.scrollTop = el.scrollHeight } catch {} }) }

function startStreaming(_prev: string, _tail: string, targetIdx: number) {
  isStreaming.value = true
  
  // Build request params
  const chatRequest = buildAssistantChatRequest()
  
  // Temp tool call state
  let pendingToolCalls: any[] = []
  
  streamCtl = generateContinuationStreaming({
    ...chatRequest,
    llm_config_id: effectiveLlmId.value as number,
    prompt_name: (props.promptName && props.promptName.trim()) ? props.promptName : 'Chat',
    project_id: projectStore.currentProject?.id as number,
    stream: true,
    temperature: props.temperature ?? 0.7,
    max_tokens: props.max_tokens ?? 8192,
    timeout: props.timeout ?? undefined,
    use_react_mode: useReactMode.value  // ReAct Mode Switch
  } as any, (chunk) => {
    // 🔑 Detect special markers
    
    // ReAct: Detect Tool Call Start
    if (chunk.includes('__TOOL_CALL_DETECTED__')) {
      if (messages.value[targetIdx]) {
        messages.value[targetIdx].toolsInProgress = '⏳ Calling tools...'
      }
      scrollToBottom()
      return
    }
    
    // ReAct: Detect Tool Executed
    if (chunk.includes('__TOOL_EXECUTED__:')) {
      const match = chunk.match(/__TOOL_EXECUTED__:(.+)/)
      if (match && messages.value[targetIdx]) {
        try {
          const toolResult = JSON.parse(match[1])
          
          // Record tool call
          if (!messages.value[targetIdx].tools) {
            messages.value[targetIdx].tools = []
          }
          messages.value[targetIdx].tools.push(toolResult)
          
          // Clear progress status
          messages.value[targetIdx].toolsInProgress = undefined
          
          // Refresh logic
          handleToolsExecuted([toolResult])
          
          scrollToBottom()
        } catch (e) {
          console.warn('[ReAct] Parse tool result failed', e)
        }
      }
      return
    }
    
    // Detect __TOOL_CALL_START__ (Standard Mode)
    if (chunk.includes('__TOOL_CALL_START__:')) {
      const match = chunk.match(/__TOOL_CALL_START__:(.+)/)
      if (match && messages.value[targetIdx]) {
        try {
          const toolCall = JSON.parse(match[1])
          pendingToolCalls.push(toolCall)
          
          if (!messages.value[targetIdx].toolsInProgress) {
            const toolsPreview = pendingToolCalls.map(t => `⏳ Calling tool: ${t.tool_name}...`).join('\n')
            messages.value[targetIdx].toolsInProgress = toolsPreview
          }
          scrollToBottom()
        } catch (e) {
          console.warn('Parse tool call start failed', e)
        }
      }
      return  // Do not add to message content
    }
    
    // Detect __RETRY__
    if (chunk.includes('__RETRY__:')) {
      const match = chunk.match(/__RETRY__:(.+)/)
      if (match && messages.value[targetIdx]) {
        try {
          const retryInfo = JSON.parse(match[1])
          messages.value[targetIdx].toolsInProgress = 
            `🔄 Tool call failed, ${retryInfo.reason}, retrying (${retryInfo.retry}/${retryInfo.max})...`
          scrollToBottom()
        } catch (e) {
          console.warn('Parse retry info failed', e)
        }
      }
      return  // Do not add
    }
    
    // Detect __TOOL_SUMMARY__
    if (chunk.includes('__TOOL_SUMMARY__:')) {
      const match = chunk.match(/__TOOL_SUMMARY__:(.+)/)
      if (match && messages.value[targetIdx]) {
        try {
          const summary = JSON.parse(match[1])
          handleToolsExecuted(summary.tools)
          messages.value[targetIdx].toolsInProgress = undefined
          pendingToolCalls = []
        } catch (e) {
          console.warn('Parse tool summary failed', e)
        }
      }
      return  // Do not add
    }
    
    // Detect __ERROR__
    if (chunk.includes('__ERROR__:')) {
      const match = chunk.match(/__ERROR__:(.+)/)
      if (match && messages.value[targetIdx]) {
        try {
          const errorInfo = JSON.parse(match[1])
          messages.value[targetIdx].toolsInProgress = `❌ Tool call failed: ${errorInfo.error || 'Execution failed'}`
          pendingToolCalls = []
          scrollToBottom()
        } catch (e) {
          console.warn('Parse error info failed', e)
        }
      }
      return  // Do not add
    }
    
    // Detect <notify>tool_name</notify>
    let hasToolTag = false
    const toolMatch = chunk.match(/<notify>([\w\-]+)<\/notify>/)
    if (toolMatch && messages.value[targetIdx]) {
      hasToolTag = true
      const toolName = toolMatch[1]
      
      // Immediately show status
      if (!messages.value[targetIdx].toolsInProgress) {
        messages.value[targetIdx].toolsInProgress = `⏳ Calling tool: ${toolName}...`
        scrollToBottom()
      }
      
      // Remove tag
      chunk = chunk.replace(/<notify>[\w\-]+<\/notify>/g, '')
    }
    
    // If no content after filtering
    const trimmedChunk = chunk.trim()
    if (!trimmedChunk) {
      if (hasToolTag) scrollToBottom()
      return
    }
    
    // Safety check
    if (!messages.value[targetIdx]) {
      console.warn(`⚠️ [AssistantPanel] Target msg index ${targetIdx} missing, stop stream`)
      return
    }
    
    // Append content
    messages.value[targetIdx].content += chunk
    
    // Clear progress on receiving text
    if (trimmedChunk.length > 0 && messages.value[targetIdx]?.toolsInProgress) {
      if (!messages.value[targetIdx].toolsInProgress.includes('❌')) {
        nextTick(() => {
          if (messages.value[targetIdx]) {
            messages.value[targetIdx].toolsInProgress = undefined
            pendingToolCalls = []
          }
        })
      }
    }
    
    scrollToBottom()
  }, () => {
    // End stream
    isStreaming.value = false
    streamCtl = null
    
    // Clear progress unless error
    if (messages.value[targetIdx]?.toolsInProgress && 
        !messages.value[targetIdx].toolsInProgress.includes('❌')) {
      messages.value[targetIdx].toolsInProgress = undefined
      pendingToolCalls = []
    }
    
    try { 
      const pid = projectStore.currentProject?.id
      if (pid && messages.value[targetIdx]) {
        assistantStore.appendHistory(pid, { role: 'assistant', content: messages.value[targetIdx].content })
      }
    } catch {}
  }, (err) => { 
    // Error
    if (messages.value[targetIdx]) {
      messages.value[targetIdx].toolsInProgress = undefined
    }
    pendingToolCalls = []
    ElMessage.error(err?.message || 'Generation Failed')
    isStreaming.value = false
    streamCtl = null 
  }) as any
}

function handleSend() {
  if (!canSend.value || isStreaming.value) return
  lastRun.value = null
  const userText = draft.value.trim(); if (!userText) return
  messages.value.push({ role: 'user', content: userText })
  try { const pid = projectStore.currentProject?.id; if (pid) assistantStore.appendHistory(pid, { role: 'user', content: userText }) } catch {}
  draft.value = ''
  scrollToBottom()

  // Assistant prompt
  const assistantIdx = messages.value.push({ role: 'assistant', content: '' }) - 1
  scrollToBottom()
  lastRun.value = { prev: '', tail: '', targetIdx: assistantIdx }
  startStreaming('', '', assistantIdx)
}

function handleCancel() { 
  try { streamCtl?.cancel() } catch {}
  isStreaming.value = false
  
  messages.value.forEach(msg => {
    if (msg.toolsInProgress) {
      msg.toolsInProgress = undefined
    }
  })
}
function handleRegenerate() { if (!canRegenerate.value || !lastRun.value) return; messages.value[lastRun.value.targetIdx].content = ''; scrollToBottom(); startStreaming('', '', lastRun.value.targetIdx) }
function regenerateFromCurrent() {
  if (isStreaming.value) return
  const lastIndex = messages.value.length - 1
  const lastIsAssistant = lastIndex >= 0 && messages.value[lastIndex].role === 'assistant'
  let targetIdx: number
  if (lastIsAssistant) {
    messages.value[lastIndex].content = ''
    targetIdx = lastIndex
  } else {
    targetIdx = messages.value.push({ role: 'assistant', content: '' }) - 1
  }
  lastRun.value = { prev: '', tail: '', targetIdx }
  startStreaming('', '', targetIdx)
}
function handleRegenerateWithHistory() {
  try {
    const pid = projectStore.currentProject?.id
    if (pid) {
      const hist = assistantStore.getHistory(pid)
      for (let i = hist.length - 1; i >= 0; i--) { if (hist[i].role === 'assistant') { hist.splice(i, 1); break } }
      assistantStore.setHistory(pid, hist)
    }
  } catch {}
  if (lastRun.value && canRegenerate.value) {
    handleRegenerate()
  } else {
    regenerateFromCurrent()
  }
}
function handleFinalize() { const summary = (() => { const last = [...messages.value].reverse().find(m => m.role === 'assistant'); return (last?.content || '').trim() || buildConversationText() })(); emit('finalize', summary) }
function onChipClick(refItem: { projectId: number; cardId: number }) {
  emit('jump-to-card', { projectId: refItem.projectId, cardId: refItem.cardId })
}

function toConversationText(list: Array<{ role: 'user'|'assistant'; content: string }>) {
  return list.map(m => {
    const prefix = m.role === 'user' ? 'User:' : 'Assistant:'
    return `${prefix} ${m.content}`
  }).join('\n\n')
}

function handleRegenerateAt(idx: number) {
  if (isStreaming.value) return
  if (idx < 0 || idx >= messages.value.length) return
  if (messages.value[idx].role !== 'assistant') return
  try {
    const pid = projectStore.currentProject?.id
    if (pid) {
      const prevMsgs = messages.value.slice(0, idx)
      assistantStore.setHistory(pid, prevMsgs.map(m => ({ role: m.role as any, content: m.content })))
    }
  } catch {}
  messages.value[idx].content = ''
  messages.value[idx].tools = undefined
  if (messages.value.length > idx + 1) messages.value.splice(idx + 1)
  lastRun.value = { prev: '', tail: '', targetIdx: idx }
  startStreaming('', '', idx)
}

function onComposerKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    if (!e.shiftKey) {
      e.preventDefault()
      if (canSend.value && !isStreaming.value) handleSend()
    }
  }
}

onMounted(async () => {
  try {
    llmOptions.value = await listLLMConfigs()
    const pid = projectStore.currentProject?.id
    
    const saved = pid ? Number(localStorage.getItem(modelKeyForProject(pid)) || '') : NaN
    if (saved && Number.isFinite(saved)) {
      overrideLlmId.value = saved
    } else if (!overrideLlmId.value && llmOptions.value.length > 0) {
      overrideLlmId.value = llmOptions.value[0].id
    }
    
    if (pid) {
      const reactModeSaved = localStorage.getItem(reactModeKeyForProject(pid))
      if (reactModeSaved !== null) {
        useReactMode.value = reactModeSaved === 'true'
      }
    }
  } catch {}
})

async function handleCopy(idx: number) {
  try {
    await navigator.clipboard.writeText(messages.value[idx]?.content || '')
    ElMessage.success('Copied to clipboard')
  } catch {
    ElMessage.error('Copy failed')
  }
}

// Handle Tool Results
function handleToolsExecuted(tools: Array<{tool_name: string, result: any}>) {
  console.log('🔧 Tools executed:', tools)
  
  const lastIdx = messages.value.length - 1
  if (lastIdx >= 0 && messages.value[lastIdx].role === 'assistant') {
    messages.value[lastIdx].tools = tools
  }
  
  const needsRefresh = tools.some(t => {
    const toolName = t.tool_name
    const result = t.result
    
    const refreshTools = ['create_card', 'modify_card_field', 'batch_create_cards', 'replace_field_text']
    
    if (refreshTools.includes(toolName)) {
      return true
    }
    
    if (result?.card_id) {
      return true
    }
    
    return false
  })
  
  if (needsRefresh && projectStore.currentProject?.id) {
    const cardStore = useCardStore()
    cardStore.fetchCards(projectStore.currentProject.id).then(() => {
      console.log('✅ Card list refreshed')
    }).catch((err) => {
      console.error('❌ Card list refresh failed:', err)
    })
  }
  
  const successTools = tools.filter(t => t.result?.success)
  if (successTools.length > 0) {
    ElMessage.success(`✅ Executed ${successTools.length} actions`)
  }
}

function formatToolName(name: string): string {
  const map: Record<string, string> = {
    'search_cards': 'Search Cards',
    'create_card': 'Create Card',
    'modify_card_field': 'Modify Field',
    'batch_create_cards': 'Batch Create',
    'replace_field_text': 'Replace Text'
  }
  return map[name] || name
}

// ===== Session Management =====
function getSessionStorageKey(projectId: number): string {
  return `assistant-sessions-${projectId}`
}

function loadHistorySessions(projectId: number) {
  try {
    const key = getSessionStorageKey(projectId)
    const stored = localStorage.getItem(key)
    if (stored) {
      const sessions = JSON.parse(stored) as ChatSession[]
      historySessions.value = sessions.sort((a, b) => b.updatedAt - a.updatedAt)
      console.log(`📚 Loaded ${sessions.length} sessions`)
    } else {
      historySessions.value = []
    }
  } catch (e) {
    console.error('Failed to load history sessions:', e)
    historySessions.value = []
  }
}

function saveCurrentSession() {
  if (!projectStore.currentProject?.id) return
  if (messages.value.length === 0) return
  
  try {
    const sessionToSave = {
      ...currentSession.value,
      messages: JSON.parse(JSON.stringify(messages.value)),
      updatedAt: Date.now(),
      projectId: projectStore.currentProject.id
    }
    
    if (sessionToSave.title === 'New Chat') {
      const firstUserMsg = messages.value.find(m => m.role === 'user')
      if (firstUserMsg) {
        sessionToSave.title = firstUserMsg.content.substring(0, 20) + (firstUserMsg.content.length > 20 ? '...' : '')
      }
    }
    
    const key = getSessionStorageKey(projectStore.currentProject.id)
    
    let sessions: ChatSession[] = []
    try {
      const stored = localStorage.getItem(key)
      sessions = stored ? JSON.parse(stored) : []
    } catch {
      sessions = []
    }
    
    const existingIndex = sessions.findIndex(s => s.id === sessionToSave.id)
    if (existingIndex >= 0) {
      sessions[existingIndex] = sessionToSave
      const [updated] = sessions.splice(existingIndex, 1)
      sessions.unshift(updated)
    } else {
      sessions.unshift(sessionToSave)
    }
    
    if (sessions.length > 50) {
      sessions.splice(50)
    }
    
    localStorage.setItem(key, JSON.stringify(sessions))
    historySessions.value = sessions
    
    if (currentSession.value.title !== sessionToSave.title) {
      currentSession.value.title = sessionToSave.title
    }
  } catch (e) {
    console.error('Failed to save session:', e)
  }
}

function createNewSession() {
  if (messages.value.length > 0) {
    saveCurrentSession()
  }
  
  currentSession.value = {
    id: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    projectId: projectStore.currentProject?.id || 0,
    title: 'New Chat',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: []
  }
  
  messages.value = []
  historyDrawerVisible.value = false
  console.log('📝 Create New Chat')
}

function loadSession(sessionId: string) {
  const session = historySessions.value.find(s => s.id === sessionId)
  if (!session) return
  
  if (messages.value.length > 0) {
    saveCurrentSession()
  }
  
  currentSession.value = { ...session }
  messages.value = [...session.messages]
  
  historyDrawerVisible.value = false
  
  console.log('📖 Load session:', session.title)
  nextTick(() => scrollToBottom())
}

function deleteSession(sessionId: string) {
  if (!projectStore.currentProject?.id) return
  
  try {
    const key = getSessionStorageKey(projectStore.currentProject.id)
    historySessions.value = historySessions.value.filter(s => s.id !== sessionId)
    localStorage.setItem(key, JSON.stringify(historySessions.value))
    
    if (currentSession.value.id === sessionId) {
      createNewSession()
    }
    
    ElMessage.success('Chat deleted')
  } catch (e) {
    console.error('Delete chat failed:', e)
    ElMessage.error('Delete chat failed')
  }
}

function handleDeleteSession(sessionId: string) {
  ElMessageBox.confirm('Are you sure you want to delete this chat?', 'Confirm Delete', {
    confirmButtonText: 'Delete',
    cancelButtonText: 'Cancel',
    type: 'warning'
  }).then(() => {
    deleteSession(sessionId)
  }).catch(() => {})
}

function formatSessionTime(timestamp: number): string {
  const now = Date.now()
  const diff = now - timestamp
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  
  if (diff < minute) {
    return 'Just now'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)} mins ago`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)} hours ago`
  } else if (diff < 7 * day) {
    return `${Math.floor(diff / day)} days ago`
  } else {
    const date = new Date(timestamp)
    return `${date.getMonth() + 1}/${date.getDate()}`
  }
}

function filterMessageContent(content: string): string {
  if (!content) return ''
  let filtered = content.replace(/<notify>[\w\-]*<\/notify>/g, '')
  filtered = filtered.replace(/<notify[^>]*$/g, '')
  filtered = filtered.replace(/<tool_call>[\s\S]*?<\/tool_call>/g, '')
  filtered = filtered.replace(/<tool_call[^>]*$/g, '')
  filtered = filtered.replace(/__TOOL_CALL_START__:.*/g, '')
  filtered = filtered.replace(/__TOOL_CALL_DETECTED__.*/g, '')
  filtered = filtered.replace(/__TOOL_EXECUTED__:.*/g, '')
  filtered = filtered.replace(/__RETRY__:.*/g, '')
  filtered = filtered.replace(/__TOOL_SUMMARY__:.*/g, '')
  filtered = filtered.replace(/__ERROR__:.*/g, '')
  filtered = filtered.replace(/\*\*工具执行结果\*\*：[\s\S]*?```json[\s\S]*?```/g, '')
  return filtered.trim()
}

watch(() => projectStore.currentProject?.id, (newProjectId, oldProjectId) => {
  if (newProjectId) {
    loadHistorySessions(newProjectId)
    if (historySessions.value.length > 0) {
      const latestSession = historySessions.value[0]
      currentSession.value = { ...latestSession }
      messages.value = [...latestSession.messages]
      console.log('📖 Load recent session:', latestSession.title)
      nextTick(() => scrollToBottom())
    } else {
      createNewSession()
    }
  }
}, { immediate: true })

let saveDebounceTimer: any = null
watch([
  () => messages.value.length,
  () => messages.value[messages.value.length - 1]?.content
], () => {
  if (messages.value.length > 0) {
    if (saveDebounceTimer) clearTimeout(saveDebounceTimer)
    saveDebounceTimer = setTimeout(() => {
      saveCurrentSession()
    }, 300)
  }
})
</script>

<style scoped>
/* Main Panel */
.assistant-panel { 
  display: flex; 
  flex-direction: column; 
  height: 100%; 
  font-size: 13px;
  font-family:"Segoe UI", "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
.panel-header { display: flex; flex-direction: column; gap: 8px; padding: 8px; border-bottom: 1px solid var(--el-border-color-light); background: var(--el-bg-color); }
.header-title-row { 
  display: flex; 
  align-items: center; 
  gap: 12px; 
}
.title-area {
  flex: 1;
  display: flex;
  align-items: baseline;
  gap: 8px;
  overflow: hidden;
}
.main-title { 
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 15px;
  flex-shrink: 0;
}
.session-subtitle {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-controls-row { display: flex; align-items: center; gap: 4px; flex-wrap: nowrap; overflow-x: auto; }
.panel-header .card-tag { flex-shrink: 0; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.panel-header .spacer { flex: 1; min-width: 4px; }
.ctx-tag { cursor: pointer; flex-shrink: 0; font-size: 12px; }
.header-controls-row .el-button { flex-shrink: 0; padding: 3px 6px; font-size: 12px; }
.ctx-preview { max-height: 40vh; overflow: auto; white-space: pre-wrap; background: var(--el-bg-color); color: var(--el-text-color-primary); padding: 8px; border: 1px solid var(--el-border-color-lighter); border-radius: 6px; }
.chat-area { flex: 1; display: flex; flex-direction: column; gap: 6px; overflow: hidden; padding: 6px 8px; }
.messages { flex: 1; overflow: auto; display: flex; flex-direction: column; gap: 6px; padding: 8px; border: 1px solid var(--el-border-color-light); border-radius: 8px; background: var(--el-fill-color-blank); }
.msg { display: flex; flex-direction: column; align-items: flex-start; }
.msg.user { align-items: flex-end; }
.msg.assistant { align-items: flex-start; }
.bubble { max-width: 80%; padding: 8px 10px; border-radius: 8px; }
.bubble-text { margin: 0; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; color: var(--el-text-color-primary); user-select: text; cursor: text; }

/* Markdown Style */
.bubble-markdown { 
  font-size: 13px;
  line-height: 1.6;
  font-family: 、"Segoe UI",  "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  color: var(--el-text-color-primary);
  user-select: text;
  cursor: text;
}

.bubble-markdown :deep(*) {
  user-select: text !important;
}


/* User message white text */
.msg.user .bubble-markdown :deep(*) { 
  color: var(--el-color-white) !important; 
}
.msg.user .bubble-markdown :deep(code) { 
  background: rgba(255, 255, 255, 0.2) !important; 
}
.msg.user .bubble-markdown :deep(pre) { 
  background: rgba(255, 255, 255, 0.15) !important; 
}
.msg.user .bubble-markdown :deep(a) { 
  color: var(--el-color-white) !important;
  text-decoration: underline;
}

.msg.assistant .bubble { background: var(--el-fill-color-light); border: 1px solid var(--el-border-color); }
.msg.user .bubble { background: var(--el-color-primary); color: var(--el-color-white); }
.msg.user .bubble-text { color: var(--el-color-white); }
.msg-toolbar { display: flex; gap: 6px; padding: 4px 0 0 2px; }
.streaming-tip { color: var(--el-text-color-secondary); padding-left: 4px; font-size: 12px; }
.composer { 
  display: flex; 
  flex-direction: column; 
  gap: 6px; 
  padding: 10px; 
  border-top: 1px solid var(--el-border-color-light); 
}

/* Inject Toolbar */
.inject-toolbar { 
  display: flex; 
  align-items: flex-start; 
  justify-content: space-between; 
  gap: 8px; 
  padding-bottom: 6px; 
  min-height: 28px;
  max-height: 64px;
}

.inject-toolbar .chips { 
  display: flex; 
  align-items: flex-start;
  gap: 6px; 
  flex: 1;
  overflow: hidden;
  max-height: 58px;
}

.chips-tags {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  row-gap: 6px;
  flex-wrap: wrap;
  flex: 1;
  overflow: hidden;
  line-height: 1.2;
  align-content: flex-start;
  min-height: 24px;
}

.chips-more {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.chip-tag { 
  cursor: pointer;
  font-size: 12px !important;
  height: 24px !important;
  line-height: 22px !important;
  padding: 0 8px !important;
  margin: 0;
  flex-shrink: 0;
  white-space: nowrap;
}

/* Composer Input */
.composer-input {
  flex: 1;
  min-height: 90px;
}

::deep(.composer-input .el-textarea__inner) {
  min-height: 90px !important;
  font-size: 13px;
  line-height: 1.6;
}

.more-refs-btn {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  padding: 0 10px !important;
  height: 24px !important;
  line-height: 22px !important;
  border: 1px dashed var(--el-color-primary);
  border-radius: 4px;
  flex-shrink: 0;
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.more-refs-btn:hover {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
}

.more-refs-dots {
  font-weight: 700;
  letter-spacing: 1px;
}

.more-refs-count {
  font-size: 11px;
  font-weight: 500;
  opacity: 0.85;
}

.add-ref-btn {
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 2px;
}

/* More Refs Popover */
.more-refs-popover {
  padding: 0;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-weight: 600;
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.popover-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: normal;
}

.more-refs-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 320px;
  overflow-y: auto;
  padding: 8px;
}

.more-ref-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  transition: all 0.2s;
}

.more-ref-item:hover {
  background: var(--el-fill-color);
}

.more-ref-item .ref-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--el-text-color-regular);
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.more-ref-item .ref-info:hover {
  color: var(--el-color-primary);
}

.composer-subbar { 
  display: flex; 
  align-items: center; 
  gap: 8px; 
  padding: 2px 0;
}

.composer-actions { 
  display: flex; 
  gap: 6px; 
  justify-content: flex-end; 
  flex-wrap: nowrap; 
  align-items: center; 
  padding: 4px 0 0 0;
}

::deep(.composer .el-button) { padding: 6px 8px; font-size: 12px; }
::deep(.inject-toolbar .el-button) { padding: 4px 8px !important; font-size: 12px; height: 24px; }

/* Tool in progress */
.tools-in-progress {
  margin-top: 8px;
  max-width: 80%;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-color-warning-light-7);
  border-radius: 8px;
  padding: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-color-warning);
}

.tools-in-progress .tools-icon {
  font-size: 16px;
}

.tools-in-progress .spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tools-progress-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  color: var(--el-color-warning-dark-2);
}

/* Tool Summary */
.tools-summary {
  margin-top: 8px;
  max-width: 80%;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-color-success-light-7);
  border-radius: 8px;
  padding: 8px;
}

.tools-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  color: var(--el-color-success);
  font-weight: 600;
  font-size: 13px;
}

.tools-icon {
  font-size: 16px;
}

.tools-count {
  color: var(--el-color-success);
}

.tools-collapse {
  margin-top: 4px;
}

.tools-expand-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tool-item {
  padding: 12px;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  background: var(--el-fill-color-blank);
  border-radius: 6px;
  margin-bottom: 8px;
}

.tool-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.tool-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.tool-status {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.tool-details {
  margin-top: 8px;
}

.tool-message {
  color: var(--el-text-color-regular);
  font-size: 12px;
  margin-bottom: 8px;
  padding: 6px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.tool-result-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.result-field {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 12px;
}

.field-label {
  color: var(--el-text-color-secondary);
  font-weight: 600;
  min-width: 70px;
}

.field-value {
  color: var(--el-text-color-primary);
  font-family: 'Consolas', 'Monaco', monospace;
}

.tool-json-collapse {
  margin-top: 4px;
}

.tool-json {
  font-size: 11px;
  background: var(--el-fill-color-darker);
  padding: 8px;
  border-radius: 4px;
  overflow-x: auto;
  max-height: 300px;
  color: var(--el-text-color-primary);
  font-family: 'Consolas', 'Monaco', monospace;
}

.tool-msg {
  color: var(--el-text-color-regular);
  font-size: 12px;
  flex: 1;
}

/* History Drawer */
.history-drawer-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
}

.history-actions {
  padding: 0 0 8px 0;
}

.empty-history {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0;
}

.history-item {
  padding: 12px;
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-light);
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: var(--el-fill-color-light);
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.history-item.is-current {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
}

.history-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.history-icon {
  color: var(--el-color-primary);
  font-size: 16px;
  flex-shrink: 0;
}

.history-title {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-time {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
</style>
