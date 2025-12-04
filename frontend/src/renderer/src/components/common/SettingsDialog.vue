<script setup lang="ts">
import { ref } from 'vue'
import LLMConfigManager from '../setting/LLMConfigManager.vue'
// import Versions from '../Versions.vue'
import PromptWorkshop from '../setting/PromptWorkshop.vue'
import CardTypeManager from '../setting/CardTypeManager.vue'
import KnowledgeManager from '../setting/KnowledgeManager.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; 'close': [] }>()

const activeTab = ref('llm')
// Read global store preset initial tab
import { useAppStore } from '@renderer/stores/useAppStore'
const appStore = useAppStore()
activeTab.value = appStore.settingsInitialTab || 'llm'

function handleClose() {
  emit('update:modelValue', false)
  emit('close')
}

// Refresh child component when switch to LLM tab or first show
import { onMounted, watch, nextTick } from 'vue'
const llmManagerRef = ref()
function emitRefreshIfLLM() {
  if (activeTab.value === 'llm' && llmManagerRef.value?.refresh) {
    llmManagerRef.value.refresh()
  }
}
onMounted(() => emitRefreshIfLLM())
watch(() => activeTab.value, () => emitRefreshIfLLM())
// Refresh dialog every time open (wait for child render)
watch(() => props.modelValue, async (open) => { if (open) { await nextTick(); emitRefreshIfLLM() } })
</script>

<template>
  <el-dialog 
    :model-value="modelValue" 
    @update:model-value="(val) => emit('update:modelValue', val)"
    title="Application Settings"
    width="85%" 
    top="4vh"
    @close="handleClose"
  >
    <div class="settings-container">
      <el-tabs v-model="activeTab" tab-position="left" class="settings-tabs">
        <el-tab-pane label="LLM Config" name="llm">
          <LLMConfigManager ref="llmManagerRef" />
        </el-tab-pane>
        <el-tab-pane label="Knowledge Base" name="knowledge">
          <KnowledgeManager />
        </el-tab-pane>
        <el-tab-pane label="Prompt Workshop" name="prompts">
          <PromptWorkshop />
        </el-tab-pane>
        <el-tab-pane label="Card Types" name="card-types">
          <CardTypeManager />
        </el-tab-pane>
        <!-- <el-tab-pane label="About" name="about">
          <Versions />
        </el-tab-pane> -->
      </el-tabs>
    </div>
  </el-dialog>
</template>

<style scoped>
.settings-container { height: 78vh; }
.settings-tabs { height: 100%; }
:deep(.el-dialog__body) { padding-top: 8px; }
:deep(.el-tabs__content) { height: 100%; overflow-y: auto; }
</style>
