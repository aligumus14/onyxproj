<template>
  <div class="sb">
    <!-- COLLAPSED: sadece expand -->
    <div v-if="collapsed" class="sb__collapsed">
      <button class="icon-btn icon-btn--big" type="button" title="Expand" @click="$emit('toggleCollapse')">
        ›
      </button>
    </div>

    <!-- EXPANDED -->
    <template v-else>
      <div class="sb__top">
        <button class="icon-btn" type="button" title="Collapse" @click="$emit('toggleCollapse')">
          ‹
        </button>

        <div class="sb__brand">
          <div class="sb__title">Chats</div>
          <div class="sb__sub">History</div>
        </div>
      </div>

      <!-- Chat list -->
      <div class="sb__list">
        <!-- ✅ Sticky New button (chatlerin üstünde sabit) -->
        <div class="sb__newbar">
          <button class="btn sb__newbtn" type="button" @click="$emit('newChat')" style="align-items: center;">
            ＋ New chat
          </button>
        </div>

        <button
          v-for="c in chats"
          :key="c.id"
          class="sb__item"
          :class="{ 'is-active': c.id === activeChatId }"
          type="button"
          @click="$emit('selectChat', c.id)"
          :title="c.title"
        >
          <span class="dot"></span>
          <span class="t">{{ c.title }}</span>
        </button>

        <div v-if="!chats || chats.length === 0" class="sb__empty">No chats.</div>
      </div>

      <!-- Footer profile row: Settings + Logout ICONS -->
      <div class="sb__foot">
        <div class="sb__profile">
          <div class="sb__avatar" :title="userName">{{ initials }}</div>

          <div class="sb__profileText">
            <div class="sb__name">{{ userName }}</div>
            <div class="sb__mail">{{ userEmail }}</div>
          </div>

          <div class="sb__icons">
            <button class="icon-btn" type="button" title="Settings" @click="$emit('openSettings')">
              ⚙
            </button>

            <button class="icon-btn" type="button" title="Logout" @click="$emit('logout')">
              ⎋
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  chats: { type: Array, default: () => [] },
  activeChatId: { type: String, default: '' },
  user: { type: Object, default: () => ({ name: 'Ali', email: '' }) },
})

defineEmits(['newChat', 'selectChat', 'toggleCollapse', 'openSettings', 'logout'])

const userName = computed(() => props.user?.name || 'User')
const userEmail = computed(() => props.user?.email || '')

const initials = computed(() => {
  const n = String(props.user?.name || 'U').trim().split(/\s+/).filter(Boolean)
  const a = (n[0]?.[0] || 'U').toUpperCase()
  const b = (n[1]?.[0] || '').toUpperCase()
  return (a + b).slice(0, 2)
})
</script>

<style scoped>
.sb{
  height: 100%;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  display:flex;
  flex-direction: column;
}

/* collapsed */
.sb__collapsed{
  padding: 10px 6px;
  display:flex;
  justify-content:center;
}

/* top */
.sb__top{
  padding: 12px;
  display:flex;
  align-items:center;
  gap: 10px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-topbar);
}

.sb__brand{ line-height: 1.1; }
.sb__title{ font-weight: 900; color: var(--text); font-size: 14px; }
.sb__sub{ color: var(--text-muted); font-size: 12px; }

/* list */
.sb__list{
  flex: 1;
  min-height: 0;
  overflow:auto;
  padding: 10px;
  display:flex;
  flex-direction: column;
  gap: 8px;
}

/* ✅ sticky new bar */
.sb__newbar{
  position: sticky;
  top: 0;
  z-index: 5;
  padding: 6px 0 10px;
  background: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
}

.sb__newbtn{
  width: 100%;
  display:flex;
  justify-content: center;
  gap: 8px;
}

.sb__item{
  display:flex;
  align-items:center;
  gap: 10px;
  padding: 10px;
  border-radius: 14px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  cursor:pointer;
  text-align:left;
  min-width:0;
}
.sb__item:hover{ background: var(--hover); border-color: var(--border-color); }
.sb__item.is-active{ background: var(--card); border-color: var(--accent); }

.dot{
  width: 8px; height: 8px; border-radius: 999px;
  background: var(--accent);
  flex: 0 0 auto;
}
.t{
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width:0;
  font-weight: 800;
  font-size: 13px;
}

.sb__empty{ color: var(--text-muted); padding: 10px; }

/* footer profile row */
.sb__foot{
  border-top: 1px solid var(--border-color);
  padding: 12px;
}

.sb__profile{
  display:flex;
  align-items:center;
  gap: 10px;
  min-width: 0;
}

.sb__avatar{
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight: 950;
  background: var(--accent-soft);
  color: var(--accent);
  flex: 0 0 auto;
}

.sb__profileText{
  min-width: 0;
  flex: 1;
}
.sb__name{
  font-weight: 900;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sb__mail{
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sb__icons{
  display:flex;
  gap: 8px;
  flex: 0 0 auto;
}

/* buttons */
.icon-btn{
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--card);
  color: var(--text);
  cursor:pointer;
  font-weight: 900;
}
.icon-btn:hover{ border-color: var(--accent); }

.icon-btn--big{
  width: 44px;
  height: 44px;
  border-radius: 14px;
  font-size: 18px;
}

.btn{
  height: 36px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--card);
  color: var(--text);
  cursor:pointer;
  font-weight: 850;
}
.btn:hover{ border-color: var(--accent); }
</style>
