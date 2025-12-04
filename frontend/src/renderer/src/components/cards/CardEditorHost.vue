<template>
  <div class="card-editor-host">
    <component :is="activeEditorComponent" :key="card.id" :card="card" :prefetched="prefetched" />
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue';
import type { CardRead } from '@renderer/api/cards';

const props = defineProps<{
  card: CardRead;
  prefetched?: any;
}>();

// --- Editor Component Map ---
// This map allows us to resolve a string name to an actual component.
// Only register editors requiring completely custom shell here
// If only content editor differs (e.g. Chapter Body CodeMirrorEditor),
// Should configure via GenericCardEditor content_editor_component
const editorMap: Record<string, any> = {
  TagsEditor: defineAsyncComponent(() => import('../editors/TagsEditor.vue')),
  // Add other custom editors here in the future
};

// --- Default Editor ---
const GenericCardEditor = defineAsyncComponent(() => import('./GenericCardEditor.vue'));


const activeEditorComponent = computed(() => {
  const customEditorName = props.card.card_type.editor_component;
  if (customEditorName && editorMap[customEditorName]) {
    return editorMap[customEditorName];
  }
  return GenericCardEditor;
});
</script>

<style scoped>
.card-editor-host {
  height: 100%;
  width: 100%;
}
</style>
