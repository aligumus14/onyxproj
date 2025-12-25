<template>
  <div class="tb">
    <!-- Left -->
    <div class="tb__left">
      <button class="icon-btn" type="button" title="Menu" @click="$emit('toggleDrawer')">
        ☰
      </button>

      <div class="tb__brand">
        <div class="tb__title">Onyx</div>
        <div class="tb__subtitle">BI Chat</div>
      </div>
    </div>

    <!-- Center: Mode Toggle -->
    <div class="tb__right">
      <div class="seg" role="tablist" aria-label="Mode">
        <button
          class="seg__btn"
          :class="{ 'is-active': mode === 'sql' }"
          type="button"
          role="tab"
          @click="$emit('setMode', 'sql')"
        >
          SQL
        </button>
        <button
          class="seg__btn"
          :class="{ 'is-active': mode === 'doc' }"
          type="button"
          role="tab"
          @click="$emit('setMode', 'doc')"
        >
          Belge
        </button>
      </div>
    </div>

    <!-- Right -->
    
  </div>
</template>

<script setup>
defineProps({
  mode: { type: String, default: 'sql' }, // 'sql' | 'doc'
  theme: { type: String, default: 'dark' }, // şimdilik UI amaçlı
})

defineEmits(['toggleDrawer', 'setMode', 'openSettings'])
</script>

<style scoped>
.tb{
  width: 100%;
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 12px;
}

.tb__left{
  display:flex;
  align-items:center;
  gap: 10px;
  min-width: 0;
}

.tb__brand{
  display:flex;
  flex-direction: column;
  line-height: 1.1;
}

.tb__title{
  font-weight: 850;
  letter-spacing: .2px;
  color: var(--text);
  font-size: 14px;
}

.tb__subtitle{
  font-size: 12px;
  color: var(--text-muted);
}

.tb__center{
  flex: 1;
  display:flex;
  justify-content: center;
  min-width: 0;
}

.tb__right{
  display:flex;
  align-items:center;
  gap: 10px;
}

/* segmented control */
.seg{
  display:flex;
  border: 1px solid var(--border-color);
  background: var(--card);
  border-radius: 12px;
  padding: 4px;
  gap: 4px;
  box-shadow: 0 10px 22px rgba(0,0,0,.08);
}

.seg__btn{
  height: 32px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-weight: 750;
  font-size: 12px;
}

.seg__btn.is-active{
  background: var(--accent);
  color: #fff;
  border-color: rgba(255,255,255,.18);
}

.icon-btn{
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--card);
  color: var(--text);
  cursor:pointer;
}

.icon-btn:hover{
  border-color: var(--accent);
}

.btn{
  height: 36px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--card);
  color: var(--text);
  cursor:pointer;
  font-weight: 700;
}

.btn:hover{
  border-color: var(--accent);
}

@media (max-width: 640px){
  .tb__brand{ display:none; }
  .tb__right .btn{ display:none; } /* mobilde yer aç */
}
</style>
