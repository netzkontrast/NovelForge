<template>
  <el-drawer
    v-model="visible"
    title="Context Injection"
    direction="rtl"
    size="500px"
  >
    <div class="drawer-wrapper">
      <slot name="params"></slot>
      <div class="section">
        <div class="drawer-header">
          <span>Template (Supports @ referencing cards)</span>
        </div>
        <el-input
          v-model="aiContext"
          type="textarea"
          :rows="10"
          placeholder="e.g.: Word Setting: @WorldSetting.content"
          class="context-area"
        />
        <div class="chips">
          <el-tag v-for="t in tokens" :key="t" closable @close="removeToken(t)" size="small">@{{ t }}</el-tag>
        </div>
      </div>

      <div class="section" style="flex:1; overflow:hidden; display:flex; flex-direction:column;">
        <div class="drawer-header">
          <span>Live Preview</span>
        </div>
        <el-input
          type="textarea"
          :model-value="previewText"
          readonly
          resize="none"
          style="flex:1;"
          input-style="height:100%;"
        />
      </div>

      <div class="footer">
        <div class="actions">
          <el-button type="primary" @click="apply">Apply to Card</el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useCardStore } from '@renderer/stores/useCardStore'
import { storeToRefs } from 'pinia'
import { unwrapChapterOutline, extractParticipantsFrom } from '@renderer/services/contextHelpers'

const props = defineProps<{
  modelValue: boolean
  contextTemplate: string
  previewText?: string
}>()
const emit = defineEmits(['update:modelValue','apply-context','open-selector'])

const visible = ref(props.modelValue)
watch(() => props.modelValue, v => visible.value = v)
watch(visible, v => emit('update:modelValue', v))

const aiContext = ref(props.contextTemplate)
watch(() => props.contextTemplate, v => aiContext.value = v)

const tokenRegex = /@([^\s]+)/g
const tokens = computed(() => {
  const out: string[] = []
  const text = aiContext.value || ''
  let m: RegExpExecArray | null
  while ((m = tokenRegex.exec(text))) out.push(m[1])
  return out
})

function removeToken(token: string) {
  const full = '@' + token
  aiContext.value = (aiContext.value || '').split(full).join('')
}

function apply() { emit('apply-context', aiContext.value) }

// Pop up selector when typing @ in drawer
const cardStore = useCardStore()
const { activeCard } = storeToRefs(cardStore)
let drawerTextarea: HTMLTextAreaElement | null = null
watch(() => visible.value, (v) => {
  if (v) {
    setTimeout(() => {
      drawerTextarea = document.querySelector('.context-area textarea') as HTMLTextAreaElement | null
      drawerTextarea?.addEventListener('input', handleDrawerInput)
    }, 0)
  } else {
    drawerTextarea?.removeEventListener('input', handleDrawerInput)
    drawerTextarea = null
  }
})

function handleDrawerInput(ev: Event) {
  const textarea = ev.target as HTMLTextAreaElement
  const cursorPos = textarea.selectionStart
  const lastChar = textarea.value.substring(cursorPos - 1, cursorPos)
  if (lastChar === '@') {
    emit('open-selector', textarea.value)
  }
}
</script>

<style scoped>
.drawer-wrapper { display: flex; flex-direction: column; gap: 16px; height: 100%; }
.drawer-header { display: flex; justify-content: space-between; align-items: center; }
.section { display: flex; flex-direction: column; gap: 8px; }
.context-area { width: 100%; }
.actions { display: flex; gap: 8px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
