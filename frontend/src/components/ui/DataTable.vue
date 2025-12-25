<template>
  <div class="dt">
    <div class="dt__top">
      <div class="dt__meta">
        <span class="pill">{{ rowCount }} rows</span>
        <span class="pill">{{ colCount }} cols</span>
      </div>

      <div class="dt__actions">
        <button class="btn" type="button" @click="copyCsv" :disabled="!rowCount">
          Copy CSV
        </button>
      </div>
    </div>

    <div class="dt__wrap">
      <table class="dt__table">
        <thead>
          <tr>
            <th v-for="c in cols" :key="c.key">
              {{ c.label }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(r, i) in rows" :key="i">
            <td v-for="c in cols" :key="c.key">
              <span class="cell" :title="stringify(r?.[c.key])">
                {{ display(r?.[c.key]) }}
              </span>
            </td>
          </tr>

          <tr v-if="rows.length === 0">
            <td :colspan="cols.length" class="dt__empty">
              No rows.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // beklenen format:
  // table: { columns: [{key,label,type?}], rows: [...] }
  // veya { columns: ['a','b'], rows: [...] } da kabul edelim
  table: { type: Object, required: true },
})

const cols = computed(() => {
  const t = props.table || {}
  const c = t.columns || []
  if (Array.isArray(c) && c.length && typeof c[0] === 'string') {
    return c.map((k) => ({ key: k, label: k }))
  }
  if (Array.isArray(c) && c.length && typeof c[0] === 'object') {
    return c.map((x) => ({
      key: x.key ?? x.name ?? x.field,
      label: x.label ?? x.key ?? x.name ?? x.field,
    })).filter(x => !!x.key)
  }

  // columns yoksa rows’tan çıkar
  const rows = Array.isArray(t.rows) ? t.rows : []
  const first = rows[0]
  if (first && typeof first === 'object') {
    return Object.keys(first).map((k) => ({ key: k, label: k }))
  }
  return []
})

const rows = computed(() => {
  const t = props.table || {}
  return Array.isArray(t.rows) ? t.rows : []
})

const rowCount = computed(() => rows.value.length)
const colCount = computed(() => cols.value.length)

function display(v) {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'number') return Number.isFinite(v) ? v : String(v)
  if (typeof v === 'boolean') return v ? 'true' : 'false'
  if (v instanceof Date) return v.toISOString()
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function stringify(v) {
  if (v === null || v === undefined) return ''
  return typeof v === 'string' ? v : display(v)
}

function escapeCsv(val) {
  const s = String(val ?? '')
  if (/[",\n]/.test(s)) return `"${s.replaceAll('"', '""')}"`
  return s
}

function toCsv() {
  const c = cols.value
  const r = rows.value

  const header = c.map(x => escapeCsv(x.label)).join(',')
  const body = r.map((row) => c.map((x) => escapeCsv(row?.[x.key] ?? '')).join(',')).join('\n')
  return header + '\n' + body
}

async function copyCsv() {
  try {
    const csv = toCsv()
    await navigator.clipboard.writeText(csv)
  } catch {
    // sessiz geç
  }
}
</script>

<style scoped>
.dt{
  width: 100%;
}

.dt__top{
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.dt__meta{
  display:flex;
  gap: 8px;
  align-items:center;
  flex-wrap: wrap;
}

.pill{
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--pill);
  color: var(--text);
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

.dt__wrap{
  overflow: auto;
  border-radius: 14px;
  border: 1px solid var(--border-color);
}

.dt__table{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  min-width: 520px;
  background: rgba(0,0,0,.12);
}

.dt__table thead th{
  position: sticky;
  top: 0;
  z-index: 2;
  background: rgba(20, 24, 34, .92);
  color: var(--text);
  font-size: 12px;
  font-weight: 900;
  text-align: left;
  padding: 10px 10px;
  border-bottom: 1px solid var(--border-color);
}

.dt__table tbody td{
  padding: 10px 10px;
  border-bottom: 1px solid rgba(255,255,255,.08);
  color: var(--text);
  font-size: 12px;
  vertical-align: top;
}

.dt__table tbody tr:hover td{
  background: rgba(255,255,255,.04);
}

.cell{
  display:inline-block;
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dt__empty{
  color: var(--text-muted);
  padding: 16px 10px;
}
</style>
