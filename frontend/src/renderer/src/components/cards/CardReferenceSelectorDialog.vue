<template>
  <el-dialog v-model="visible" title="Insert Reference" width="600" append-to-body>
    <div class="ref-toolbar">
      <el-input v-model="search" placeholder="Search card title..." clearable>
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>
    <div class="ref-list">
      <div v-for="c in filtered" :key="c.id" class="ref-item" @click="select(c)">
        <span class="ref-tag">{{ c.card_type?.name || 'Card' }}</span>
        <span class="ref-title">{{ c.title }}</span>
      </div>
      <div v-if="!filtered.length" class="empty-tip">No matching cards</div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useCardStore } from '@renderer/stores/useCardStore'
import { storeToRefs } from 'pinia'

const visible = ref(false)
const search = ref('')
const emit = defineEmits(['select'])

const cardStore = useCardStore()
const { cards } = storeToRefs(cardStore)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return cards.value.slice(0, 20)
  return cards.value.filter(c => c.title.toLowerCase().includes(q)).slice(0, 20)
})

function open() {
  search.value = ''
  visible.value = true
}

function select(c: any) {
  emit('select', c)
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.ref-toolbar { margin-bottom: 12px; }
.ref-list { max-height: 400px; overflow-y: auto; border: 1px solid var(--el-border-color-light); border-radius: 4px; }
.ref-item { display: flex; align-items: center; padding: 8px 12px; cursor: pointer; border-bottom: 1px solid var(--el-border-color-lighter); gap: 8px; }
.ref-item:hover { background: var(--el-fill-color-light); }
.ref-tag { font-size: 12px; background: var(--el-fill-color); padding: 2px 6px; border-radius: 4px; color: var(--el-text-color-secondary); }
.ref-title { font-size: 14px; font-weight: 500; color: var(--el-text-color-primary); }
.empty-tip { padding: 20px; text-align: center; color: var(--el-text-color-secondary); }
</style>
