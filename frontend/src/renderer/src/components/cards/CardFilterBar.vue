<template>
  <div class="filter-bar">
    <el-input v-model="searchQuery" placeholder="Search Cards (Match by Title/Content)" clearable @input="handleSearch" class="search-input">
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>
    <el-select v-model="selectedType" placeholder="Filter by Type" clearable @change="handleTypeChange" class="type-select">
      <el-option v-for="t in types" :key="t.id" :label="t.name" :value="t.id" />
    </el-select>
    <el-select v-model="sortOrder" placeholder="Sort" @change="handleSortChange" class="sort-select">
      <el-option label="Creation Time (New->Old)" value="created_desc" />
      <el-option label="Creation Time (Old->New)" value="created_asc" />
      <el-option label="Title A->Z" value="title_asc" />
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useCardStore } from '@renderer/stores/useCardStore'
import { storeToRefs } from 'pinia'

const emit = defineEmits(['filter'])
const cardStore = useCardStore()
const { cardTypes } = storeToRefs(cardStore)

const searchQuery = ref('')
const selectedType = ref<number | undefined>(undefined)
const sortOrder = ref('created_desc')

const types = cardTypes

function handleSearch() {
  emitFilter()
}

function handleTypeChange() {
  emitFilter()
}

function handleSortChange() {
  emitFilter()
}

function emitFilter() {
  emit('filter', {
    search: searchQuery.value,
    typeId: selectedType.value,
    sort: sortOrder.value
  })
}

onMounted(() => {
  cardStore.fetchCardTypes()
})
</script>

<style scoped>
.filter-bar { display: flex; gap: 12px; align-items: center; width: 100%; flex-wrap: wrap; }
.search-input { flex: 1; min-width: 200px; }
.type-select { width: 160px; }
.sort-select { width: 180px; }
</style>
