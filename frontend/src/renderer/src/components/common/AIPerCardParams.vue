<template>
	<div class="ai-param-inline">
		<el-popover placement="bottom" trigger="manual" v-model:visible="visible" width="360">
			<template #reference>
				<el-button type="primary" size="small" class="model-trigger" @click="visible = !visible">
					<template #icon>
						<el-icon><Setting /></el-icon>
					</template>
					<span class="model-label">Model:</span>
					<span class="model-name">{{ selectedModelName || 'Unset' }}</span>
				</el-button>
			</template>
			<div class="ai-config-form">
				<el-form label-width="92px" size="small">
					<el-form-item label="Model ID">
						<el-select v-model="editing.llm_config_id" placeholder="Select Model" style="width: 240px;" :teleported="false">
							<el-option v-for="m in (aiOptions?.llm_configs || [])" :key="m.id" :label="m.display_name || String(m.id)" :value="Number(m.id)" />
						</el-select>
					</el-form-item>
					<el-form-item label="Prompt">
						<el-select v-model="editing.prompt_name" placeholder="Select Prompt" filterable style="width: 240px;" :teleported="false">
							<el-option v-for="p in (aiOptions?.prompts || [])" :key="p.id" :label="p.name" :value="p.name" />
						</el-select>
					</el-form-item>
					<el-form-item label="Temperature">
						<el-input-number v-model="editing.temperature" :min="0" :max="2" :step="0.1" />
					</el-form-item>
					<el-form-item label="Max Tokens">
						<el-input-number v-model="editing.max_tokens" :min="1" :step="256" />
					</el-form-item>
					<el-form-item label="Timeout(s)">
						<el-input-number v-model="editing.timeout" :min="1" :step="5" />
					</el-form-item>
					<el-form-item>
						<div class="ai-actions">
							<div class="left">
								<el-button type="primary" size="small" @click="saveLocal">Save</el-button>
								<el-button size="small" @click="resetToPreset">Reset to Preset</el-button>
							</div>
							<div class="right">
								<el-button size="small" type="warning" plain @click="restoreFollowType">Restore Follow Type</el-button>
								<el-button size="small" type="primary" plain @click="applyToType">Apply to Type</el-button>
							</div>
						</div>
					</el-form-item>
				</el-form>
			</div>
		</el-popover>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Setting } from '@element-plus/icons-vue'
import { usePerCardAISettingsStore, type PerCardAIParams } from '@renderer/stores/usePerCardAISettingsStore'
import { getAIConfigOptions, type AIConfigOptions } from '@renderer/api/ai'
import { getCardAIParams, updateCardAIParams, applyCardAIParamsToType } from '@renderer/api/setting'
import { ElMessage } from 'element-plus'

const props = defineProps<{ cardId: number; cardTypeName?: string }>()

const store = usePerCardAISettingsStore()
const visible = ref(false)
const aiOptions = ref<AIConfigOptions | null>(null)
const editing = ref<PerCardAIParams>({})

async function loadOptions() { try { aiOptions.value = await getAIConfigOptions() } catch {} }

const saved = computed(() => store.getByCardId(props.cardId))
const selectedModelName = computed(() => {
	try {
		const raw = (saved.value || editing.value)?.llm_config_id as any
		const id = raw == null ? undefined : Number(raw)
		const list = aiOptions.value?.llm_configs || []
		const found = list.find(m => Number(m.id) === id)
		return found?.display_name || (id != null ? String(id) : '')
	} catch { return '' }
})

watch(() => props.cardId, async (id) => {
	if (!id) return
	await loadOptions()
	try {
		const resp = await getCardAIParams(id)
		const eff = (resp as any)?.effective_params
		if (eff && Object.keys(eff).length) {
			const fixed = { ...eff, llm_config_id: eff.llm_config_id == null ? eff.llm_config_id : Number(eff.llm_config_id) }
			editing.value = fixed
			store.setForCard(id, { ...fixed })
			return
		}
	} catch {}
	// fallback to saved or preset
	if (saved.value) {
		const sv = saved.value as any
		editing.value = { ...sv, llm_config_id: sv?.llm_config_id == null ? sv?.llm_config_id : Number(sv.llm_config_id) }
	} else {
		const preset = getPresetForType(props.cardTypeName)
		if (!preset.llm_config_id) {
			const first = aiOptions.value?.llm_configs?.[0]; if (first) preset.llm_config_id = Number(first.id)
		}
		editing.value = { ...preset, llm_config_id: preset.llm_config_id == null ? preset.llm_config_id : Number(preset.llm_config_id) }
		store.setForCard(id, editing.value)
	}
}, { immediate: true })

function getPresetForType(typeName?: string): PerCardAIParams {
	// Updated to use English names and prompts
	const map: Record<string, PerCardAIParams> = {
		'SpecialAbility': { prompt_name: 'SpecialAbilityGeneration', temperature: 0.6, max_tokens: 1024, timeout: 60 },
		'OneSentenceSummary': { prompt_name: 'OneSentenceSummary', temperature: 0.6, max_tokens: 1024, timeout: 60 },
		'WorldSetting': { prompt_name: 'WorldSetting', temperature: 0.6, max_tokens: 8192, timeout: 120 },
		'CoreBlueprint': { prompt_name: 'CoreBlueprint', temperature: 0.6, max_tokens: 8192, timeout: 120 },
		'VolumeOutline': { prompt_name: 'VolumeOutline', temperature: 0.6, max_tokens: 8192, timeout: 120 },
		'StageOutline': { prompt_name: 'StageOutline', temperature: 0.6, max_tokens: 8192, timeout: 120 },
		'ChapterOutline': { prompt_name: 'ChapterOutline', temperature: 0.6, max_tokens: 4096, timeout: 60 },
		'WritingGuide': { prompt_name: 'WritingGuide', temperature: 0.7, max_tokens: 8192, timeout: 60 },
		'Chapter': { prompt_name: 'ContentGeneration', temperature: 0.7, max_tokens: 8192, timeout: 60 },
	}
	return map[typeName || ''] || {}
}

function saveLocal() {
	try {
		const payload = { ...editing.value, llm_config_id: editing.value.llm_config_id == null ? editing.value.llm_config_id : Number(editing.value.llm_config_id) }
		// Write to backend first
		updateCardAIParams(props.cardId, payload)
			.then(() => {
				store.setForCard(props.cardId, { ...payload })
				ElMessage.success('Saved')
				visible.value = false
			})
			.catch(() => { ElMessage.error('Failed to save to backend') })
	} catch { ElMessage.error('Save failed') }
}
function resetToPreset() {
	const preset = getPresetForType(props.cardTypeName)
	editing.value = { ...preset, llm_config_id: preset.llm_config_id == null ? preset.llm_config_id : Number(preset.llm_config_id) }
	store.setForCard(props.cardId, editing.value)
}
async function restoreFollowType() {
	try { await updateCardAIParams(props.cardId, null); ElMessage.success('Restored follow type'); const resp = await getCardAIParams(props.cardId); const eff = (resp as any)?.effective_params; if (eff) { editing.value = { ...eff }; store.setForCard(props.cardId, { ...eff }) } } catch { ElMessage.error('Operation failed') }
}
async function applyToType() {
	try {
		await updateCardAIParams(props.cardId, { ...editing.value })
		await applyCardAIParamsToType(props.cardId)
		window.dispatchEvent(new Event('card-types-updated'))
		await updateCardAIParams(props.cardId, null)
		const resp = await getCardAIParams(props.cardId)
		const eff = (resp as any)?.effective_params
		if (eff) { editing.value = { ...eff }; store.setForCard(props.cardId, { ...eff }) }
		ElMessage.success('Applied to type, and restored this card follow type')
	} catch { ElMessage.error('Apply failed') }
}

</script>

<style scoped>
.ai-param-inline { 
  display: inline-flex; 
  align-items: center; 
}

.model-trigger { 
  min-width: 200px;
  max-width: 320px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  overflow: hidden; /* Ensure button itself doesn't overflow */
}

.model-trigger :deep(.el-button__content) {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  flex: 1;
  min-width: 0;
}

.model-label { 
  flex-shrink: 0;
  margin-right: 4px;
  font-weight: 500;
}

.model-name { 
  flex: 1; 
  min-width: 0; 
  overflow: hidden; 
  text-overflow: ellipsis; 
  white-space: nowrap;
  text-align: left;
}
</style>
