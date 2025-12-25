<template>
  <teleport to="body">
    <div v-if="open" class="sd" @keydown.esc="$emit('close')">
      <!-- overlay -->
      <div class="sd__overlay" @click="$emit('close')"></div>

      <!-- drawer -->
      <aside class="sd__drawer" role="dialog" aria-modal="true">
        <div class="sd__top">
          <div class="sd__title">Chats</div>
          <button class="icon-btn" type="button" title="Close" @click="$emit('close')">✕</button>
        </div>

        <div class="sd__header">
          <button class="btn btn-primary sd__new" type="button" @click="$emit('newChat')">
            + New chat
          </button>

          <input
            class="input"
            v-model="q"
            type="text"
            placeholder="Search chats…"
            autocomplete="off"
          />
        </div>

        <div class="sd__list">
          <template v-for="group in groupedChats" :key="group.label">
            <div v-if="group.items.length" class="sd__group">
              <div class="sd__groupLabel">{{ group.label }}</div>

              <button
                v-for="c in group.items"
                :key="c.id"
                class="sd__item"
                :class="{ 'is-active': c.id === activeChatId }"
                type="button"
                @click="selectAndClose(c.id)"
                :title="c.title"
              >
                <div class="sd__itemTitle">{{ c.title }}</div>
                <div class="sd__itemMeta">
                  <span>{{ formatTime(c.updatedAt) }}</span>
                  <span v-if="c.badge" class="sd__badge">{{ c.badge }}</span>
                </div>
              </button>
            </div>
          </template>

          <div v-if="filteredChats.length === 0" class="sd__empty">No chats found.</div>
        </div>

        <div class="sd__footer">
          <div class="sd__profile">
            <div class="sd__avatar" aria-hidden="true">{{ initials }}</div>
            <div class="sd__profileText">
              <div class="sd__name">{{ userName }}</div>
              <div class="sd__mail">{{ userEmail }}</div>
            </div>
          </div>

          <div class="sd__actions">
            <button class="btn" type="button" @click="$emit('openSettings')">Settings</button>
            <button class="btn" type="button" @click="$emit('logout')">Logout</button>
          </div>
        </div>
      </aside>
    </div>
  </teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  chats: { type: Array, default: () => [] },
  activeChatId: { type: String, default: '' },
  user: {
    type: Object,
    default: () => ({ name: 'Ali', email: 'ali@example.com' }),
  },
})

const emit = defineEmits(['close', 'newChat', 'selectChat', 'openSettings', 'logout'])

const q = ref('')

watch(
  () => props.open,
  (v) => {
    if (v) q.value = ''
  }
)

const filteredChats = computed(() => {
  const term = q.value.trim().toLowerCase()
  if (!term) return props.chats
  return props.chats.filter((c) => String(c.title ?? '').toLowerCase().includes(term))
})

function startOfDay(d) {
  const x = new Date(d)
  x.setHours(0, 0, 0, 0)
  return x.getTime()
}

const groupedChats = computed(() => {
  const now = new Date()
  const today = startOfDay(now)
  const yesterday = today - 24 * 60 * 60 * 1000

  const items = filteredChats.value
    .slice()
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())

  const gToday = []
  const gYesterday = []
  const gOlder = []

  for (const c of items) {
    const t = startOfDay(c.updatedAt)
    if (t === today) gToday.push(c)
    else if (t === yesterday) gYesterday.push(c)
    else gOlder.push(c)
  }

  return [
    { label: 'Today', items: gToday },
    { label: 'Yesterday', items: gYesterday },
    { label: 'Older', items: gOlder },
  ]
})

const userName = computed(() => props.user?.name || 'User')
const userEmail = computed(() => props.user?.email || '')
const initials = computed(() => {
  const n = (props.user?.name || 'U').trim()
  const parts = n.split(/\s+/).filter(Boolean)
  const a = (parts[0]?.[0] || 'U').toUpperCase()
  const b = (parts[1]?.[0] || '').toUpperCase()
  return (a + b).slice(0, 2)
})

function formatTime(dt) {
  if (!dt) return ''
  const d = new Date(dt)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function selectAndClose(id) {
  emit('selectChat', id)
  emit('close')
}
</script>

<style scoped>
.sd{
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  grid-template-columns: 1fr auto;
}

.sd__overlay{
  grid-column: 1 / 2;
  background: rgba(0,0,0,.55);
  backdrop-filter: blur(3px);
}

.sd__drawer{
  grid-column: 2 / 3;
  width: min(92vw, 380px);
  height: 100%;
  background: var(--bg-sidebar);
  border-left: 1px solid var(--border-color);
  display:flex;
  flex-direction: column;
  box-shadow: -20px 0 60px rgba(0,0,0,.35);
  animation: slideIn .18s ease-out;
}

@keyframes slideIn{
  from{ transform: translateX(18px); opacity: .6; }
  to{ transform: translateX(0); opacity: 1; }
}

.sd__top{
  padding: 12px 14px;
  display:flex;
  align-items:center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-topbar);
}

.sd__title{
  font-weight: 850;
  color: var(--text);
}

.sd__header{
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--border-color);
}

.sd__new{
  width: 100%;
  height: 38px;
  border-radius: 10px;
  margin-bottom: 10px;
}

.input{
  width: 100%;
  height: 36px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: var(--card);
  color: var(--text);
  padding: 0 12px;
}

.sd__list{
  flex: 1;
  overflow: auto;
  padding: 10px 10px 14px;
}

.sd__group{ margin-bottom: 12px; }

.sd__groupLabel{
  font-size: 12px;
  color: var(--text-muted);
  padding: 6px 6px 8px;
}

.sd__item{
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  padding: 10px 10px;
  border-radius: 12px;
  cursor: pointer;
  display:flex;
  flex-direction: column;
  gap: 6px;
}

.sd__item:hover{
  background: var(--hover);
  border-color: var(--border-color);
}

.sd__item.is-active{
  background: var(--card);
  border-color: var(--accent);
  box-shadow: 0 10px 22px rgba(0,0,0,.10);
}

.sd__itemTitle{
  font-size: 13px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sd__itemMeta{
  font-size: 12px;
  color: var(--text-muted);
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 8px;
}

.sd__badge{
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--pill);
  color: var(--text);
  font-size: 11px;
}

.sd__empty{
  padding: 18px 10px;
  color: var(--text-muted);
  font-size: 13px;
}

.sd__footer{
  border-top: 1px solid var(--border-color);
  padding: 12px 14px;
  display:flex;
  flex-direction: column;
  gap: 10px;
}

.sd__profile{
  display:flex;
  align-items:center;
  gap: 10px;
  min-width: 0;
}

.sd__avatar{
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight: 800;
  background: var(--accent-soft);
  color: var(--accent);
  flex: 0 0 auto;
}

.sd__profileText{ min-width: 0; }

.sd__name{
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sd__mail{
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sd__actions{
  display:flex;
  gap: 10px;
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
  flex: 1;
}

.btn:hover{ border-color: var(--accent); }

.btn-primary{
  background: var(--accent);
  border-color: transparent;
  color: #fff;
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
</style>
