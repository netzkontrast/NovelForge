<template>
  <div class="generic-card-editor">
    <EditorHeader
      :project-name="projectName"
      :card-type="props.card.card_type.name"
      v-model:title="titleProxy"
      :dirty="isDirty"
      :saving="isSaving"
      :can-save="isDirty && !isSaving"
      :last-saved-at="lastSavedAt"
      :is-chapter-content="!!activeContentEditor"
      @save="handleSave"
      @generate="handleGenerate"
      @open-context="openDrawer = true"
      @delete="handleDelete"
      @open-versions="showVersions = true"
    />
    
    <!-- Custom Content Editor (e.g. CodeMirrorEditor)-->
    <template v-if="activeContentEditor">
      <component 
        :is="activeContentEditor"
        ref="contentEditorRef"
        :card="props.card"
        :prefetched="props.prefetched"
        @switch-tab="handleSwitchTab"
        @update:dirty="handleContentEditorDirtyChange"
      />
    </template>
    
    <!-- Default Form Editor -->
    <template v-else>
      <!-- Params Config: Show current model ID, click to pop up config panel in place -->
      <div class="toolbar-row param-toolbar">
        <div class="param-inline">
          <AIPerCardParams :card-id="props.card.id" :card-type-name="props.card.card_type?.name" />
          <el-button size="small" type="primary" plain @click="schemaStudioVisible = true">Structure</el-button>
        </div>
      </div>

      <div class="editor-body">
        <div class="main-pane">
          <div v-if="schema" class="form-container">
            <template v-if="sections && sections.length">
              <SectionedForm v-if="wrapperName" :schema="innerSchema" v-model="innerData" :sections="sections" />
              <SectionedForm v-else :schema="schema" v-model="localData" :sections="sections" />
            </template>
            <template v-else>
              <ModelDrivenForm v-if="wrapperName" :schema="innerSchema" v-model="innerData" />
              <ModelDrivenForm v-else :schema="schema" v-model="localData" />
            </template>
          </div>
          <div v-else class="loading-or-error-container">
            <p v-if="schemaIsLoading">Loading model...</p>
            <p v-else>Cannot load edit model for this card content.</p>
          </div>
        </div>
      </div>
    </template>

    <ContextDrawer
      v-model="openDrawer"
      :context-template="localAiContextTemplate"
      :preview-text="previewText"
      @apply-context="applyContextTemplateAndSave"
      @open-selector="openSelectorFromDrawer"
    >
      <template #params>
        <div class="param-placeholder">Params Setting Entry (Changed to per-card local params)</div>
      </template>
    </ContextDrawer>

    <CardReferenceSelectorDialog v-model="isSelectorVisible" :cards="cards" :currentCardId="props.card.id" @confirm="handleReferenceConfirm" />
    <CardVersionsDialog
      v-if="projectStore.currentProject?.id"
      v-model="showVersions"
      :project-id="projectStore.currentProject!.id"
      :card-id="props.card.id"
      :current-content="wrapperName ? innerData : localData"
      :current-context-template="localAiContextTemplate"
      @restore="handleRestoreVersion"
    />

    <SchemaStudio v-model:visible="schemaStudioVisible" :mode="'card'" :target-id="props.card.id" :context-title="props.card.title" @saved="onSchemaSaved" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted, onBeforeUnmount, defineAsyncComponent } from 'vue'
import { storeToRefs } from 'pinia'
import { useCardStore } from '@renderer/stores/useCardStore'
import { useAIStore } from '@renderer/stores/useAIStore'
import { usePerCardAISettingsStore, type PerCardAIParams } from '@renderer/stores/usePerCardAISettingsStore'
import { getCardAIParams, updateCardAIParams, applyCardAIParamsToType } from '@renderer/api/setting'
import { useProjectStore } from '@renderer/stores/useProjectStore'
import { schemaService } from '@renderer/api/schema'
import type { JSONSchema } from '@renderer/api/schema'
import { getAIConfigOptions, type AIConfigOptions } from '@renderer/api/ai'
import ModelDrivenForm from '../dynamic-form/ModelDrivenForm.vue'
import SectionedForm from '../dynamic-form/SectionedForm.vue'
import { mergeSections, autoGroup, type SectionConfig } from '@renderer/services/uiLayoutService'
import CardReferenceSelectorDialog from './CardReferenceSelectorDialog.vue'
import EditorHeader from '../common/EditorHeader.vue'
import ContextDrawer from '../common/ContextDrawer.vue'
import CardVersionsDialog from '../common/CardVersionsDialog.vue'
import { cloneDeep, isEqual } from 'lodash-es'
import type { CardRead, CardUpdate } from '@renderer/api/cards'
import { ElMessage, ElMessageBox } from 'element-plus'
import { addVersion } from '@renderer/services/versionService'
import { Setting } from '@element-plus/icons-vue'
import { useAIStore as useAIStoreForOptions } from '@renderer/stores/useAIStore'
import SchemaStudio from '../shared/SchemaStudio.vue'
import AIPerCardParams from '../common/AIPerCardParams.vue'
// Removed AssistantSidebar import and logic
import { resolveTemplate } from '@renderer/services/contextResolver'

const props = defineProps<{ 
  card: CardRead
  prefetched?: any
}>()

const cardStore = useCardStore()
const aiStore = useAIStore()
const perCardStore = usePerCardAISettingsStore()
const projectStore = useProjectStore()
const aiStoreForOptions = useAIStoreForOptions()

const { cards } = storeToRefs(cardStore)

const openDrawer = ref(false)
const isSelectorVisible = ref(false)
const showVersions = ref(false)
const schemaStudioVisible = ref(false)
const assistantVisible = ref(false)
const assistantResolvedContext = ref<string>('')
const assistantEffectiveSchema = ref<any>(null)
const prefetchedContext = ref<any>(null)

// --- Content Editor Dynamic Mapping ---
// Similar to CardEditorHost editorMap, but here for content editors (shared shell)
const contentEditorMap: Record<string, any> = {
  CodeMirrorEditor: defineAsyncComponent(() => import('../editors/CodeMirrorEditor.vue')),
  // Future additions:
  // RichTextEditor: defineAsyncComponent(() => import('../editors/RichTextEditor.vue')),
  // MarkdownEditor: defineAsyncComponent(() => import('../editors/MarkdownEditor.vue')),
}

// Select content editor based on card_type.editor_component
const activeContentEditor = computed(() => {
  const editorName = props.card?.card_type?.editor_component
  if (editorName && contentEditorMap[editorName]) {
    return contentEditorMap[editorName]
  }
  return null // null means use default form editor
})

// Generic content editor reference (Can be CodeMirrorEditor or other)
const contentEditorRef = ref<any>(null)
const contentEditorDirty = ref(false)

function handleSwitchTab(tab: string) {
  const evt = new CustomEvent('nf:switch-right-tab', { detail: { tab } })
  window.dispatchEvent(evt)
}

function handleContentEditorDirtyChange(dirty: boolean) {
  contentEditorDirty.value = dirty
}

function openAssistant() {
  const editingContent = wrapperName.value ? innerData.value : localData.value
  const currentCardForResolve = { ...props.card, content: editingContent }
  const resolved = resolveTemplate({ template: localAiContextTemplate.value, cards: cards.value, currentCard: currentCardForResolve as any })
  assistantResolvedContext.value = resolved
  // Read effective Schema as chat guidance
  import('@renderer/api/setting').then(async ({ getCardSchema }) => {
    try {
      const resp = await getCardSchema(props.card.id)
      assistantEffectiveSchema.value = resp?.effective_schema || resp?.json_schema || null
    } catch { assistantEffectiveSchema.value = null }
  })
  assistantVisible.value = true
}

const isSaving = ref(false)
const localData = ref<any>({})
const localAiContextTemplate = ref<string>('')
const originalData = ref<any>({})
const originalAiContextTemplate = ref<string>('')
const schema = ref<JSONSchema | undefined>(undefined)
const schemaIsLoading = ref(false)
let atIndexForInsertion = -1
const sections = ref<SectionConfig[] | undefined>(undefined)
const wrapperName = ref<string | undefined>(undefined)
const innerSchema = ref<JSONSchema | undefined>(undefined)
const innerData = computed({
  get: () => {
    if (!wrapperName.value) return localData.value
    return (localData.value && localData.value[wrapperName.value]) || {}
  },
  set: (v: any) => {
    if (!wrapperName.value) { localData.value = v; return }
    localData.value = { ...(localData.value || {}), [wrapperName.value]: v }
  }
})

// AI Options (Model/Prompt/Response Model)
const aiOptions = ref<AIConfigOptions | null>(null)
async function loadAIOptions() { try { aiOptions.value = await getAIConfigOptions() } catch {} }

const projectName = 'Current Project'
const lastSavedAt = ref<string | undefined>(undefined)
const titleProxy = ref(props.card.title)
watch(() => props.card.title, v => titleProxy.value = v)
watch(titleProxy, v => localData.value = { ...localData.value, title: v })

const isDirty = computed(() => {
  // If custom content editor used, use its dirty state
  if (activeContentEditor.value) {
    return contentEditorDirty.value
  }
  // Default form editor uses data comparison
  return !isEqual(localData.value, originalData.value) || localAiContextTemplate.value !== originalAiContextTemplate.value
})

watch(
  () => props.card,
  async (newCard) => {
    if (newCard) {
      localData.value = cloneDeep(newCard.content) || {}
      localAiContextTemplate.value = newCard.ai_context_template || ''
      originalData.value = cloneDeep(newCard.content) || {}
      originalAiContextTemplate.value = newCard.ai_context_template || ''
      titleProxy.value = newCard.title
      await loadSchemaForCard(newCard)
      // Load per card params
      await loadAIOptions()
      // Prioritize reading effective params from backend
      try {
        const resp = await getCardAIParams(newCard.id)
        const eff = resp?.effective_params
        if (eff) editingParams.value = { ...eff }
      } catch {}
      if (!editingParams.value || Object.keys(editingParams.value).length === 0) {
        const preset = getPresetForType(newCard.card_type?.name) || {}
        editingParams.value = { ...preset }
      }
      if (!editingParams.value.llm_config_id) {
        const first = aiOptions.value?.llm_configs?.[0]
        if (first) editingParams.value.llm_config_id = first.id
      }
      // Local compat save
      perCardStore.setForCard(newCard.id, editingParams.value)
    }
  },
  { immediate: true, deep: true }
)

const perCardParams = computed(() => perCardStore.getByCardId(props.card.id))
const editingParams = ref<PerCardAIParams>({})

const selectedModelName = computed(() => {
  try {
    const id = (perCardParams.value || editingParams.value)?.llm_config_id
    const list = aiOptions.value?.llm_configs || []
    const found = list.find(m => m.id === id)
    return found?.display_name || (id != null ? String(id) : '')
  } catch { return '' }
})

const paramSummary = computed(() => {
  const p = perCardParams.value || editingParams.value
  const model = selectedModelName.value ? `Model:${selectedModelName.value}` : 'Model:Unset'
  const prompt = p?.prompt_name ? `Prompt:${p.prompt_name}` : 'Prompt:Unset'
  const t = p?.temperature != null ? `Temp:${p.temperature}` : ''
  const m = p?.max_tokens != null ? `MaxTokens:${p.max_tokens}` : ''
  return [model, prompt, t, m].filter(Boolean).join(' · ')
})

async function applyAndSavePerCardParams() {
  try {
    await updateCardAIParams(props.card.id, { ...editingParams.value })
    perCardStore.setForCard(props.card.id, { ...editingParams.value })
    ElMessage.success('Saved')
  } catch { ElMessage.error('Save failed') }
}

async function restoreParamsFollowType() {
  try {
    await updateCardAIParams(props.card.id, null)
    ElMessage.success('Restored follow type')
    const resp = await getCardAIParams(props.card.id)
    const eff = resp?.effective_params
    if (eff) editingParams.value = { ...eff }
  } catch { ElMessage.error('Operation failed') }
}

async function applyParamsToType() {
  try {
    // 1) Save current edit value to this card (as source)
    await updateCardAIParams(props.card.id, { ...editingParams.value })
    // 2) Apply to type
    await applyCardAIParamsToType(props.card.id)
    // Notify setting page refresh
    window.dispatchEvent(new Event('card-types-updated'))
    // 3) After applying to type, default let current card restore follow type, so params match top display immediately
    await updateCardAIParams(props.card.id, null)
    const resp = await getCardAIParams(props.card.id)
    const eff = resp?.effective_params
    if (eff) {
      editingParams.value = { ...eff }
      perCardStore.setForCard(props.card.id, { ...eff })
    }
    ElMessage.success('Applied to type, and restored this card follow type')
  } catch { ElMessage.error('Apply failed') }
}

function resetToPreset() {
  const preset = getPresetForType(props.card.card_type?.name) || {}
  if (!preset.llm_config_id) {
    const first = aiOptions.value?.llm_configs?.[0]
    if (first) preset.llm_config_id = first.id
  }
  editingParams.value = { ...preset }
  perCardStore.setForCard(props.card.id, editingParams.value)
}

function getPresetForType(typeName?: string) : PerCardAIParams | undefined {
  // Compat old preset: Provide simple default based on type name
  // Updated to use English names and prompts
  const map: Record<string, PerCardAIParams> = {
    'SpecialAbility': { prompt_name: 'SpecialAbilityGeneration', response_model_name: 'SpecialAbilityResponse', temperature: 0.6, max_tokens: 1024, timeout: 60 },
    'OneSentenceSummary': { prompt_name: 'OneSentenceSummary', response_model_name: 'OneSentence', temperature: 0.6, max_tokens: 1024, timeout: 60 },
    'StoryOutline': { prompt_name: 'StoryOutline', response_model_name: 'ParagraphOverview', temperature: 0.6, max_tokens: 2048, timeout: 60 },
    'WorldSetting': { prompt_name: 'WorldSetting', response_model_name: 'WorldBuilding', temperature: 0.6, max_tokens: 8192, timeout: 120 },
    'CoreBlueprint': { prompt_name: 'CoreBlueprint', response_model_name: 'Blueprint', temperature: 0.6, max_tokens: 8192, timeout: 120 },
    'VolumeOutline': { prompt_name: 'VolumeOutline', response_model_name: 'VolumeOutline', temperature: 0.6, max_tokens: 8192, timeout: 120 },
    'StageOutline': { prompt_name: 'StageOutline', response_model_name: 'StageLine', temperature: 0.6, max_tokens: 8192, timeout: 120 },
    'ChapterOutline': { prompt_name: 'ChapterOutline', response_model_name: 'ChapterOutline', temperature: 0.6, max_tokens: 4096, timeout: 60 },
    'WritingGuide': { prompt_name: 'WritingGuide', response_model_name: 'WritingGuide', temperature: 0.7, max_tokens: 8192, timeout: 60 },
    'Chapter': { prompt_name: 'ContentGeneration', temperature: 0.7, max_tokens: 8192, timeout: 60 },
  }
  return map[typeName || '']
}

async function loadSchemaForCard(card: CardRead) {
  schemaIsLoading.value = true
  try {
    // Prioritize reading schema from backend by type/instance
    try {
      const { getCardSchema } = await import('@renderer/api/setting')
      const resp = await getCardSchema(card.id)
      const effective = (resp?.effective_schema || resp?.json_schema)
      if (effective) {
        schema.value = effective
      }
    } catch {}
    if (!schema.value) {
      // Fallback: Use existing schemaService to avoid blank caused by null value in first migration
      const typeName = (card.card_type as any)?.name as string | undefined
      await schemaService.loadSchemas()
      if (!typeName) {
        schema.value = undefined
        sections.value = undefined
        wrapperName.value = undefined
        innerSchema.value = undefined
        return
      }
      schema.value = schemaService.getSchema(typeName)
      if (!schema.value) {
        await schemaService.refreshSchemas()
        schema.value = schemaService.getSchema(typeName)
      }
    }
    const props: any = (schema.value as any)?.properties || {}
    const keys = Object.keys(props)
    const onlyKey = keys.length === 1 ? keys[0] : undefined
    const isObject = onlyKey && (props[onlyKey]?.type === 'object' || props[onlyKey]?.$ref || props[onlyKey]?.anyOf)
    if (onlyKey && isObject) {
      wrapperName.value = onlyKey
      const maybeRef = props[onlyKey]
      if (maybeRef && typeof maybeRef === 'object' && '$ref' in maybeRef && typeof maybeRef.$ref === 'string') {
        const refName = maybeRef.$ref.split('/').pop() || ''
        const localDefs = (schema.value as any)?.$defs || {}
        innerSchema.value = localDefs[refName] || schemaService.getSchema(refName) || maybeRef
      } else {
        innerSchema.value = maybeRef
      }
    } else {
      wrapperName.value = undefined
      innerSchema.value = undefined
    }
    const schemaForLayout = (wrapperName.value ? innerSchema.value : schema.value) as any
    const schemaMeta = schemaForLayout?.['x-ui'] || undefined
    const backendLayout = (schemaForLayout?.['ui_layout'] || undefined)
    sections.value = mergeSections({ schemaMeta, backendLayout, frontendDefault: autoGroup(schemaForLayout) })
  } finally { schemaIsLoading.value = false }
}

function handleReferenceConfirm(reference: string) {
  if (atIndexForInsertion < 0) {
    // If not triggered by @, append to end
    localAiContextTemplate.value = `${localAiContextTemplate.value}${reference}`
    ElMessage.success('Reference inserted')
    return
  }
  const text = localAiContextTemplate.value
  const isAt = text.charAt(atIndexForInsertion) === '@'
  const before = text.substring(0, atIndexForInsertion)
  const after = text.substring(atIndexForInsertion + (isAt ? 1 : 0))
  localAiContextTemplate.value = before + reference + after
  atIndexForInsertion = -1
  ElMessage.success('Reference inserted')
}

function applyContextTemplate(text: string) {
  localAiContextTemplate.value = text
}

async function applyContextTemplateAndSave(text: string) {
  localAiContextTemplate.value = typeof text === 'string' ? text : String(text)
  ElMessage.success('Context template applied')
  openDrawer.value = false
  await handleSave()
}

// Alt+K Open Drawer
function keyHandler(e: KeyboardEvent) {
  if ((e.altKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
    e.preventDefault()
    openDrawer.value = true
  }
  if ((e.altKey || e.metaKey) && (e.key === 'j' || e.key === 'J')) {
    e.preventDefault()
    openAssistant()
  }
}

onMounted(() => { window.addEventListener('keydown', keyHandler) })
onBeforeUnmount(() => { window.removeEventListener('keydown', keyHandler) })

// Pop up selector when typing @ in drawer
let drawerTextarea: HTMLTextAreaElement | null = null
watch(() => openDrawer.value, (v) => {
  if (v) {
    nextTick(() => {
      drawerTextarea = document.querySelector('.context-area textarea') as HTMLTextAreaElement | null
      drawerTextarea?.addEventListener('input', handleDrawerInput)
    })
  } else {
    drawerTextarea?.removeEventListener('input', handleDrawerInput)
    drawerTextarea = null
    atIndexForInsertion = -1
  }
})

function handleDrawerInput(ev: Event) {
  const textarea = ev.target as HTMLTextAreaElement
  // Sync text in drawer to local template, avoid prefix loss when selector inserts
  localAiContextTemplate.value = textarea.value
  const cursorPos = textarea.selectionStart
  const lastChar = textarea.value.substring(cursorPos - 1, cursorPos)
  if (lastChar === '@') {
    atIndexForInsertion = cursorPos - 1
    isSelectorVisible.value = true
  }
}

function openSelectorFromDrawer() {
  const textarea = document.querySelector('.context-area textarea') as HTMLTextAreaElement | null
  if (textarea) {
    localAiContextTemplate.value = textarea.value
    // Insert at cursor current position, do not backspace
    atIndexForInsertion = textarea.selectionStart
  }
  isSelectorVisible.value = true
}

const previewText = computed(() => localAiContextTemplate.value)

async function handleSave() {
  // Custom content editor save logic (e.g. CodeMirrorEditor)
  if (activeContentEditor.value && contentEditorRef.value) {
    try {
      isSaving.value = true
      const savedContent = await contentEditorRef.value.handleSave()
      
      // Save context template (if changed)
      if (localAiContextTemplate.value !== props.card.ai_context_template) {
        await cardStore.modifyCard(props.card.id, {
          ai_context_template: localAiContextTemplate.value
        })
      }
      
      // Save history version
      try {
        if (projectStore.currentProject?.id && savedContent) {
          await addVersion(projectStore.currentProject.id, {
            cardId: props.card.id,
            projectId: projectStore.currentProject.id,
            title: titleProxy.value,
            content: savedContent,
            ai_context_template: localAiContextTemplate.value,
          })
        }
      } catch (e) {
        console.error('Failed to add version:', e)
      }
      
      contentEditorDirty.value = false
      originalAiContextTemplate.value = localAiContextTemplate.value
      lastSavedAt.value = new Date().toLocaleTimeString()
      ElMessage.success('Saved successfully')
    } catch (e) {
      ElMessage.error('Save failed')
    } finally {
      isSaving.value = false
    }
    return
  }
  
  // Default form editor save logic
  try {
    isSaving.value = true
    const updatePayload: CardUpdate = {
      title: titleProxy.value,
      content: cloneDeep(localData.value),
      ai_context_template: localAiContextTemplate.value,
    }
    await cardStore.modifyCard(props.card.id, updatePayload)
    try {
      await addVersion(projectStore.currentProject!.id!, {
        cardId: props.card.id,
        projectId: projectStore.currentProject!.id!,
        title: titleProxy.value,
        content: updatePayload.content as any,
        ai_context_template: localAiContextTemplate.value,
      })
    } catch {}
    originalData.value = cloneDeep(localData.value)
    originalAiContextTemplate.value = localAiContextTemplate.value
    lastSavedAt.value = new Date().toLocaleTimeString()
    ElMessage.success('Saved successfully!')
  } finally { isSaving.value = false }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(`Confirm delete card "${props.card.title}"? This action cannot be undone`, 'Delete Confirmation', { type: 'warning' })
    await cardStore.removeCard(props.card.id)
    ElMessage.success('Card deleted')
    const evt = new CustomEvent('nf:navigate', { detail: { to: 'market' } })
    window.dispatchEvent(evt)
  } catch (e) {
  }
}

async function handleGenerate() {
  const p = perCardStore.getByCardId(props.card.id) || editingParams.value
  if (!p?.llm_config_id) { ElMessage.error('Please set valid Model ID first'); return }
  const editingContent = wrapperName.value ? innerData.value : localData.value
  const currentCardForResolve = { ...props.card, content: editingContent }
  const resolvedContext = resolveTemplate({ template: localAiContextTemplate.value, cards: cards.value, currentCard: currentCardForResolve as any })
  try {
    // Read effective Schema directly and send as response_model_schema
    const { getCardSchema } = await import('@renderer/api/setting')
    const resp = await getCardSchema(props.card.id)
    const effective = resp?.effective_schema || resp?.json_schema
    if (!effective) { ElMessage.error('Structure (Schema) not found for this card.'); return }
    const sampling = { temperature: p.temperature, max_tokens: p.max_tokens, timeout: p.timeout }
    const result = await aiStore.generateContentWithSchema(effective as any, resolvedContext, p.llm_config_id!, p.prompt_name ?? undefined, sampling)
    if (result) {
      const { mergeWith, isArray } = await import('lodash-es')
      const arrayOverwrite = (objValue: any, srcValue: any) => {
        if (isArray(objValue) || isArray(srcValue)) {
          return srcValue
        }
        return undefined
      }
      if (wrapperName.value) {
        const mergedInner = mergeWith({}, innerData.value || {}, result, arrayOverwrite)
        innerData.value = mergedInner
      } else {
        const merged = mergeWith({}, localData.value || {}, result, arrayOverwrite)
        localData.value = merged
      }
      ElMessage.success('Content generation successful!')
    }
  } catch (e) { console.error('AI generation failed:', e) }
}

async function handleRestoreVersion(v: any) {
  showVersions.value = false
  
  // Custom content editor restore logic (e.g. CodeMirrorEditor)
  if (activeContentEditor.value && contentEditorRef.value) {
    try {
      ElMessage.success('Version restored, saving...')
      
      // Notify content editor to restore content (requires editor to implement restoreContent method)
      if (typeof contentEditorRef.value.restoreContent === 'function') {
        await contentEditorRef.value.restoreContent(v.content)
      }
      
      // Restore context template
      localAiContextTemplate.value = v.ai_context_template || localAiContextTemplate.value
      
      // Save restored content
      await handleSave()
      
      // Refresh card data
      await cardStore.fetchCards(projectStore.currentProject!.id!)
      
      ElMessage.success('Version restored and saved')
    } catch (e) {
      console.error('Failed to restore content editor version:', e)
      ElMessage.error('Restore failed')
    }
    return
  }
  
  // Default form editor restore logic
  if (wrapperName.value) innerData.value = v.content
  else localData.value = v.content
  localAiContextTemplate.value = v.ai_context_template || localAiContextTemplate.value
  ElMessage.success('Version restored, saving...')
  await handleSave()
}

async function onSchemaSaved() {
  // Refresh schema and recalculate sections after saving structure
  await loadSchemaForCard(props.card)
}

async function handleAssistantFinalize(summary: string) {
  try {
    const p = perCardStore.getByCardId(props.card.id) || editingParams.value
    if (!p?.llm_config_id) { ElMessage.error('Please set valid Model ID first'); return }
    // Merge dialogue summary and context as input text (no longer append card prompt template)
    const editingContent = wrapperName.value ? innerData.value : localData.value
    const currentCardForResolve = { ...props.card, content: editingContent }
    const resolvedContextText = resolveTemplate({ template: localAiContextTemplate.value, cards: cards.value, currentCard: currentCardForResolve as any })
    const inputText = `${resolvedContextText}\n\n[Conversation Summary]\n${summary}`
    // Read effective Schema
    const { getCardSchema } = await import('@renderer/api/setting')
    const resp = await getCardSchema(props.card.id)
    const effective = resp?.effective_schema || resp?.json_schema
    if (!effective) { ElMessage.error('Structure (Schema) not found for this card.'); return }
    const sampling = { temperature: p.temperature, max_tokens: p.max_tokens, timeout: p.timeout }
    const result = await aiStore.generateContentWithSchema(effective as any, inputText, p.llm_config_id!, p.prompt_name ?? undefined, sampling)
    if (result) {
      const { mergeWith, isArray } = await import('lodash-es')
      const arrayOverwrite = (objValue: any, srcValue: any) => {
        if (isArray(objValue) || isArray(srcValue)) {
          return srcValue
        }
        return undefined
      }
      if (wrapperName.value) {
        const mergedInner = mergeWith({}, innerData.value || {}, result, arrayOverwrite)
        innerData.value = mergedInner
      } else {
        const merged = mergeWith({}, localData.value || {}, result, arrayOverwrite)
        localData.value = merged
      }
      assistantVisible.value = false
      ElMessage.success('Finalization generation completed!')
    }
  } catch (e) { console.error('Finalize generate failed:', e) }
}
</script>

<style scoped>
.generic-card-editor { 
  display: flex; 
  flex-direction: column; 
  height: 100%; 
  overflow: hidden; /* Prevent overall scroll */
}

/* Ensure custom content editor (e.g. CodeMirrorEditor) takes remaining space */
.generic-card-editor > :deep(.chapter-studio),
.generic-card-editor > :deep([class*="-editor"]) {
  flex: 1;
  min-height: 0;
}

.editor-body { display: grid; grid-template-columns: 1fr; gap: 0; flex: 1; overflow: hidden; }
.main-pane { overflow: auto; padding: 12px; }
.form-container { display: flex; flex-direction: column; gap: 12px; }
.loading-or-error-container { text-align: center; padding: 2rem; color: var(--el-text-color-secondary); }
.toolbar-row { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--el-border-color-light); }
.param-toolbar { padding: 6px 12px; border-bottom: 1px solid var(--el-border-color-light); justify-content: flex-end; }
.param-inline { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ai-config-form { padding: 4px 2px; }
/* Fixed button width and truncate model name */
:deep(.model-trigger) { width: 230px; min-width: 220px; max-width: 260px; box-sizing: border-box; }
:deep(.model-trigger .el-button__content) { width: 100%; display: inline-flex; align-items: center; gap: 4px; overflow: hidden; }
.model-label { flex: 0 0 auto; }
.model-name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-actions { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; flex-wrap: wrap; }
.ai-actions .left, .ai-actions .right { display: flex; gap: 6px; align-items: center; }
</style>
