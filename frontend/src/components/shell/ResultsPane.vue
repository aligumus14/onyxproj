<template>
  <div class="rp">
    <div class="rp__header">
      <div class="rp__title">
        {{ mode === 'doc' ? 'Sources' : 'Results' }}
      </div>

      <div class="rp__actions">
        <button class="btn" type="button" @click="$emit('downloadPdf')" :disabled="!hasAnyResult">
          PDF
        </button>
      </div>
    </div>

    <!-- ✅ DOC MODE: SADECE SOURCES -->
    <template v-if="mode === 'doc'">
      <div class="rp__body">
        <div v-if="(result?.sources || []).length" class="rp__card">
          <div class="rp__cardTitle">Sources</div>

          <div class="srcList">
            <button
              v-for="s in result.sources"
              :key="s.docId"
              class="srcItem"
              type="button"
              @click="$emit('openDoc', s.docId)"
            >
              <div class="srcItem__title">{{ s.title || s.docId }}</div>
              <div class="srcItem__meta">
                <span class="pill">score: {{ formatScore(s.score) }}</span>
                <span class="muted">id: {{ s.docId }}</span>
              </div>
              <div v-if="s.excerpt" class="srcItem__excerpt">
                {{ s.excerpt }}
              </div>
            </button>
          </div>
        </div>

        <div v-else class="rp__empty">
          Bu sonuçta kaynak yok.
        </div>
      </div>
    </template>

    <!-- ✅ SQL MODE: TAB’LER KALSIN -->
    <template v-else>
      <ResultsTabs :tabs="tabs" :activeTab="activeTabSafe" @setTab="$emit('setTab', $event)" />

      <div class="rp__body">
        <!-- TABLE -->
        <div v-if="activeTabSafe === 'table'">
          <div v-if="result?.table" class="rp__card">
            <div class="rp__cardTitle">Table</div>
            <DataTable :table="result.table" />
          </div>
          <div v-else class="rp__empty">
            Bu sonuçta tablo yok.
          </div>
        </div>

        <!-- CHARTS -->
        <div v-else-if="activeTabSafe === 'charts'">
          <div v-if="(result?.charts || []).length" class="rp__stack">
            <div v-for="(ch, i) in result.charts" :key="i" class="rp__card">
              <div class="rp__cardTitle">{{ ch.title || 'Chart' }}</div>
              <EChart :spec="ch" />
            </div>
          </div>
          <div v-else class="rp__empty">
            Bu sonuçta grafik yok.
          </div>
        </div>

        <!-- SQL -->
        <div v-else-if="activeTabSafe === 'sql'">
          <div v-if="result?.sql?.query" class="rp__card">
            <div class="rp__cardTitle">SQL</div>

            <pre class="rp__code"><code>{{ result.sql.query }}</code></pre>

            <div v-if="result.sql.explanation" class="rp__muted">
              {{ result.sql.explanation }}
            </div>

            <div class="rp__row">
              <button class="btn" type="button" @click="copy(result.sql.query)">Copy</button>
            </div>
          </div>
          <div v-else class="rp__empty">
            Bu sonuçta SQL yok.
          </div>
        </div>

        <!-- fallback -->
        <div v-else class="rp__empty">Sekme seç.</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ResultsTabs from '../ui/ResultsTabs.vue'
import DataTable from '../ui/DataTable.vue'
import EChart from '../ui/EChart.vue'

const props = defineProps({
  mode: { type: String, default: 'sql' }, // 'sql' | 'doc'
  result: { type: Object, default: null },
  activeTab: { type: String, default: 'table' }, // table|charts|sql|sources (doc modda ignore)
})

defineEmits(['setTab', 'openDoc', 'downloadPdf'])

const tabs = computed(() => [
  { key: 'table', label: 'Table' },
  { key: 'charts', label: 'Charts' },
  { key: 'sql', label: 'SQL' },
])

const hasAnyResult = computed(() => {
  const r = props.result
  if (!r) return false
  return !!(r.table || (r.charts && r.charts.length) || r.sql?.query || (r.sources && r.sources.length))
})

const activeTabSafe = computed(() => {
  const k = props.activeTab
  const ok = tabs.value.some(t => t.key === k)
  return ok ? k : 'table'
})

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {}
}

function formatScore(v) {
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toFixed(3)
}
</script>

<style scoped>
.rp{
  height: 100%;
  display:flex;
  flex-direction: column;
  min-height: 0;
}

.rp__header{
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.rp__title{
  font-weight: 900;
  color: var(--text);
  letter-spacing: .2px;
}

.rp__actions{
  display:flex;
  gap: 8px;
}

.rp__body{
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.rp__stack{
  display:flex;
  flex-direction: column;
  gap: 12px;
}

.rp__card{
  border: 1px solid var(--border-color);
  background: var(--card);
  border-radius: 16px;
  padding: 12px;
  box-shadow: 0 10px 22px rgba(0,0,0,.10);
}

.rp__cardTitle{
  font-weight: 850;
  color: var(--text);
  margin-bottom: 10px;
  font-size: 13px;
}

.rp__empty{
  padding: 18px 12px;
  color: var(--text-muted);
  border: 1px dashed var(--border-color);
  border-radius: 14px;
  background: rgba(255,255,255,.03);
}

.rp__code{
  margin: 0;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--border-color);
  background: rgba(0,0,0,.22);
  color: var(--text);
  overflow: auto;
  font-size: 12px;
  line-height: 1.5;
}

.rp__muted{
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.rp__row{
  margin-top: 10px;
  display:flex;
  gap: 10px;
}

.btn{
  height: 34px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: rgba(255,255,255,.06);
  color: var(--text);
  cursor:pointer;
  font-weight: 750;
}

.btn:disabled{
  opacity:.55;
  cursor:not-allowed;
}

/* sources */
.srcList{
  display:flex;
  flex-direction: column;
  gap: 10px;
}

.srcItem{
  text-align: left;
  border: 1px solid var(--border-color);
  background: rgba(255,255,255,.04);
  color: var(--text);
  border-radius: 14px;
  padding: 10px 10px;
  cursor:pointer;
}

.srcItem:hover{
  border-color: var(--accent);
}

.srcItem__title{
  font-weight: 850;
  font-size: 13px;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.srcItem__meta{
  display:flex;
  gap: 8px;
  align-items:center;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.pill{
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--pill);
}

.muted{
  color: var(--text-muted);
  font-size: 12px;
}

.srcItem__excerpt{
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.45;
}
</style>
