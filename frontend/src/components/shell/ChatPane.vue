<template>
  <div class="cp">
    <!-- ERROR -->
    <div v-if="error" class="cp__error">
      ⚠️ {{ error }}
    </div>

    <!-- MESSAGES -->
    <div ref="listEl" class="cp__messages">
      <div v-if="messages.length === 0" class="cp__empty">
        <div class="cp__emptyTitle">
          {{ mode === 'sql' ? 'SQL modundasın' : 'Belge modundasın' }}
        </div>
        <div class="cp__emptyText">
          <template v-if="mode === 'sql'">
            Örnek: “Toplam satış tutarı en yüksek 5 müşteri kim? Sipariş sayısı ve toplam satış.”
          </template>
          <template v-else>
            Örnek: “Palet Sarma Makinesi servis raporunda arıza nedeni ve yapılan işlemler nelerdir?”
          </template>
        </div>

        <div v-if="mode === 'doc'" class="cp__emptyHint">
          PDF yükleyip sonra soru sorabilirsin. İstersen “Belge ID” girerek tek bir belgeyi hedefleyebilirsin.
        </div>
      </div>

      <div
        v-for="m in messages"
        :key="m.id"
        class="msg"
        :class="[
          m.role === 'user' ? 'msg--user' : 'msg--ai',
          m.role === 'ai' && m.hasResult ? 'msg--clickable' : '',
          m.role === 'ai' && selectedResultId && m.id === selectedResultId ? 'msg--selected' : ''
        ]"
        @click="onMsgClick(m)"
      >
        <div class="msg__bubble">
          <div class="msg__text">{{ m.content }}</div>
          <div class="msg__meta">
            <span class="msg__role">{{ m.role === 'user' ? 'Sen' : 'Asistan' }}</span>
            <span v-if="m.ts" class="msg__time">{{ formatTime(m.ts) }}</span>

            <!-- mini ipucu -->
            <span v-if="m.role === 'ai' && m.hasResult" class="msg__hint">↗ sonuç</span>
          </div>
        </div>
      </div>

      <div v-if="loading" class="cp__typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        <span class="cp__typingText">Düşünüyor…</span>
      </div>
    </div>

    <!-- COMPOSER -->
    <div class="cp__composer">
      <div v-if="mode === 'doc'" class="cp__docTools">
        <input
          ref="fileEl"
          type="file"
          accept=".pdf,.txt"
          class="cp__file"
          @change="onFileChange"
        />
        <button class="btn" type="button" @click="pickFile" :disabled="loading">
          📤 PDF Yükle
        </button>

        <input
          v-model="docId"
          class="input cp__docId"
          type="text"
          placeholder="Belge ID (opsiyonel)"
          :disabled="loading"
        />
      </div>

      <div class="cp__askRow">
        <textarea
          v-model="question"
          class="ta"
          :placeholder="mode === 'sql'
            ? 'SQL için sorunu yaz…'
            : 'Belge için sorunu yaz…'"
          :disabled="loading"
          rows="2"
          @keydown="onKeydown"
        ></textarea>

        <button class="btn btn-primary" type="button" @click="submit" :disabled="loading || !question.trim()">
          {{ loading ? '...' : 'Sor' }}
        </button>
      </div>

      <div class="cp__hint">
        Enter = gönder • Shift+Enter = yeni satır
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  mode: { type: String, default: 'sql' }, // 'sql' | 'doc'
  messages: { type: Array, default: () => [] }, // [{id, role:'user'|'ai', content, ts?, hasResult?}]
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  selectedResultId: { type: String, default: '' },
})

const emit = defineEmits(['send', 'upload', 'selectResult'])

const question = ref('')
const docId = ref('')

const listEl = ref(null)
const fileEl = ref(null)

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

watch(
  () => props.loading,
  async (v) => {
    if (!v) {
      await nextTick()
      scrollToBottom()
    }
  }
)

function scrollToBottom() {
  const el = listEl.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}

function submit() {
  const q = question.value.trim()
  if (!q || props.loading) return

  const payload =
    props.mode === 'doc'
      ? { question: q, doc_id: docId.value.trim() || null }
      : { question: q }

  emit('send', payload)
  question.value = ''
}

function pickFile() {
  fileEl.value?.click()
}

function onFileChange(e) {
  const f = e?.target?.files?.[0]
  if (!f) return
  emit('upload', f)
  e.target.value = ''
}

function onMsgClick(m) {
  // sadece AI mesajında result varsa tıklanabilir
  if (m?.role === 'ai' && m?.hasResult) {
    emit('selectResult', m.id)
  }
}

function formatTime(ts) {
  const d = new Date(ts)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}
</script>

<style scoped>
.cp{height:100%;display:flex;flex-direction:column;min-height:0}
.cp__error{background:rgba(255,76,76,.12);border:1px solid rgba(255,76,76,.35);color:var(--text,#fff);padding:10px 12px;border-radius:12px;margin-bottom:10px}
.cp__messages{flex:1;min-height:0;overflow:auto;padding:6px 2px 14px}
.cp__empty{margin-top:20px;padding:18px 16px;border:1px dashed var(--border-color,rgba(255,255,255,.16));border-radius:14px;background:var(--card,rgba(255,255,255,.04))}
.cp__emptyTitle{font-weight:850;color:var(--text,#fff);margin-bottom:6px}
.cp__emptyText{color:var(--text-muted,rgba(255,255,255,.7));font-size:13px;line-height:1.5}
.cp__emptyHint{margin-top:10px;color:var(--text-muted,rgba(255,255,255,.7));font-size:12px}

.msg{display:flex;margin:10px 0}
.msg--user{justify-content:flex-end}
.msg--ai{justify-content:flex-start}

.msg__bubble{
  max-width:min(720px,92%);
  padding:12px 12px 10px;
  border-radius:16px;
  border:1px solid var(--border-color,rgba(255,255,255,.14));
  background:var(--card,rgba(255,255,255,.05));
}

.msg--user .msg__bubble{background:var(--accent,#6d5efc);border-color:rgba(255,255,255,.14)}

.msg__text{white-space:pre-wrap;word-break:break-word;color:#fff;font-size:13px;line-height:1.5}
.msg--ai .msg__text{color:var(--text,#fff)}

.msg__meta{
  display:flex;justify-content:space-between;gap:10px;margin-top:8px;font-size:11px;opacity:.85
}
.msg__role{color:rgba(255,255,255,.9)}
.msg__time{color:rgba(255,255,255,.75)}
.msg__hint{color:rgba(255,255,255,.75);font-weight:800}

/* ✅ tıklanabilir AI mesajı */
.msg--clickable{cursor:pointer}
.msg--clickable .msg__bubble{transition: border-color .12s ease, transform .12s ease}
.msg--clickable:hover .msg__bubble{
  border-color: var(--accent);
  transform: translateY(-1px);
}

/* seçili result mesajı */
.msg--selected .msg__bubble{
  border-color: var(--accent);
  box-shadow: 0 12px 26px rgba(0,0,0,.18);
}

.cp__typing{display:flex;align-items:center;gap:8px;padding:10px 4px;color:var(--text-muted,rgba(255,255,255,.7));font-size:12px}
.dot{width:6px;height:6px;border-radius:999px;background:var(--text-muted,rgba(255,255,255,.6));display:inline-block;animation:b 1s infinite ease-in-out}
.dot:nth-child(2){animation-delay:.12s}
.dot:nth-child(3){animation-delay:.24s}
@keyframes b{0%,100%{transform:translateY(0);opacity:.45}50%{transform:translateY(-4px);opacity:1}}

.cp__composer{border-top:1px solid var(--border-color,rgba(255,255,255,.14));padding:12px 0 0}
.cp__docTools{display:flex;gap:10px;align-items:center;margin-bottom:10px}
.cp__file{display:none}
.cp__docId{flex:1}
.cp__askRow{display:flex;gap:10px;align-items:flex-end}

.ta{
  flex:1;min-height:44px;max-height:160px;resize:vertical;border-radius:14px;
  border:1px solid var(--border-color,rgba(255,255,255,.14));
  background:var(--card,rgba(255,255,255,.05));color:var(--text,#fff);
  padding:10px 12px;outline:none
}
.ta:focus{border-color:var(--accent,#6d5efc)}

.input{
  height:36px;border-radius:12px;border:1px solid var(--border-color,rgba(255,255,255,.14));
  background:var(--card,rgba(255,255,255,.05));color:var(--text,#fff);padding:0 12px;outline:none
}
.input:focus{border-color:var(--accent,#6d5efc)}

.btn{
  height:44px;padding:0 14px;border-radius:14px;border:1px solid var(--border-color,rgba(255,255,255,.14));
  background:var(--card,rgba(255,255,255,.06));color:var(--text,#fff);cursor:pointer;font-weight:750
}
.btn:disabled{opacity:.55;cursor:not-allowed}
.btn-primary{background:var(--accent,#6d5efc);border-color:transparent;color:#fff}

.cp__hint{margin-top:8px;font-size:12px;color:var(--text-muted,rgba(255,255,255,.7))}
</style>
