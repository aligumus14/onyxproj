<template>
  <AppShell class="page" :style="shellVars">
    <!-- Sidebar (desktop) -->
    <template #sidebar>
      <Sidebar
        :collapsed="ui.sidebarCollapsed"
        :chats="chats"
        :activeChatId="ui.activeChatId"
        :user="user"
        @newChat="newChat"
        @selectChat="selectChat"
        @toggleCollapse="toggleCollapse"
        @openSettings="ui.settingsOpen = true"
        @logout="logout"
      />
    </template>

    <!-- Topbar -->
    <template #topbar>
      <Topbar
        :mode="ui.mode"
        :theme="ui.theme"
        @toggleDrawer="ui.mobileDrawerOpen = true"
        @setMode="setMode"
        @openSettings="ui.settingsOpen = true"
      />
    </template>

    <!-- Chat -->
    <template #chat>
      <ChatPane
        :mode="ui.mode"
        :messages="activeMessages"
        :loading="ui.loading"
        :error="ui.error"
        @send="sendQuestion"
        @upload="uploadDoc"
        :selectedResultId="ui.selectedResultId"
        @selectResult="selectResultFromMessage"
      />
    </template>

    <!-- Results -->
    <template #results>
      <ResultsPane
        :mode="ui.mode"
        :result="ui.lastResult"
        :activeTab="ui.resultsTab"
        @setTab="ui.resultsTab = $event"
        @openDoc="openDoc"
        @downloadPdf="downloadPDF"
      />
    </template>

    <!-- Modals -->
    <template #modal>
      <!-- Mobile drawer (sağdan) -->
      <SidebarDrawer
        :open="ui.mobileDrawerOpen"
        :chats="chats"
        :activeChatId="ui.activeChatId"
        :user="user"
        @close="ui.mobileDrawerOpen = false"
        @newChat="newChat"
        @selectChat="selectChat"
        @openSettings="ui.settingsOpen = true"
        @logout="logout"
      />

      <!-- Settings modal (bir sonraki adımda dolduracağız) -->
      <!-- ŞİMDİLİK dosya boşsa import hatası vermesin diye, bir sonraki mesajda SettingsModal.vue yazacağız -->
      <SettingsModal
        :open="ui.settingsOpen"
        :theme="ui.theme"
        :sidebarDefaultCollapsed="ui.sidebarDefaultCollapsed"
        :mobileDrawerDefaultOpen="ui.mobileDrawerDefaultOpen"
        @close="ui.settingsOpen = false"
        @setTheme="setTheme"
        @setSidebarDefaultCollapsed="setSidebarDefaultCollapsed"
        @setMobileDrawerDefaultOpen="setMobileDrawerDefaultOpen"
      />

      <!-- Doc Viewer (minimal) -->
      <teleport to="body">
        <div v-if="doc.open" class="docOverlay" @click.self="doc.open = false">
          <div class="docModal">
            <div class="docHead">
              <div class="docTitle">{{ doc.docId }}</div>
              <button class="btn" type="button" @click="doc.open = false">Kapat</button>
            </div>
            <pre class="docPre"><code>{{ doc.json }}</code></pre>
          </div>
        </div>
      </teleport>
    </template>
  </AppShell>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import AppShell from '../shell/AppShell.vue'
import Sidebar from '../shell/Sidebar.vue'
import SidebarDrawer from '../shell/SidebarDrawer.vue'
import Topbar from '../shell/Topbar.vue'
import ChatPane from '../shell/ChatPane.vue'
import ResultsPane from '../shell/ResultsPane.vue'
import SettingsModal from '../ui/SettingsModal.vue'

/** ========= API ========= */
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function apiJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const msg = data?.detail || data?.message || `HTTP ${res.status}`
    throw new Error(msg)
  }
  return data
}

async function apiUpload(path, file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}${path}`, { method: 'POST', body: fd })
  const data = await res.json().catch(() => null)
  if (!res.ok || !data) {
    const msg = data?.detail || data?.message || `HTTP ${res.status}`
    throw new Error(msg)
  }
  return data
}

async function apiPdf(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const msg = data?.detail || data?.message || `HTTP ${res.status}`
    throw new Error(msg)
  }
  return await res.blob()
}

/** ========= UI STATE (Pinia yok) ========= */
const LS_UI = 'onyx_ui_v1'
const LS_CHATS = 'onyx_chats_v1'

const ui = reactive({
  theme: 'dark', // 'dark' | 'light' | 'system'
  mode: 'sql', // 'sql' | 'doc'
  sidebarCollapsed: false,
  sidebarDefaultCollapsed: false,
  mobileDrawerOpen: false,
  mobileDrawerDefaultOpen: true,
  selectedResultId: '',

  settingsOpen: false,

  activeChatId: '',
  resultsTab: 'table', // table|charts|sql|sources
  lastResult: null,

  loading: false,
  error: '',

  // PDF export için son rapor paketi
  lastPdf: { summary: '', question: '' },
})

const user = ref(readUser())
const chats = ref(readChats())

const doc = reactive({
  open: false,
  docId: '',
  json: '',
})

/** ========= Derived ========= */
const shellVars = computed(() => ({
  '--sidebar-width': ui.sidebarCollapsed ? '78px' : '320px',
}))

const activeChat = computed(() => chats.value.find(c => c.id === ui.activeChatId) || null)
const activeMessages = computed(() => activeChat.value?.messages || [])

/** ========= Init ========= */
function ensureChat() {
  if (!chats.value.length) {
    const id = makeId()
    chats.value.push({
      id,
      title: 'New chat',
      updatedAt: new Date().toISOString(),
      badge: '',
      messages: [],
      lastResult: null,
    })
    ui.activeChatId = id
  }
  if (!ui.activeChatId) ui.activeChatId = chats.value[0].id
}

onMounted(() => {
  loadUi()
  ensureChat()
  applyTheme(ui.theme)

  // mobile drawer default
  if (ui.mobileDrawerDefaultOpen) {
    // sadece küçük ekranlarda otomatik açılabilir; şimdilik direkt açma yok
    // kullanıcı topbar menüsünden açsın
  }
})

/** ========= Chat ops ========= */
function newChat() {
  const id = makeId()
  chats.value.unshift({
    id,
    title: 'New chat',
    updatedAt: new Date().toISOString(),
    badge: '',
    messages: [],
    lastResult: null,
  })
  ui.activeChatId = id
  ui.lastResult = null
  ui.resultsTab = 'table'
  persistChats()
  newChat()
}

function selectChat(id) {
  ui.activeChatId = id
  const c = chats.value.find(x => x.id === id)
  ui.lastResult = c?.lastResult || null
  ui.resultsTab = ui.lastResult?.table ? 'table' : (ui.lastResult?.charts?.length ? 'charts' : 'sources')
  ui.mobileDrawerOpen = false
  persistChats()
}

function toggleCollapse() {
  ui.sidebarCollapsed = !ui.sidebarCollapsed
  persistUi()
}

function setMode(m) {
  ui.mode = m
  // mode değişince results tab’ı mantıklı yere çek
  ui.resultsTab = m === 'sql' ? 'table' : 'charts'
  persistUi()
}

function pushMsg(role, content) {
  const c = activeChat.value
  if (!c) return null

  const msg = {
    id: makeId(),
    role,
    content: String(content ?? ''),
    ts: new Date().toISOString(),
    hasResult: false,
  }

  c.messages.push(msg)
  c.updatedAt = new Date().toISOString()

  if (role === 'user' && (c.title === 'New chat' || !c.title)) {
    c.title = (content || 'New chat').trim().slice(0, 42)
  }

  persistChats()
  return msg
}

/** ========= SEND (SQL / DOC) ========= */
async function sendQuestion(payload) {
  ui.error = ''
  ui.loading = true

  const question = payload?.question || ''
  pushMsg('user', question)

  try {
    if (ui.mode === 'sql') {
      const res = await apiJson('/ask', { question })

      if (!res?.success) throw new Error(res?.message || 'SQL başarısız')

      const rows = Array.isArray(res.data) ? res.data : []
      const meta = res.meta || {}
      const summary = res.summary || ''

      // Chat’e summary bas
      const aiMsg = pushMsg('ai', summary || '✅ Sorgu çalıştırıldı.')


      // Result packet
      const columns = (meta.columns || inferColumns(rows)).map((k) => ({ key: k, label: k }))
      const charts = autoChartsFromTable(rows, meta)

      ui.lastResult = {
        table: { columns, rows },
        charts,
        sql: { query: meta.sql || '' , explanation: '' },
        sources: [],
      }
      const c = activeChat.value
if (c) {
  c.results ||= {}
  const compact = compactResult(ui.lastResult)
  if (aiMsg) {
    aiMsg.hasResult = true
    c.results[aiMsg.id] = compact
    ui.selectedResultId = aiMsg.id
  }
  c.lastResult = compact
  ui.lastResult = compact
  persistChats()
}


      ui.lastPdf = { summary: summary || JSON.stringify(rows, null, 2), question }
      ui.resultsTab = rows.length ? 'table' : (charts.length ? 'charts' : 'sql')

      // chat içine de kaydet
      if (activeChat.value) activeChat.value.lastResult = ui.lastResult
      persistChats()
    } else {
      const res = await apiJson('/ask-doc', { question })

      if (!res?.success) throw new Error('Belge sorgusu başarısız')

      const answer = res.answer || ''
      const candidates = Array.isArray(res.candidates) ? res.candidates : []

      const aiMsg = pushMsg('ai', answer || '✅ Yanıt geldi.')


      const sources = candidates.map((c) => ({
        docId: c.doc_id,
        title: buildDocTitle(c),
        score: c.score ?? null,
        excerpt: buildDocExcerpt(c),
      }))

      ui.lastResult = {
        table: null,
        charts: [], // ResultsPane doc modunda sources varsa stackedBar üretir
        sql: null,
        sources,
      }
      const c = activeChat.value
if (c) {
  c.results ||= {}
  const compact = compactResult(ui.lastResult)
  if (aiMsg) {
    aiMsg.hasResult = true
    c.results[aiMsg.id] = compact
    ui.selectedResultId = aiMsg.id
  }
  c.lastResult = compact
  ui.lastResult = compact
  persistChats()
}


      ui.lastPdf = {
        summary: answer + (sources.length ? `\n\nSources:\n- ` + sources.map(s => `${s.docId} (${s.score ?? '-'})`).join('\n- ') : ''),
        question,
      }

      ui.resultsTab = 'charts' // stacked bar’ı direkt gösterelim
      if (activeChat.value) activeChat.value.lastResult = ui.lastResult
      persistChats()
    }
  } catch (e) {
    ui.error = e?.message || String(e)
    pushMsg('ai', `❌ Hata: ${ui.error}`)
  } finally {
    ui.loading = false
  }
}

/** ========= UPLOAD ========= */
async function uploadDoc(file) {
  ui.error = ''
  ui.loading = true
  try {
    const res = await apiUpload('/upload', file)
    if (!res?.success) throw new Error(res?.message || 'Upload başarısız')

    pushMsg('ai', `📄 Yüklendi: ${res.filename}\n${res.summary || ''}`.trim())
  } catch (e) {
    ui.error = e?.message || String(e)
    pushMsg('ai', `❌ Upload hatası: ${ui.error}`)
  } finally {
    ui.loading = false
  }
}

/** ========= PDF DOWNLOAD ========= */
async function downloadPDF() {
  ui.error = ''
  try {
    const { summary, question } = ui.lastPdf || {}
    if (!summary || !question) throw new Error('PDF için içerik yok (önce bir sonuç üret).')

    const blob = await apiPdf('/download-pdf', { summary, question })
    saveBlob(blob, 'rapor.pdf')
  } catch (e) {
    ui.error = e?.message || String(e)
    pushMsg('ai', `❌ PDF hatası: ${ui.error}`)
  }
}

/** ========= DOC VIEW ========= */
async function openDoc(docId) {
  ui.error = ''
  if (!docId) return
  try {
    const res = await fetch(`${API_BASE}/document/${encodeURIComponent(docId)}`)
    const data = await res.json().catch(() => null)
    if (!res.ok || !data?.success) {
      const msg = data?.detail || data?.message || `HTTP ${res.status}`
      throw new Error(msg)
    }

    doc.open = true
    doc.docId = docId
    doc.json = JSON.stringify(data.document, null, 2)
  } catch (e) {
    ui.error = e?.message || String(e)
    pushMsg('ai', `❌ Belge açma hatası: ${ui.error}`)
  }
}

/** ========= SETTINGS (theme + defaults) ========= */
function setTheme(t) {
  ui.theme = t
  applyTheme(t)
  persistUi()
}

function setSidebarDefaultCollapsed(v) {
  ui.sidebarDefaultCollapsed = !!v
  ui.sidebarCollapsed = !!v
  persistUi()
}

function setMobileDrawerDefaultOpen(v) {
  ui.mobileDrawerDefaultOpen = !!v
  persistUi()
}

function applyTheme(t) {
  const root = document.documentElement
  if (t === 'system') {
    // şimdilik dark'a düş; bir sonraki adımda media query dinleriz
    root.setAttribute('data-theme', 'dark')
    return
  }
  root.setAttribute('data-theme', t)
}

/** ========= AUTH ========= */
function logout() {
  localStorage.removeItem('onyx_token')
  localStorage.removeItem('onyx_user')
  // router varsa login'e yönlendireceğiz; şimdilik hard refresh
  window.location.href = '/login'
}

/** ========= Persistence ========= */
function persistUi() {
  const pack = {
    theme: ui.theme,
    mode: ui.mode,
    sidebarCollapsed: ui.sidebarCollapsed,
    sidebarDefaultCollapsed: ui.sidebarDefaultCollapsed,
    mobileDrawerDefaultOpen: ui.mobileDrawerDefaultOpen,
  }
  localStorage.setItem(LS_UI, JSON.stringify(pack))
}

function loadUi() {
  try {
    const raw = localStorage.getItem(LS_UI)
    if (!raw) return
    const p = JSON.parse(raw)
    ui.theme = p.theme ?? ui.theme
    ui.mode = p.mode ?? ui.mode
    ui.sidebarCollapsed = p.sidebarCollapsed ?? ui.sidebarCollapsed
    ui.sidebarDefaultCollapsed = p.sidebarDefaultCollapsed ?? ui.sidebarDefaultCollapsed
    ui.mobileDrawerDefaultOpen = p.mobileDrawerDefaultOpen ?? ui.mobileDrawerDefaultOpen
  } catch {}
}

function persistChats() {
  try {
    localStorage.setItem(LS_CHATS, JSON.stringify(chats.value))
  } catch {}
}

function readChats() {
  try {
    const raw = localStorage.getItem(LS_CHATS)
    if (!raw) return []
    const v = JSON.parse(raw)
    const arr = Array.isArray(v) ? v : []
    // eski kayıtları upgrade et
    for (const c of arr) {
      c.messages ||= []
      c.results ||= {}
      // eski mesajlarda hasResult yoksa ekle
      for (const m of (c.messages || [])) {
        if (m && typeof m === 'object' && m.role === 'ai' && m.hasResult == null) {
          m.hasResult = !!c.results?.[m.id]
        }
      }
    }
    return arr
  } catch {
    return []
  }
}
function compactResult(r) {
  if (!r) return r
  const out = JSON.parse(JSON.stringify(r))

  // tablo çok büyükse localStorage şişmesin
  if (out.table?.rows && Array.isArray(out.table.rows) && out.table.rows.length > 200) {
    out.table.rows = out.table.rows.slice(0, 200)
    out.table._truncated = true
  }
  return out
}

function readUser() {
  try {
    const raw = localStorage.getItem('onyx_user')
    if (!raw) return { name: 'Ali', email: '' }
    const u = JSON.parse(raw)
    return { name: u?.name || 'Ali', email: u?.email || '' }
  } catch {
    return { name: 'Ali', email: '' }
  }
}

/** ========= Utils ========= */
function makeId() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16)
}

function inferColumns(rows) {
  const r0 = rows?.[0]
  if (r0 && typeof r0 === 'object' && !Array.isArray(r0)) return Object.keys(r0)
  return []
}

function autoChartsFromTable(rows, meta) {
  // Basit otomatik grafik: ilk categorical + ilk numeric => bar
  // numericColumns meta'dan geliyorsa kullan
  if (!Array.isArray(rows) || rows.length === 0) return []

  const cols = meta?.columns || inferColumns(rows)
  const numeric = (meta?.numeric_columns || []).filter(Boolean)

  const firstObj = rows[0]
  const cat = cols.find(k => typeof firstObj?.[k] === 'string') || cols[0]
  const num = numeric[0] || cols.find(k => typeof firstObj?.[k] === 'number')

  if (!cat || !num) return []

  const dataset = rows.slice(0, 20).map(r => ({ x: r[cat], y: Number(r[num] ?? 0) }))

  return [
    {
      type: 'bar',
      title: `${num} by ${cat}`,
      xKey: 'x',
      dataset,
      series: [{ name: num, yKey: 'y' }],
      stack: false,
    },
    {
      type: 'area',
      title: `Area: ${num}`,
      xKey: 'x',
      dataset,
      series: [{ name: num, yKey: 'y' }],
      stack: false,
    },
  ]
}

function buildDocTitle(c) {
  const id = c.doc_id || ''
  const t = c.doc_type || ''
  const d = c.date ? ` • ${c.date}` : ''
  const v = c.vendor ? ` • ${c.vendor}` : ''
  const m = c.machine ? ` • ${c.machine}` : ''
  return `${id} • ${t}${d}${v}${m}`.trim()
}

function buildDocExcerpt(c) {
  const parts = []
  if (c.vendor) parts.push(`Vendor: ${c.vendor}`)
  if (c.machine) parts.push(`Machine: ${c.machine}`)
  if (c.grand_total != null) parts.push(`Grand Total: ${c.grand_total}`)
  return parts.join(' • ')
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
function selectResultFromMessage(msgId) {
  const c = activeChat.value
  if (!c?.results?.[msgId]) return

  ui.lastResult = c.results[msgId]
  ui.selectedResultId = msgId

  // SQL modda uygun sekmeye çek (doc modda zaten sources-only)
  if (ui.mode === 'sql') {
    ui.resultsTab = ui.lastResult?.table ? 'table' : (ui.lastResult?.charts?.length ? 'charts' : 'sql')
  }

  c.lastResult = ui.lastResult
  persistChats()
}

onBeforeUnmount(() => {
  persistUi()
  persistChats()
})
</script>

<style scoped>
.page{
  height: 100%;
}

/* Doc modal */
.docOverlay{
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0,0,0,.55);
  display:flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}

.docModal{
  width: min(980px, 96vw);
  max-height: 86vh;
  background: rgba(20,24,34,.98);
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 16px;
  overflow: hidden;
  display:flex;
  flex-direction: column;
}

.docHead{
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255,255,255,.14);
}

.docTitle{
  color: #fff;
  font-weight: 900;
}

.docPre{
  margin: 0;
  padding: 14px;
  overflow: auto;
  color: rgba(255,255,255,.9);
  font-size: 12px;
  line-height: 1.45;
}

.btn{
  height: 34px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.14);
  background: rgba(255,255,255,.06);
  color: #fff;
  cursor:pointer;
  font-weight: 750;
}
</style>
