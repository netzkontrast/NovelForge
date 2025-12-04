<template>
  <div class="editor-header">
    <div class="left">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item>{{ projectName }}</el-breadcrumb-item>
        <el-breadcrumb-item>{{ cardType }}</el-breadcrumb-item>
        <el-breadcrumb-item>
          <el-input v-model="titleProxy" size="small" class="title-input" />
        </el-breadcrumb-item>
      </el-breadcrumb>
      <el-tag :type="statusTag.type" size="small">{{ statusTag.label }}</el-tag>
      <span v-if="lastSavedAt" class="last-saved">Last saved: {{ lastSavedAt }}</span>
    </div>
    <div class="right">
      <el-tooltip content="Open Context Drawer (Alt+K)">
        <el-button type="primary" plain @click="$emit('open-context')">Context Injection</el-button>
      </el-tooltip>
      <el-button v-if="!isChapterContent" type="success" plain @click="$emit('generate')">AI Generate</el-button>
      <el-button type="primary" :disabled="!canSave" :loading="saving" @click="$emit('save')">Save</el-button>
      <el-dropdown>
        <el-button text>More</el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="$emit('open-versions')">History Versions</el-dropdown-item>
            <el-dropdown-item divided type="danger" @click="$emit('delete')">Delete</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'

const props = defineProps<{
  projectName?: string
  cardType: string
  title: string
  dirty: boolean
  saving: boolean
  lastSavedAt?: string
  canSave?: boolean
  isChapterContent?: boolean
}>()

const emit = defineEmits(['update:title','save','generate','open-versions','delete','open-context'])

const titleProxy = ref(props.title)
watch(() => props.title, v => titleProxy.value = v)
watch(titleProxy, v => emit('update:title', v))

const statusTag = computed(() => {
  if (props.saving) return { type: 'warning', label: 'Saving' }
  if (props.dirty) return { type: 'info', label: 'Unsaved' }
  return { type: 'success', label: 'Saved' }
})
</script>

<style scoped>
.editor-header { 
  display: flex; 
  align-items: center; 
  justify-content: space-between; 
  padding: 8px 12px; 
  border-bottom: 1px solid var(--el-border-color-light); 
  background: var(--el-bg-color);
  flex-shrink: 0; /* Fixed: prevent shrinking */
}
.left { display: flex; align-items: center; gap: 10px; }
.right { display: flex; align-items: center; gap: 8px; }
.title-input { width: 280px; }
.last-saved { color: var(--el-text-color-secondary); font-size: 12px; }
</style>
