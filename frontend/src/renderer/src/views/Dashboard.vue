<template>
  <div class="dashboard-container">
    <!-- 顶部横幅：视觉层级 + 关键信息与CTA -->
    <section class="dashboard-hero">
      <div class="hero-text">
        <h1>My Bookshelf</h1>
        <p class="subtitle">Gather your worlds and stories, start every inspiration from here</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="handleOpenCreateDialog" size="large" class="hero-cta">
        Start Creating
      </el-button>
    </section>

    <!-- Toolbar: Search + Sort -->
    <div class="toolbar">
      <el-input v-model="searchQuery" placeholder="Search Projects (Match by Name/Description)" clearable class="search-input" />
      <el-select v-model="sortKey" class="sort-select" size="default">
        <el-option label="By Creation Time (Newest First)" value="created-desc" />
        <el-option label="By Creation Time (Oldest First)" value="created-asc" />
        <el-option label="By Name A→Z" value="name-asc" />
        <el-option label="By Name Z→A" value="name-desc" />
      </el-select>
    </div>

    <main class="dashboard-main" v-loading="isLoading">
      <el-empty v-if="displayProjects.length === 0" description="No matching projects, try creating one!">
        <el-button type="primary" :icon="Plus" @click="handleOpenCreateDialog">New Project</el-button>
      </el-empty>
      <el-row :gutter="20" v-else>
        <el-col :xs="24" :sm="12" :md="8" :lg="6" :xl="6" v-for="project in displayProjects" :key="project.id">
          <el-card class="project-card showcase" shadow="hover" @click="handleProjectSelect(project)">
            <!-- Cover: Gradient + Initial Identifier, making card more recognizable -->
            <div class="card-cover" :class="getCoverClass(project.name)">
              <span class="cover-initial">{{ getInitial(project.name) }}</span>
            </div>
            <div class="card-content">
              <div class="title-row">
                <h3 class="title" :title="project.name">{{ project.name }}</h3>
                <!-- Hover visible actions: Avoid info noise -->
                <div class="card-actions" @click.stop>
                  <el-tooltip content="Edit"><el-button :icon="Edit" circle plain size="small" @click="handleProjectEdit(project)" /></el-tooltip>
                  <el-tooltip content="Delete"><el-button :icon="Delete" circle plain type="danger" size="small" @click="handleProjectDelete(project)" /></el-tooltip>
                </div>
              </div>
              <p class="desc" :title="project.description || 'No Description'">{{ project.description || 'No Description' }}</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </main>
    <ProjectCreateDialog ref="createDialogRef" @create="handleProjectCreate" @update="handleProjectUpdate" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit } from '@element-plus/icons-vue'
import { storeToRefs } from 'pinia'
import type { components } from '@renderer/types/generated'
import ProjectCreateDialog from '@renderer/components/ProjectCreateDialog.vue'
import { useProjectListStore } from '@renderer/stores/useProjectListStore'

// 类型别名
type Project = components['schemas']['ProjectRead']

const projectListStore = useProjectListStore()
const { projects, isLoading } = storeToRefs(projectListStore)

const createDialogRef = ref<InstanceType<typeof ProjectCreateDialog>>()
const emit = defineEmits(['project-selected'])

// Search and Sort (Frontend only, interface not changed)
const searchQuery = ref('')
// Note: Backend Project does not provide created_at field, using id increment as approximate "Creation Time" sort
type SortKey = 'created-desc' | 'created-asc' | 'name-asc' | 'name-desc'
const sortKey = ref<SortKey>('created-desc')

const displayProjects = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  let data = projects.value.slice()
  // Hide system reserved project
  data = data.filter(p => (p.name || '') !== '__free__')
  if (q) {
    data = data.filter(p => (p.name || '').toLowerCase().includes(q) || (p.description || '').toLowerCase().includes(q))
  }
  if (sortKey.value === 'created-desc') data.sort((a, b) => b.id - a.id)
  if (sortKey.value === 'created-asc') data.sort((a, b) => a.id - b.id)
  if (sortKey.value === 'name-asc') data.sort((a, b) => a.name.localeCompare(b.name))
  if (sortKey.value === 'name-desc') data.sort((a, b) => b.name.localeCompare(a.name))
  return data
})

function handleOpenCreateDialog() {
  createDialogRef.value?.open()
}

async function handleProjectCreate(projectData: any) {
  try {
    await projectListStore.createProject(projectData)
  } catch (error) {
    // 错误已在store中处理
  }
}

function handleProjectEdit(project: Project) {
  if ((project.name || '') === '__free__') return
  createDialogRef.value?.open(project)
}

async function handleProjectUpdate(projectId: number, projectData: any) {
  try {
    await projectListStore.updateProject(projectId, projectData)
  } catch (error) {
    // 错误已在store中处理
  }
}

async function handleProjectDelete(project: Project) {
  try {
    if ((project.name || '') === '__free__') return
    await ElMessageBox.confirm(
      `Are you sure you want to delete project "${project.name}"? This action will permanently delete this project and all its contents, and cannot be recovered.`,
      'Warning',
      {
        confirmButtonText: 'Confirm Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    await projectListStore.deleteProject(project.id)
  } catch (error) {
    if (error !== 'cancel') {
      // 错误已在store中处理
    }
  }
}

function handleProjectSelect(project: Project) {
  emit('project-selected', project)
}

onMounted(() => {
  projectListStore.fetchProjects()
})

// Calculate initial (Take first char for Chinese), used for cover logo
function getInitial(name: string) {
  if (!name) return 'N'
  const ch = name.trim().charAt(0)
  return ch.toUpperCase()
}

// Hash map name to fixed gradient set, ensuring consistent visual for same name projects
function getCoverClass(name: string) {
  const palettes = ['g1','g2','g3','g4','g5','g6']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  return 'cover-' + palettes[hash % palettes.length]
}
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  /* Let container fill parent main area, not viewport height, avoid scrollbar with top Header height */
  min-height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
}

/* Top Hero: Visual Hierarchy + Key Info and CTA */
.dashboard-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  /* Gradient softer, ensure title readability */
  background: linear-gradient(135deg, var(--el-color-primary-light-8), var(--el-fill-color-light) 65%);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  margin-bottom: 14px;
}
.hero-text h1 { margin: 0; font-size: 22px; color: var(--el-text-color-primary); text-shadow: 0 1px 0 rgba(255,255,255,.4); }
.subtitle { margin: 4px 0 0; color: var(--el-text-color-secondary); font-size: 13px; text-shadow: 0 1px 0 rgba(255,255,255,.35); }
.hero-cta { white-space: nowrap; }

/* Toolbar: Search + Sort */
.toolbar {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 16px;
}
.search-input { width: 320px; max-width: 60vw; }
/* Sort select widened, avoid label truncation */
.sort-select { width: 240px; max-width: 50vw; }

/* Main area height not forced to fill viewport, controlled by parent scroll */
.dashboard-main { min-height: auto; }

/* Card: Cover + Content Area + Hover Actions */
.project-card { margin-bottom: 20px; cursor: pointer; transition: transform .18s ease, box-shadow .18s ease; overflow: hidden; }
.project-card:hover { transform: translateY(-3px); }

.card-cover { height: 120px; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 28px; letter-spacing: 1px; }
.cover-initial { text-shadow: 0 1px 2px rgba(0,0,0,.25); }

/* Six groups of fixed gradients, visual clean and high distinction */
.cover-g1 { background: linear-gradient(135deg, #8E9EAB, #EEF2F3); color: #2c3e50; }
.cover-g2 { background: linear-gradient(135deg, #74ebd5, #ACB6E5); }
.cover-g3 { background: linear-gradient(135deg, #f6d365, #fda085); }
.cover-g4 { background: linear-gradient(135deg, #a18cd1, #fbc2eb); }
.cover-g5 { background: linear-gradient(135deg, #84fab0, #8fd3f4); }
.cover-g6 { background: linear-gradient(135deg, #f5576c, #f093fb); }

.card-content { padding: 10px 12px 12px; position: relative; }
.title-row { display: flex; align-items: center; gap: 8px; }
.title { margin: 0; font-size: 16px; font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.desc { margin: 6px 0 0; color: var(--el-text-color-regular); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 42px; }

/* Hover actions: Default transparent, visible on hover */
.card-actions { display: flex; gap: 6px; opacity: 0; transition: opacity .18s ease; }
.project-card:hover .card-actions { opacity: 1; }

@media (max-width: 768px) {
  .search-input { width: 100%; max-width: 100%; }
  .sort-select { width: 100%; max-width: 100%; }
}
</style> 