<template>
  <div class="card-market">
    <div class="market-header">
      <CardFilterBar @filter="handleFilter" />
      <div class="market-stats">Total {{ filteredCards.length }} Cards</div>
    </div>
    <div class="market-grid" v-if="filteredCards.length">
      <div v-for="card in filteredCards" :key="card.id" class="market-card" @click="$emit('edit-card', card.id)">
        <div class="card-cover" :class="getCoverClass(card.title)">
          <div class="card-type-tag">{{ card.card_type?.name }}</div>
          <div class="card-initial">{{ getInitial(card.title) }}</div>
        </div>
        <div class="card-info">
          <div class="card-title" :title="card.title">{{ card.title }}</div>
          <div class="card-meta">
            <span class="meta-item"><el-icon><Clock /></el-icon>{{ formatTime(card.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
    <el-empty v-else description="No matching cards found" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCardStore } from '@renderer/stores/useCardStore'
import { storeToRefs } from 'pinia'
import { Clock } from '@element-plus/icons-vue'
import CardFilterBar from './CardFilterBar.vue'
import dayjs from 'dayjs'

const cardStore = useCardStore()
const { cards } = storeToRefs(cardStore)

const filterState = ref({ search: '', typeId: undefined as number | undefined, sort: 'created_desc' })

function handleFilter(state: any) {
  filterState.value = state
}

const filteredCards = computed(() => {
  let list = cards.value.slice()
  const { search, typeId, sort } = filterState.value

  if (search) {
    const q = search.toLowerCase()
    list = list.filter(c =>
      c.title.toLowerCase().includes(q) ||
      JSON.stringify(c.content).toLowerCase().includes(q)
    )
  }

  if (typeId) {
    list = list.filter(c => c.card_type?.id === typeId)
  }

  if (sort === 'created_desc') list.sort((a, b) => dayjs(b.created_at).valueOf() - dayjs(a.created_at).valueOf())
  if (sort === 'created_asc') list.sort((a, b) => dayjs(a.created_at).valueOf() - dayjs(b.created_at).valueOf())
  if (sort === 'title_asc') list.sort((a, b) => a.title.localeCompare(b.title))

  return list
})

function formatTime(t: string) {
  return dayjs(t).format('YYYY-MM-DD')
}

function getInitial(name: string) {
  return name ? name.charAt(0).toUpperCase() : '?'
}

function getCoverClass(name: string) {
  const palettes = ['g1','g2','g3','g4','g5','g6']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  return 'cover-' + palettes[hash % palettes.length]
}
</script>

<style scoped>
.card-market { padding: 12px; height: 100%; display: flex; flex-direction: column; }
.market-header { margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.market-stats { font-size: 13px; color: var(--el-text-color-secondary); white-space: nowrap; }
.market-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; overflow-y: auto; padding-bottom: 20px; }
.market-card { background: var(--el-bg-color); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05); cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; height: 240px; border: 1px solid var(--el-border-color-lighter); }
.market-card:hover { transform: translateY(-4px); box-shadow: 0 4px 16px 0 rgba(0,0,0,0.1); border-color: var(--el-color-primary-light-5); }
.card-cover { height: 140px; display: flex; align-items: center; justify-content: center; position: relative; color: #fff; font-weight: bold; font-size: 48px; }
.card-type-tag { position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; font-size: 12px; backdrop-filter: blur(4px); }
.card-initial { text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
.cover-g1 { background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%); }
.cover-g2 { background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); }
.cover-g3 { background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%); }
.cover-g4 { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.cover-g5 { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.cover-g6 { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
.card-info { padding: 12px; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
.card-title { font-size: 15px; font-weight: 600; color: var(--el-text-color-primary); margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.4; }
.card-meta { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--el-text-color-secondary); }
.meta-item { display: flex; align-items: center; gap: 4px; }
</style>
