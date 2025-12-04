<template>
  <el-dialog v-model="visible" title="History Versions" width="800px" append-to-body destroy-on-close>
    <div class="versions-container" v-loading="loading">
      <div v-if="versions.length === 0 && !loading" class="empty-tip">
        <el-empty description="No history versions" />
      </div>
      <div v-else class="version-list">
        <el-table :data="versions" style="width: 100%" height="400px">
          <el-table-column prop="created_at" label="Creation Time" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="word_count" label="Word Count" width="100" />
          <el-table-column prop="title" label="Title" show-overflow-tooltip />
          <el-table-column label="Action" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="previewVersion(row)">Details</el-button>
              <el-button type="warning" link size="small" @click="handleRestore(row)">Restore</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Preview Dialog -->
    <el-dialog v-model="previewVisible" title="Version Details" width="600px" append-to-body>
      <div class="version-preview">
        <div class="preview-meta">
          <p><strong>Title:</strong> {{ previewData?.title }}</p>
          <p><strong>Time:</strong> {{ formatTime(previewData?.created_at) }}</p>
        </div>
        <el-divider>Content</el-divider>
        <div class="preview-content">
          <pre>{{ formatContent(previewData?.content) }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">Close</el-button>
        <el-button type="primary" @click="handleRestore(previewData!)">Restore</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { getVersions } from '@renderer/services/versionService'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const props = defineProps<{
  modelValue: boolean
  projectId: number
  cardId: number
}>()

const emit = defineEmits(['update:modelValue', 'restore'])

const visible = ref(props.modelValue)
watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) loadVersions()
})
watch(visible, (val) => emit('update:modelValue', val))

const loading = ref(false)
const versions = ref<any[]>([])
const previewVisible = ref(false)
const previewData = ref<any>(null)

async function loadVersions() {
  try {
    loading.value = true
    const list = await getVersions(props.projectId, props.cardId)
    // Sort by time desc
    versions.value = list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  } catch (e) {
    ElMessage.error('Failed to load versions')
  } finally {
    loading.value = false
  }
}

function formatTime(t: string) {
  return dayjs(t).format('YYYY-MM-DD HH:mm:ss')
}

function formatContent(content: any) {
  if (typeof content === 'string') return content
  return JSON.stringify(content, null, 2)
}

function previewVersion(row: any) {
  previewData.value = row
  previewVisible.value = true
}

async function handleRestore(row: any) {
  try {
    await ElMessageBox.confirm('Confirm restore this version? Current content will be overwritten.', 'Restore Confirmation', {
      confirmButtonText: 'Restore',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    emit('restore', row)
    previewVisible.value = false
    visible.value = false
  } catch {}
}
</script>

<style scoped>
.versions-container { padding: 10px; }
.preview-content { max-height: 400px; overflow: auto; background: var(--el-fill-color-light); padding: 10px; border-radius: 4px; }
.preview-content pre { white-space: pre-wrap; margin: 0; font-family: inherit; font-size: 13px; }
</style>
