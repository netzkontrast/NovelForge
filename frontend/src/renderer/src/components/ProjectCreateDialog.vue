
<template>
  <el-dialog v-model="visible" :title="dialogTitle" width="500" >
    <el-form :model="form" ref="formRef" :rules="rules" label-width="120px" @submit.prevent="handleConfirm">
      <el-form-item label="Project Name" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="Description" prop="description">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item v-if="!isEditMode" label="Project Template">
        <el-select v-model="selectedWorkflowId" placeholder="Select Init Workflow (Type: onprojectcreate)" filterable clearable :loading="loadingWorkflows" style="width:100%">
          <el-option v-for="wf in initWorkflows" :key="wf.id" :label="wf.name" :value="wf.id" />
        </el-select>
      </el-form-item>
      <!-- Hidden submit button to trigger form submit on enter -->
      <button type="submit" style="display:none"></button>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">Cancel</el-button>
        <el-button type="primary" @click="handleConfirm">Confirm</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { components } from '@renderer/types/generated'
import { listWorkflowTriggers, listWorkflows, type WorkflowRead, type WorkflowTriggerRead } from '@renderer/api/workflows'

type Project = components['schemas']['ProjectRead']
type ProjectCreate = components['schemas']['ProjectCreate']
type ProjectUpdate = components['schemas']['ProjectUpdate']


const visible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive<ProjectCreate | ProjectUpdate>({
  name: '',
  description: ''
})
const editingProject = ref<Project | null>(null)

// Workflow Mode
const selectedWorkflowId = ref<number | null>(null)
const initWorkflows = ref<WorkflowRead[]>([])
const loadingWorkflows = ref(false)

const isEditMode = computed(() => !!editingProject.value)
const dialogTitle = computed(() => isEditMode.value ? 'Edit Project' : 'New Project')

const rules = reactive<FormRules>({
  name: [{ required: true, message: 'Please enter project name', trigger: 'blur' }]
})

const emit = defineEmits(['create', 'update'])


async function loadInitWorkflows() {
  try {
    loadingWorkflows.value = true
    // Filter triggers for onprojectcreate, then map to workflows
    const triggers = await listWorkflowTriggers()
    const ids = Array.from(new Set(triggers.filter(t=>t.trigger_on==='onprojectcreate').map(t=>t.workflow_id)))
    if (ids.length) {
      const all = await listWorkflows()
      initWorkflows.value = all.filter(w => ids.includes(w.id))
      selectedWorkflowId.value = initWorkflows.value[0]?.id ?? null
    } else {
      initWorkflows.value = []
      selectedWorkflowId.value = null
    }
  } finally {
    loadingWorkflows.value = false
  }
}

function open(project: Project | null = null) {
  visible.value = true
  editingProject.value = project
  
  nextTick(() => {
    formRef.value?.resetFields()
    if (project) {
      form.name = project.name
      form.description = project.description || ''
    } else {
      form.name = ''
      form.description = ''
      // Reload workflows (ensure latest)
      loadInitWorkflows()
    }
  })
}

function handleConfirm() {
  formRef.value?.validate((valid) => {
    if (valid) {
      if (isEditMode.value && editingProject.value) {
        emit('update', editingProject.value.id, { ...form })
      } else {
        const payload: any = { ...form }
        if (selectedWorkflowId.value) payload.workflow_id = selectedWorkflowId.value
        emit('create', payload)
      }
      visible.value = false
    } else {
      ElMessage.error('Please fill in required fields')
    }
  })
}

// Expose open method to parent
defineExpose({
  open
})
// 样式
</script>

<style scoped>
.mode-switch { margin-bottom: 8px; }
.selector-block { width: 100%; }
</style>