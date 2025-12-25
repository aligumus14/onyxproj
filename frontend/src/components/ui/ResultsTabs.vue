<template>
  <div class="rt">
    <button
      v-for="t in tabs"
      :key="t.key"
      class="rt__tab"
      :class="{ 'is-active': t.key === activeTab }"
      type="button"
      @click="$emit('setTab', t.key)"
    >
      {{ t.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  tabs: { type: Array, default: () => [] }, // [{key,label}]
  activeTab: { type: String, default: '' },
})
defineEmits(['setTab'])
</script>

<style scoped>
.rt{
  display:flex;
  gap: 8px;
  padding: 6px;
  border-radius: 14px;
  border: 1px solid var(--border-color);
  background: rgba(255,255,255,.04);
  margin-bottom: 12px;
  overflow-x: auto;
}

.rt__tab{
  height: 32px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted);
  cursor:pointer;
  font-weight: 800;
  font-size: 12px;
  white-space: nowrap;
}

.rt__tab:hover{
  background: rgba(255,255,255,.06);
  color: var(--text);
}

.rt__tab.is-active{
  background: var(--accent);
  border-color: rgba(255,255,255,.18);
  color: #fff;
}
</style>
