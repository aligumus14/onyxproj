<template>
  <teleport to="body">
    <div v-if="open" class="sm" @keydown.esc="$emit('close')">
      <div class="sm__overlay" @click="$emit('close')"></div>

      <div class="sm__modal" role="dialog" aria-modal="true">
        <div class="sm__head">
          <div>
            <div class="sm__title">Settings</div>
            <div class="sm__subtitle">Tema ve arayüz tercihleri</div>
          </div>
          <button class="icon-btn" type="button" title="Close" @click="$emit('close')">✕</button>
        </div>

        <div class="sm__body">
          <!-- Theme -->
          <div class="section">
            <div class="section__title">Theme</div>
            <div class="seg">
              <button
                class="seg__btn"
                :class="{ 'is-active': theme === 'light' }"
                type="button"
                @click="$emit('setTheme', 'light')"
              >
                Light
              </button>
              <button
                class="seg__btn"
                :class="{ 'is-active': theme === 'dark' }"
                type="button"
                @click="$emit('setTheme', 'dark')"
              >
                Dark
              </button>
              <button
                class="seg__btn"
                :class="{ 'is-active': theme === 'system' }"
                type="button"
                @click="$emit('setTheme', 'system')"
              >
                System
              </button>
            </div>
          </div>

          <!-- Sidebar default -->
          <div class="section">
            <div class="section__title">Sidebar</div>

            <label class="row">
              <div class="row__text">
                <div class="row__label">Default collapsed</div>
                <div class="row__hint">Uygulama açılınca sidebar kapalı başlasın</div>
              </div>

              <input
                class="toggle"
                type="checkbox"
                :checked="sidebarDefaultCollapsed"
                @change="$emit('setSidebarDefaultCollapsed', $event.target.checked)"
              />
            </label>
          </div>

          <!-- Mobile drawer default -->
          <div class="section">
            <div class="section__title">Mobile</div>

            <label class="row">
              <div class="row__text">
                <div class="row__label">Drawer default open</div>
                <div class="row__hint">Mobilde menü otomatik açık gelsin</div>
              </div>

              <input
                class="toggle"
                type="checkbox"
                :checked="mobileDrawerDefaultOpen"
                @change="$emit('setMobileDrawerDefaultOpen', $event.target.checked)"
              />
            </label>
          </div>

          <div class="section">
            <div class="section__title">About</div>
            <div class="about">
              Onyx BI Chat UI • Vue 3 • ECharts • DataTable
            </div>
          </div>
        </div>

        <div class="sm__foot">
          <button class="btn" type="button" @click="$emit('close')">Close</button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  theme: { type: String, default: 'dark' }, // light|dark|system
  sidebarDefaultCollapsed: { type: Boolean, default: false },
  mobileDrawerDefaultOpen: { type: Boolean, default: true },
})

defineEmits([
  'close',
  'setTheme',
  'setSidebarDefaultCollapsed',
  'setMobileDrawerDefaultOpen',
])
</script>

<style scoped>
.sm{
  position: fixed;
  inset: 0;
  z-index: 10000;
  display:flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}

.sm__overlay{
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,.55);
  backdrop-filter: blur(3px);
}

.sm__modal{
  position: relative;
  width: min(720px, 96vw);
  max-height: 86vh;
  overflow: hidden;
  display:flex;
  flex-direction: column;
  border-radius: 18px;
  border: 1px solid var(--border-color);
  background: var(--bg-sidebar);
  box-shadow: 0 30px 80px rgba(0,0,0,.45);
}

.sm__head{
  display:flex;
  align-items:flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-topbar);
}

.sm__title{
  font-weight: 950;
  color: var(--text);
  font-size: 16px;
  letter-spacing: .2px;
}

.sm__subtitle{
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.icon-btn{
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--card);
  color: var(--text);
  cursor:pointer;
}

.icon-btn:hover{
  border-color: var(--accent);
}

.sm__body{
  padding: 14px 16px;
  overflow: auto;
}

.section{
  padding: 12px 0;
  border-bottom: 1px dashed rgba(255,255,255,.12);
}

.section:last-child{
  border-bottom: none;
}

.section__title{
  font-weight: 900;
  color: var(--text);
  font-size: 13px;
  margin-bottom: 10px;
}

/* segmented */
.seg{
  display:flex;
  gap: 8px;
  padding: 6px;
  border-radius: 14px;
  border: 1px solid var(--border-color);
  background: rgba(255,255,255,.04);
}

.seg__btn{
  flex: 1;
  height: 34px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted);
  cursor:pointer;
  font-weight: 900;
  font-size: 12px;
}

.seg__btn:hover{
  background: rgba(255,255,255,.06);
  color: var(--text);
}

.seg__btn.is-active{
  background: var(--accent);
  color: #fff;
  border-color: rgba(255,255,255,.18);
}

/* rows */
.row{
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 0;
}

.row__text{
  min-width: 0;
}

.row__label{
  font-weight: 850;
  color: var(--text);
  font-size: 13px;
}

.row__hint{
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.35;
}

/* toggle (simple) */
.toggle{
  width: 46px;
  height: 22px;
  cursor:pointer;
}

/* footer */
.sm__foot{
  padding: 12px 16px;
  border-top: 1px solid var(--border-color);
  display:flex;
  justify-content: flex-end;
  background: var(--bg-topbar);
}

.btn{
  height: 36px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--card);
  color: var(--text);
  cursor:pointer;
  font-weight: 850;
}

.btn:hover{
  border-color: var(--accent);
}

.about{
  color: var(--text-muted);
  font-size: 12px;
}
</style>
